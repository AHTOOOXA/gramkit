import asyncio
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.infrastructure.database.models.enums import NotificationSlot
from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.schemas.users import UserSchema
from core.services.base import BaseService
from core.services.messages import SendFailure, send_error_code, user_language
from core.services.notifications.types import NotificationTemplate

logger = get_logger(__name__)

SEND_INTERVAL_SECONDS = 0.05  # between two sends, under Telegram's broadcast limit


@dataclass(frozen=True, slots=True)
class DeliveryAttempt:
    """One send of a template: who, which message key, and the send's result (falsy on failure)."""

    user: UserSchema
    message_key: str
    result: object


class NotificationsService(BaseService):
    """
    Core notification service providing scheduling and delivery infrastructure.

    Apps should subclass this and provide their specific notification templates via:
    - MORNING_NOTIFICATIONS: list of notification classes for morning
    - EVENING_NOTIFICATIONS: list of notification classes for evening
    - MORNING_HOUR: hour for morning notifications (default 10)
    - EVENING_HOUR: hour for evening notifications (default 19)

    Per slot, templates run by priority and each user gets at most one message. Every send
    attempt is recorded in ``notification_deliveries`` through ``_record_delivery`` (the single
    choke point to extend, e.g. with per-user analytics).
    """

    # Default configuration - apps should override
    MORNING_HOUR = 10  # 10am local time
    EVENING_HOUR = 19  # 7pm local time
    MORNING_NOTIFICATIONS = []  # Override in app
    EVENING_NOTIFICATIONS = []  # Override in app

    def get_morning_notifications_with_promotions(self):
        """
        Get morning notifications including promotional broadcasts.

        Override this method in app to add promotional broadcasts or other dynamic notifications.
        Default implementation just returns the static list.
        """
        return self.MORNING_NOTIFICATIONS.copy()

    def get_evening_notifications_with_promotions(self):
        """
        Get evening notifications including promotional broadcasts.

        Override this method in app to add promotional broadcasts or other dynamic notifications.
        Default implementation just returns the static list.
        """
        return self.EVENING_NOTIFICATIONS.copy()

    # ------------------------------------------------------------------ planning

    def build_notifications(self, notification_classes: list[type], now: datetime | None = None):
        """Instantiate the templates in send order: priority descending, shuffled within a priority."""
        notifications = [cls().initialize(self.services, now=now) for cls in notification_classes]
        priority_groups: dict[int, list[NotificationTemplate]] = {}
        for notification in notifications:
            priority_groups.setdefault(notification.priority, []).append(notification)
        ordered = []
        for priority in sorted(priority_groups, reverse=True):
            group = priority_groups[priority]
            random.shuffle(group)  # Randomize notifications with the same priority
            ordered.extend(group)
        return ordered

    async def plan_slot(
        self, notifications: list[NotificationTemplate], users: list[UserSchema]
    ) -> list[tuple[NotificationTemplate, list[UserSchema]]]:
        """Who gets which template in one slot (at most one per user). Read-only: nothing is sent."""
        planned = []
        taken: set = set()
        for notification in notifications:
            available = [user for user in users if user.id not in taken]
            eligible = await notification.filter_eligible_users(available) if available else []
            taken.update(user.id for user in eligible)
            planned.append((notification, eligible))
        return planned

    # ------------------------------------------------------------------ sending

    async def send_notification(
        self,
        notification: NotificationTemplate,
        target_users: list[UserSchema] = None,
        slot: str = NotificationSlot.OTHER,
    ) -> tuple[int, list[UserSchema]]:
        """Filter ``target_users`` through one template and send it.

        Returns:
            Tuple containing (successful_count, eligible_users)
        """
        if not target_users:
            return 0, []
        eligible_users = await notification.filter_eligible_users(target_users)
        if not eligible_users:
            return 0, []
        return await self._deliver(notification, eligible_users, slot), eligible_users

    async def _deliver(self, notification: NotificationTemplate, users: list[UserSchema], slot: str) -> int:
        """Send one template to already-eligible users, one message (and one log row) per user."""
        sendable = await notification.pre_send_actions(users)
        if sendable is not None:
            users = sendable
            if not users:
                return 0

        content = self._custom_content(notification)
        if content == {}:
            logger.warning("No custom notification content found")
            await notification.post_send_actions(users, 0)
            return 0

        attempts: list[DeliveryAttempt] = []
        await self._send_each(notification, users, content, attempts)
        successful_count = await self.record_attempts(notification, attempts, slot)

        self._capture_batch_event(notification, users, successful_count, content)
        await notification.post_send_actions(users, successful_count)
        return successful_count

    async def send_attempts(
        self, notification: NotificationTemplate, users: list[UserSchema], attempts: list[DeliveryAttempt]
    ) -> None:
        """The send half of ``_deliver``, for a caller that records the attempts itself.

        No delivery rows: ``record_attempts`` writes them, so the slow Telegram sends can run
        outside any transaction (``WorkerContext.without_transaction()``) and the rows go in
        a short one afterwards (``user_broadcast_job``). ``attempts`` fills as the sends go,
        so whatever went out before a cancellation can still be recorded. No pre/post-send
        actions or batch event: the caller owns those.
        """
        content = self._custom_content(notification)
        if content == {}:
            logger.warning("No custom notification content found")
            return
        await self._send_each(notification, users, content, attempts)

    async def record_attempts(
        self, notification: NotificationTemplate, attempts: list[DeliveryAttempt], slot: str
    ) -> int:
        """One ``notification_deliveries`` row per attempt; returns how many were delivered."""
        successful_count = 0
        for attempt in attempts:
            await self._record_delivery(notification, attempt.user, attempt.message_key, slot, attempt.result)
            if attempt.result:
                successful_count += 1
        return successful_count

    @staticmethod
    def _custom_content(notification: NotificationTemplate) -> dict | None:
        """The template's custom content (``{}`` when it has none to send), ``None`` for i18n templates."""
        get_message_content = getattr(notification, "get_message_content", None)
        if get_message_content is None:
            return None
        return get_message_content() or {}

    async def _send_each(
        self,
        notification: NotificationTemplate,
        users: list[UserSchema],
        content: dict | None,
        attempts: list[DeliveryAttempt],
    ) -> None:
        """Send to each user (custom ``content`` or the template's i18n message), appending to ``attempts``."""
        for user in users:
            if not user.telegram_id or user.id is None:
                continue
            message_key = ""
            try:  # everything per user, so one bad key/markup/send can't end the slot for the rest
                message_key = await notification.get_message_key_for_user(user)
                reply_markup = notification.get_reply_markup(message_key, user_language(user))
                if content is not None:
                    result = await self._send_custom_content(user.telegram_id, content, reply_markup)
                else:
                    result = await notification.send_to_user(self.services.messages, user, message_key, reply_markup)
            except Exception:
                logger.exception(f"Notification {notification.template_name} to user {user.id} failed")
                result = SendFailure(SendFailure.OTHER)
            attempts.append(DeliveryAttempt(user, message_key, result))
            await asyncio.sleep(SEND_INTERVAL_SECONDS)

    async def _record_delivery(
        self, notification: NotificationTemplate, user: UserSchema, message_key: str, slot: str, result: object
    ) -> None:
        """The one place a send attempt is recorded. Extend here (analytics, variants), not at call sites."""
        error_code = send_error_code(result)
        assert user.id is not None
        await self.repo.notification_deliveries.record(
            user_id=user.id,
            template=notification.template_name,
            message_key=message_key,
            slot=str(slot),
            delivered=error_code is None,
            error_code=error_code,
            sent_at=notification.now,
        )

    def _capture_batch_event(
        self, notification: NotificationTemplate, users: list[UserSchema], successful_count: int, content: dict | None
    ) -> None:
        """The per-batch PostHog event the templates always sent (``distinct_id="system"``)."""
        event = notification.get_posthog_event()
        if not event:
            return
        properties: dict[str, Any] = {"success_count": successful_count, "total_count": len(users)}
        if content is not None:
            current_broadcast = getattr(notification, "_current_broadcast", None)
            properties["broadcast_id"] = getattr(current_broadcast, "id", None)
            properties["message_type"] = content.get("type")
        posthog.capture(distinct_id="system", event=event, properties=properties)

    async def _send_custom_content(self, telegram_id: int, content: dict, reply_markup=None):
        """Send one custom-content message (text / photo / video / animation / document)."""
        return await self.services.messages.send_content(telegram_id, content, reply_markup)

    async def send_notifications_by_time(
        self,
        notification_classes: list[type],
        hour: int,
        slot: str = NotificationSlot.OTHER,
        now: datetime | None = None,
    ) -> dict[str, int]:
        """Send notifications ensuring each user gets at most one, by priority"""
        time_eligible_users = await self.services.users.get_users_by_local_time(hour)
        if not time_eligible_users:
            logger.info(f"No users found with local time {hour}:00")
            return {cls.__name__: 0 for cls in notification_classes}

        notifications = self.build_notifications(notification_classes, now=now)
        results = {}
        for notification, eligible_users in await self.plan_slot(notifications, time_eligible_users):
            name = notification.__class__.__name__
            results[name] = await self._deliver(notification, eligible_users, slot) if eligible_users else 0
        return results

    async def send_morning_notification(self) -> dict[str, int]:
        """Send morning notifications to eligible users"""
        return await self.send_notifications_by_time(
            self.get_morning_notifications_with_promotions(), self.MORNING_HOUR, slot=NotificationSlot.MORNING
        )

    async def send_evening_notification(self) -> dict[str, int]:
        """Send evening notifications to eligible users"""
        return await self.send_notifications_by_time(
            self.get_evening_notifications_with_promotions(), self.EVENING_HOUR, slot=NotificationSlot.EVENING
        )

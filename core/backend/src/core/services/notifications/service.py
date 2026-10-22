import asyncio
import random
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

        content = None
        get_message_content = getattr(notification, "get_message_content", None)
        if get_message_content is not None:
            # Custom content (e.g. promotional broadcasts) instead of i18n keys
            content = get_message_content()
            if not content:
                logger.warning("No custom notification content found")
                await notification.post_send_actions(users, 0)
                return 0

        successful_count = 0
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
            await self._record_delivery(notification, user, message_key, slot, result)
            if result:
                successful_count += 1
            await asyncio.sleep(SEND_INTERVAL_SECONDS)

        self._capture_batch_event(notification, users, successful_count, content)
        await notification.post_send_actions(users, successful_count)
        return successful_count

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
        messages = self.services.messages
        message_type = content.get("type")
        parse_mode = content.get("parse_mode")
        if message_type == "text":
            return await messages.send_message(
                telegram_id=telegram_id, text=content["text"], reply_markup=reply_markup, parse_mode=parse_mode
            )
        senders = {
            "photo": messages.send_photo_by_file_id,
            "video": messages.send_video_by_file_id,
            "animation": messages.send_animation_by_file_id,
            "document": messages.send_document_by_file_id,
        }
        if message_type not in senders:
            logger.error(f"Unsupported custom notification message type: {message_type}")
            return SendFailure(SendFailure.OTHER)
        return await senders[message_type](
            telegram_id=telegram_id,
            file_id=content["media_file_id"],
            caption=content.get("caption"),
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )

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

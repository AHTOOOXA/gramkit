"""Broadcast notification templates: how a broadcast goes through the notification engine.

- ``PromotionalBroadcastNotification`` (+ ``Morning…`` / ``Evening…``): the scheduled path.
  In its slot, the highest-priority active ``promotional_broadcasts`` row replaces the
  regular notifications (priority 1000) until its deadline; the delivery counters on the
  row move once per cycle. Apps list the Morning/Evening classes in their
  ``get_*_notifications_with_promotions()`` and may narrow the audience by overriding
  ``filter_audience`` (default: everyone in the slot).
- ``ImmediateBroadcastNotification``: one send-now / bot ``/broadcast`` run
  (``user_broadcast_job``). Built per run with the content, the keyboard config and a
  per-run message key; users who already have a delivered row with that key are skipped
  (by the job up front, or by ``filter_eligible_users``), so a re-run of the same job
  doesn't send twice.

Both go through the engine → ``MessageService.send_content`` (the scheduled path through
``NotificationsService._deliver``; the job through its two halves, ``send_attempts`` outside
a transaction and ``record_attempts`` in a short one): one ``notification_deliveries`` row
per recipient, blocked bots flagged, the keyboard built per user (in the user's language)
from the core keyboard registry.
"""

from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardMarkup

from core.infrastructure.database.models import PromotionalBroadcast
from core.infrastructure.database.models.enums import NotificationTimeSlot
from core.infrastructure.logging import get_logger
from core.schemas.users import UserSchema
from core.services.broadcast_formatting import build_keyboard_markup
from core.services.notifications.types import NotificationTemplate

logger = get_logger(__name__)

PROMOTIONAL_BROADCAST_PRIORITY = 1000  # above every regular notification: a promo wins its slot


class PromotionalBroadcastNotification(NotificationTemplate):
    """Notification template for promotional broadcasts stored in the database.

    Audience: everyone in the slot, narrowed by ``filter_audience`` (the app override point;
    there's no per-broadcast audience choice).
    """

    def __init__(self, time_slot: NotificationTimeSlot):
        super().__init__()
        self._priority = PROMOTIONAL_BROADCAST_PRIORITY
        self._time_slot = time_slot
        # Read by NotificationsService._capture_batch_event (the PostHog broadcast_id).
        self._current_broadcast: PromotionalBroadcast | None = None

    @property
    def template_name(self) -> str:
        return "PromotionalBroadcastNotification"  # same for the morning and evening subclasses

    async def get_message_key(self) -> str:
        if self._current_broadcast is None:
            return "promotional_broadcast"
        return f"promotional_broadcast.{self._current_broadcast.id}"

    async def filter_eligible_users(self, users: list[UserSchema]) -> list[UserSchema]:
        broadcasts = await self._services.repo.promotional_broadcasts.get_active_by_time_slot(self._time_slot)
        if not broadcasts:
            return []
        self._current_broadcast = broadcasts[0]
        return await self.filter_audience(users)

    async def filter_audience(self, users: list[UserSchema]) -> list[UserSchema]:
        """Who in the slot gets the broadcast. Override in the app (e.g. only engaged users)."""
        return users

    def get_reply_markup(self, message_key: str, locale: str) -> InlineKeyboardMarkup | None:
        if self._current_broadcast is None:
            return None
        return build_keyboard_markup(
            {
                "keyboard_type": self._current_broadcast.keyboard_type,
                "keyboard_button_text": self._current_broadcast.keyboard_button_text,
            },
            locale,
        )

    async def pre_send_actions(self, users: list[UserSchema]) -> None:
        if users and self._current_broadcast:
            preview = self._current_broadcast.get_display_text()
            logger.info(
                f"Sending promotional broadcast #{self._current_broadcast.id} "
                f"'{preview}' to {len(users)} users "
                f"(deadline: {self._current_broadcast.deadline})"
            )

    async def post_send_actions(self, users: list[UserSchema], successful_count: int) -> None:
        if self._current_broadcast:
            # Delivery tracking: record this cycle's outcome. ``users`` is the eligible-user
            # list that was attempted; the rest are failures. Telegram exposes neither read
            # receipts nor clicks, so we only track sent / success / fail / cycles.
            attempted = len([u for u in users if u.telegram_id is not None])
            fail_count = max(0, attempted - successful_count)
            await self._services.repo.promotional_broadcasts.record_send_result(
                broadcast_id=self._current_broadcast.id,
                success=successful_count,
                fail=fail_count,
            )

            if successful_count > 0:
                logger.info(
                    f"Promotional broadcast #{self._current_broadcast.id} sent to {successful_count} users. "
                    f"Deadline: {self._current_broadcast.deadline}"
                )
            if self._current_broadcast.is_expired:
                logger.info(f"Promotional broadcast #{self._current_broadcast.id} has expired")
                await self._services.repo.promotional_broadcasts.expire_outdated_broadcasts()

    def get_posthog_event(self) -> str | None:
        return "promotional_broadcast_sent"

    def get_message_content(self) -> dict:
        if not self._current_broadcast:
            return {}
        return self._current_broadcast.get_content_for_sending()


class MorningPromotionalBroadcast(PromotionalBroadcastNotification):
    def __init__(self):
        super().__init__(NotificationTimeSlot.MORNING)


class EveningPromotionalBroadcast(PromotionalBroadcastNotification):
    def __init__(self):
        super().__init__(NotificationTimeSlot.EVENING)


class ImmediateBroadcastNotification(NotificationTemplate):
    """One send-now / bot ``/broadcast`` run, sent through the notification engine.

    Not a ``PromotionalBroadcastNotification``: that one records the row's counters in
    ``post_send_actions``; for a send-now run ``user_broadcast_job`` records them per chunk.
    """

    TEMPLATE_NAME = "ImmediateBroadcastNotification"

    def __init__(self, content: dict, keyboard: dict[str, Any] | None, message_key: str):
        super().__init__()
        self._priority = PROMOTIONAL_BROADCAST_PRIORITY
        self._content = content
        # The keyboard CONFIG (keyboard_type + keyboard_button_text): the markup is built per
        # user, in their language.
        self._keyboard = keyboard
        self._message_key = message_key

    @property
    def template_name(self) -> str:
        return self.TEMPLATE_NAME

    async def get_message_key(self) -> str:
        return self._message_key

    async def filter_eligible_users(self, users: list[UserSchema]) -> list[UserSchema]:
        """Everyone given, minus whoever this run already reached (a re-run after a worker restart)."""
        delivered = await self._services.repo.notification_deliveries.delivered_user_ids(
            self.template_name, self._message_key, [u.id for u in users if u.id is not None]
        )
        return [u for u in users if u.id not in delivered]

    def get_reply_markup(self, message_key: str, locale: str) -> InlineKeyboardMarkup | None:
        return build_keyboard_markup(self._keyboard, locale)

    def get_posthog_event(self) -> str | None:
        return None  # send-now never emitted a batch event (docs/ANALYTICS_CATALOG.md unchanged)

    def get_message_content(self) -> dict:
        return self._content

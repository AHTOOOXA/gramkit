import asyncio
import random

from core.infrastructure.logging import get_logger
from core.schemas.users import UserSchema
from core.services.base import BaseService
from core.services.notifications.types import NotificationTemplate

logger = get_logger(__name__)


class NotificationsService(BaseService):
    """
    Core notification service providing scheduling and delivery infrastructure.

    Apps should subclass this and provide their specific notification templates via:
    - MORNING_NOTIFICATIONS: list of notification classes for morning
    - EVENING_NOTIFICATIONS: list of notification classes for evening
    - MORNING_HOUR: hour for morning notifications (default 10)
    - EVENING_HOUR: hour for evening notifications (default 19)

    TODO: Make this more configurable and generic for multi-app usage:
    - Extract notification scheduling into a separate scheduler class
    - Make broadcast behavior pluggable (not all apps use promotional broadcasts)
    - Support custom notification time slots beyond morning/evening
    - Consider dependency injection for notification class discovery
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

    async def send_notification(
        self, notification: NotificationTemplate, target_users: list[UserSchema] = None
    ) -> tuple[int, list[UserSchema]]:
        """Generic method to send any type of notification

        Returns:
            Tuple containing (successful_count, eligible_users)
        """
        if not target_users:
            return 0, []

        eligible_users = await notification.filter_eligible_users(target_users)

        if not eligible_users:
            return 0, []

        await notification.pre_send_actions(eligible_users)

        # Check if notification has custom send method
        if hasattr(notification, "get_message_content"):
            # Handle custom content notifications (e.g., promotional broadcasts)
            # TODO: Make this more generic - perhaps a protocol/interface
            successful_count = await self._send_custom_notification(notification, eligible_users)
        else:
            # Regular notification using i18n message keys
            message_key = await notification.get_message_key()
            successful_count = await self.services.messages.broadcast(
                users=eligible_users,
                message_key=message_key,
                reply_markup_func=notification.get_keyboard_func(),
                posthog_event=notification.get_posthog_event(),
            )

        await notification.post_send_actions(eligible_users, successful_count)

        return successful_count, eligible_users

    async def _send_custom_notification(self, notification: NotificationTemplate, users: list[UserSchema]) -> int:
        """
        Send notification with custom content (not using i18n message keys).

        TODO: Make this more generic - currently assumes promotional broadcast structure.
        Apps with custom notification types should override this method.
        """
        message_content = notification.get_message_content()

        if not message_content:
            logger.warning("No custom notification content found")
            return 0

        keyboard_func = notification.get_keyboard_func()
        keyboard = keyboard_func() if keyboard_func else None

        successful_count = 0
        # Filter for registered users with telegram_id only
        telegram_users = [user for user in users if user.telegram_id is not None]
        user_ids = [user.telegram_id for user in telegram_users]

        try:
            message_type = message_content["type"]
            parse_mode = message_content.get("parse_mode")

            if message_type == "text":
                # Send text broadcast
                successful_count = await self._send_text_broadcast(
                    user_ids=user_ids,
                    text=message_content["text"],
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                )

            elif message_type == "photo":
                # Send photo broadcast
                successful_count = await self._send_media_broadcast(
                    user_ids=user_ids,
                    media_type="photo",
                    file_id=message_content["media_file_id"],
                    caption=message_content.get("caption"),
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                )

            elif message_type == "video":
                # Send video broadcast
                successful_count = await self._send_media_broadcast(
                    user_ids=user_ids,
                    media_type="video",
                    file_id=message_content["media_file_id"],
                    caption=message_content.get("caption"),
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                )

            elif message_type == "animation":
                # Send GIF/animation broadcast
                successful_count = await self._send_media_broadcast(
                    user_ids=user_ids,
                    media_type="animation",
                    file_id=message_content["media_file_id"],
                    caption=message_content.get("caption"),
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                )

            elif message_type == "document":
                # Send document broadcast
                successful_count = await self._send_media_broadcast(
                    user_ids=user_ids,
                    media_type="document",
                    file_id=message_content["media_file_id"],
                    caption=message_content.get("caption"),
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                )
            else:
                logger.error(f"Unsupported custom notification message type: {message_type}")
                return 0

            # Track in PostHog
            if notification.get_posthog_event():
                from core.infrastructure.posthog import posthog

                posthog.capture(
                    distinct_id="system",
                    event=notification.get_posthog_event(),
                    properties={
                        "success_count": successful_count,
                        "total_count": len(users),
                        "broadcast_id": getattr(notification, "_current_broadcast", {}).get("id"),
                        "message_type": message_type,
                    },
                )

        except Exception as e:
            logger.error(f"Failed to send custom notification: {e}")
            successful_count = 0

        return successful_count

    async def _send_text_broadcast(
        self, user_ids: list[int], text: str, reply_markup=None, parse_mode: str = None
    ) -> int:
        """Send text broadcast with parse mode support"""
        count = 0
        try:
            for user_id in user_ids:
                if await self.services.messages.send_message(
                    telegram_id=user_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                ):
                    count += 1
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Text broadcast error: {e}")
        return count

    async def _send_media_broadcast(
        self,
        user_ids: list[int],
        media_type: str,
        file_id: str,
        caption: str = None,
        reply_markup=None,
        parse_mode: str = None,
    ) -> int:
        """Send media broadcast (photo, video, animation, document) with parse mode support"""
        count = 0
        try:
            for user_id in user_ids:
                success = False

                if media_type == "photo":
                    success = await self.services.messages.send_photo_by_file_id(
                        telegram_id=user_id,
                        file_id=file_id,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                    )
                elif media_type == "video":
                    success = await self.services.messages.send_video_by_file_id(
                        telegram_id=user_id,
                        file_id=file_id,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                    )
                elif media_type == "animation":
                    success = await self.services.messages.send_animation_by_file_id(
                        telegram_id=user_id,
                        file_id=file_id,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                    )
                elif media_type == "document":
                    success = await self.services.messages.send_document_by_file_id(
                        telegram_id=user_id,
                        file_id=file_id,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                    )

                if success:
                    count += 1
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Media broadcast error: {e}")
        return count

    async def send_notifications_by_time(self, notification_classes: list[type], hour: int) -> dict[str, int]:
        """Send notifications ensuring each user gets exactly one notification based on priority"""
        results = {}
        notified_users: set[int] = set()  # Track users who have already received a notification

        time_eligible_users = await self.services.users.get_users_by_local_time(hour)
        if not time_eligible_users:
            logger.info(f"No users found with local time {hour}:00")
            return {cls.__name__: 0 for cls in notification_classes}

        notifications = [cls().initialize(self.services) for cls in notification_classes]

        # Group notifications by priority
        priority_groups = {}
        for notification in notifications:
            priority = notification.priority
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(notification)

        # Sort priorities in descending order and randomly shuffle notifications within each priority group
        sorted_notifications = []
        for priority in sorted(priority_groups.keys(), reverse=True):
            group = priority_groups[priority]
            random.shuffle(group)  # Randomize notifications with the same priority
            sorted_notifications.extend(group)

        for notification in sorted_notifications:
            notification_name = notification.__class__.__name__

            available_users = [user for user in time_eligible_users if user.id not in notified_users]

            if available_users:
                count, eligible_users = await self.send_notification(notification, available_users)
                results[notification_name] = count

                notified_users.update(user.id for user in eligible_users)
            else:
                results[notification_name] = 0

        return results

    async def send_morning_notification(self) -> dict[str, int]:
        """Send morning notifications to eligible users"""
        return await self.send_notifications_by_time(
            self.get_morning_notifications_with_promotions(), self.MORNING_HOUR
        )

    async def send_evening_notification(self) -> dict[str, int]:
        """Send evening notifications to eligible users"""
        return await self.send_notifications_by_time(
            self.get_evening_notifications_with_promotions(), self.EVENING_HOUR
        )

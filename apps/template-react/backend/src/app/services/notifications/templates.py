"""Example notification templates for the template app.

Replace these with your app's actual notification templates.

Each notification template should:
- Inherit from NotificationTemplate
- Set a priority (higher = sent first)
- Define message_keys for i18n
- Optionally implement filter_eligible_users() for targeting
- Optionally implement get_keyboard_func() for interactive buttons
- Optionally implement pre_send_actions() and post_send_actions() for logging/tracking
"""

from collections.abc import Callable

from core.infrastructure.logging import get_logger
from core.schemas.users import UserSchema
from core.services.notifications.types import NotificationTemplate

logger = get_logger(__name__)


class ExampleDailyNotification(NotificationTemplate):
    """
    Example daily notification sent to all users.

    Replace this with your app's actual daily notification logic.
    Example: Daily reminder, daily challenge, daily content, etc.
    """

    def __init__(self):
        super().__init__()
        self._priority = 50  # Medium priority
        self._message_keys = [
            "notifications.daily.message_1",
            "notifications.daily.message_2",
            "notifications.daily.message_3",
        ]

    async def get_message_key(self) -> str:
        """Return a random message key from the list"""
        return self.get_random_key(self._message_keys)

    def get_keyboard_func(self) -> Callable | None:
        """
        Return a function that generates a keyboard for this notification.

        Example:
            from app.tgbot.keyboards.notification_keyboards import daily_notification_kb
            return daily_notification_kb

        Return None if no keyboard is needed.
        """
        return None

    async def pre_send_actions(self, users: list[UserSchema]) -> None:
        """Log notification sending"""
        if users:
            logger.info(f"Sending example daily notification to {len(users)} users")


class ExampleEngagementNotification(NotificationTemplate):
    """
    Example engagement notification for premium/active users.

    Replace this with your app's actual engagement notification logic.
    Example: Feature announcement, re-engagement, premium benefits, etc.
    """

    def __init__(self):
        super().__init__()
        self._priority = 40  # Lower priority than daily
        self._message_keys = [
            "notifications.engagement.message_1",
            "notifications.engagement.message_2",
        ]

    async def filter_eligible_users(self, users: list[UserSchema]) -> list[UserSchema]:
        """
        Filter users who should receive this notification.

        Example implementations:
        - Only premium users: users with active subscriptions
        - Only active users: users who used the app recently
        - Only lapsed users: users who haven't used the app in X days
        - Only users without feature: users who haven't tried a specific feature

        This example filters for premium users (if subscriptions exist):
        """
        # Example: Only send to premium users
        # filtered_users = [
        #     user for user in users
        #     if await self._services.subscriptions.has_active_subscription(user.id)
        # ]
        # return filtered_users

        # For template: send to all users
        return users

    async def get_message_key(self) -> str:
        """Return a random message key from the list"""
        return self.get_random_key(self._message_keys)

    def get_keyboard_func(self) -> Callable | None:
        """Return keyboard function if needed"""
        return None

    async def pre_send_actions(self, users: list[UserSchema]) -> None:
        """Log notification sending"""
        if users:
            logger.info(f"Sending example engagement notification to {len(users)} users")

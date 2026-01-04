import re
from abc import ABC, abstractmethod
from collections.abc import Callable

from core.schemas.users import UserSchema


class NotificationTemplate(ABC):
    """Base abstract class for all notifications"""

    def __init__(self):
        self._services = None
        self._priority = 0  # Default priority, higher values take precedence
        self._message_keys = []  # List of message keys for this notification

    def initialize(self, services):
        """Initialize the notification with services"""
        self._services = services
        return self

    @property
    def priority(self) -> int:
        """Priority of the notification, higher values take precedence"""
        return getattr(self, "_priority", 0)

    @priority.setter
    def priority(self, value: int):
        self._priority = value

    @abstractmethod
    async def get_message_key(self) -> str:
        """Get the message key for this notification"""
        pass

    # Helper method for templates using random message keys
    def get_random_key(self, keys: list[str]) -> str:
        """Get a random message key from the provided list"""
        import random

        return random.choice(keys) if keys else ""

    # Optional methods with default implementations
    async def filter_eligible_users(self, users: list[UserSchema]) -> list[UserSchema]:
        """Filter users that are eligible to receive this notification"""
        return users

    def get_keyboard_func(self) -> Callable | None:
        """Get the keyboard function for this notification"""
        return None

    async def pre_send_actions(self, users: list[UserSchema]) -> None:
        """Actions to perform before sending the notification"""
        pass

    async def post_send_actions(self, users: list[UserSchema], successful_count: int) -> None:
        """Actions to perform after sending the notification"""
        pass

    def get_posthog_event(self) -> str | None:
        """Get the PostHog event name for tracking"""
        # Default implementation to derive event name from class name:
        # Convert CamelCase to snake_case and append "_notification_sent"
        class_name = self.__class__.__name__
        # Insert underscore between lowercase and uppercase letters
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
        # Remove "notification" from the name if it's already there to avoid duplication
        name = name.replace("_notification", "")
        return f"{name}_notification_sent"

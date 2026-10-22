import random
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from core.schemas.users import UserSchema


class NotificationTemplate(ABC):
    """Base abstract class for all notifications"""

    def __init__(self):
        self._services: Any = None  # the app's RequestsService, set by initialize()
        self._now: datetime | None = None
        self._priority = 0  # Default priority, higher values take precedence
        self._message_keys = []  # List of message keys for this notification

    def initialize(self, services, now: datetime | None = None):
        """Initialize the notification with services (and a fixed "now" for the slot, e.g. in tests)"""
        self._services = services
        self._now = now
        return self

    @property
    def now(self) -> datetime:
        """The moment the slot is evaluated at (wall clock unless fixed by ``initialize``)."""
        return self._now or datetime.now(UTC)

    @property
    def template_name(self) -> str:
        """Stable name stored in ``notification_deliveries.template`` (the caps query by it)."""
        return self.__class__.__name__

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

    async def get_message_key_for_user(self, user: UserSchema) -> str:
        """The message key for one recipient. Default: ``get_message_key()`` (random per call → per user)."""
        return await self.get_message_key()

    async def send_to_user(self, messages, user: UserSchema, message_key: str, reply_markup):
        """Send this template's message to one user (``messages`` is the ``MessageService``).

        Default: the i18n text ``message_key`` in the user's language. Override for another kind of message
        (e.g. a poll); the engine still logs the attempt and handles a blocked bot.
        """
        return await messages.send_localized(user, message_key, reply_markup=reply_markup)

    # Helper method for templates using random message keys
    def get_random_key(self, keys: list[str]) -> str:
        """Get a random message key from the provided list"""
        return random.choice(keys) if keys else ""

    # Optional methods with default implementations
    async def filter_eligible_users(self, users: list[UserSchema]) -> list[UserSchema]:
        """Filter users that are eligible to receive this notification"""
        return users

    def get_keyboard_func(self) -> Callable | None:
        """Get the keyboard function for this notification"""
        return None

    def get_reply_markup(self, message_key: str, locale: str):
        """Keyboard for one message. Override when the button depends on the chosen key."""
        keyboard_func = self.get_keyboard_func()
        return keyboard_func(locale) if keyboard_func else None

    async def pre_send_actions(self, users: list[UserSchema]) -> list[UserSchema] | None:
        """Actions to perform before sending the notification. May return the users to send it to
        (e.g. only those a gift was actually credited to); None sends it to all of ``users``."""
        return None

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

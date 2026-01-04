"""Authentication middleware for Telegram bot handlers."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, Update

from core.schemas.users import UserSchema, UserType

# Deep link prefixes that should skip user creation
# These handlers manage their own user lookup/creation logic
SKIP_USER_CREATION_PREFIXES = ("link_",)


class UserService(Protocol):
    """Protocol for user service with get_or_create_user method."""

    async def get_or_create_user(self, user_data: UserSchema) -> Any:
        """Get or create user from user data."""
        ...


class RequestsServiceProtocol(Protocol):
    """Protocol for requests service with users attribute."""

    @property
    def users(self) -> UserService:
        """User service."""
        ...


def _should_skip_user_creation(event: Message | CallbackQuery | Update) -> bool:
    """Check if user creation should be skipped for this event.

    Skips for /start commands with specific deep link prefixes (e.g., link_)
    that handle their own user management logic.

    Note: When registered as dp.update.outer_middleware, the event is an Update
    object, not a Message. We need to extract the message from Update.
    """
    # Handle Update objects (from dp.update.outer_middleware)
    message: Message | None = None
    if isinstance(event, Update):
        message = event.message
    elif isinstance(event, Message):
        message = event

    if not message:
        return False

    text = message.text or ""
    if not text.startswith("/start "):
        return False

    # Extract deep link argument after "/start "
    args = text[7:]  # len("/start ") = 7
    return any(args.startswith(prefix) for prefix in SKIP_USER_CREATION_PREFIXES)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware that authenticates Telegram users.

    Uses Protocol-based typing to support different RequestsService implementations.
    Extracts Telegram user from event, creates UserSchema, and calls services.users.get_or_create_user.

    Note: Skips user creation for certain deep link commands (e.g., /start link_*)
    that have their own user management logic.
    """

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery | Update, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery | Update,
        data: dict[str, Any],
    ) -> Any:
        """Authenticate user and inject into handler data."""
        # Skip user creation for specific deep link commands
        if _should_skip_user_creation(event):
            return await handler(event, data)

        services: RequestsServiceProtocol | None = data.get("services")
        assert services is not None, "ServiceMiddleware must run before AuthMiddleware"

        # Extract Telegram user based on event type
        if isinstance(event, Message):
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery):
            tg_user = event.from_user
        else:
            # For other update types, try to get from event_from_user
            tg_user = data.get("event_from_user")

        if not tg_user:
            return await handler(event, data)

        # Map TelegramUser fields to UserSchema with tg_ prefix
        display_name = f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip() or tg_user.username or "User"
        user_data = UserSchema(
            telegram_id=tg_user.id,
            # App profile fields (populated from TG data on first login)
            display_name=display_name,
            username=tg_user.username,
            language_code=tg_user.language_code,
            # Telegram data (read-only from TG API)
            tg_first_name=tg_user.first_name,
            tg_last_name=tg_user.last_name,
            tg_username=tg_user.username,
            tg_language_code=tg_user.language_code,
            tg_is_bot=tg_user.is_bot,
            tg_is_premium=tg_user.is_premium,
            user_type=UserType.REGISTERED,
        )

        # Get or create user via services
        user = await services.users.get_or_create_user(user_data)
        data["user"] = user

        return await handler(event, data)

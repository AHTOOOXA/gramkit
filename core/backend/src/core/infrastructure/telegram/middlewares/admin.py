"""Admin authorization middleware for Telegram bot handlers.

This middleware checks if a user has admin permissions before allowing
handler execution. Useful for protecting admin-only commands.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from core.schemas.users import UserSchema


class AdminMiddleware(BaseMiddleware):
    """
    Middleware that authorizes owner users for protected handlers.

    This middleware checks if the authenticated user's telegram_id is in
    the configured list of owner IDs. If not, it sends an unauthorized
    message and prevents handler execution.

    Args:
        owner_ids: List of Telegram user IDs with owner permissions
        unauthorized_msg: Message to send when user is not authorized
                         (default: "You don't have permission to use this command")

    Usage:
        >>> from aiogram import Router
        >>> from core.infrastructure.config import settings
        >>>
        >>> admin_router = Router()
        >>> admin_router.message.middleware(
        ...     AdminMiddleware(
        ...         owner_ids=settings.rbac.owner_ids,
        ...         unauthorized_msg="Admin only!"
        ...     )
        ... )
        >>>
        >>> @admin_router.message(Command("admin"))
        >>> async def admin_command(message: Message):
        ...     await message.answer("Welcome, admin!")

    Note:
        - Requires AuthMiddleware to inject 'user' into handler data
        - Only processes Message and CallbackQuery events
        - Sends unauthorized_msg and returns early if not authorized
    """

    def __init__(
        self,
        owner_ids: list[int],
        unauthorized_msg: str = "You don't have permission to use this command",
    ):
        self.owner_ids = owner_ids
        self.unauthorized_msg = unauthorized_msg

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        """Check admin authorization and execute handler if authorized."""
        # Get authenticated user from data (injected by AuthMiddleware)
        user: UserSchema | None = data.get("user")

        # Check if user is owner
        if not user or not user.telegram_id or user.telegram_id not in self.owner_ids:
            # Send unauthorized message
            if isinstance(event, Message):
                await event.answer(self.unauthorized_msg)
            elif isinstance(event, CallbackQuery):
                await event.answer(self.unauthorized_msg, show_alert=True)
            return

        # User is authorized, proceed to handler
        return await handler(event, data)

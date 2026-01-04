"""I18n middleware for Telegram bot handlers."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message

from core.infrastructure.i18n import i18n


class I18nMiddleware(BaseMiddleware):
    """
    Middleware that sets user locale for translation.

    Uses the authenticated user's locale from the data dict.
    """

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        """Set user locale and ensure cleanup."""
        i18n.set_user_locale(data.get("user"))
        try:
            return await handler(event, data)
        finally:
            i18n.reset_translation()

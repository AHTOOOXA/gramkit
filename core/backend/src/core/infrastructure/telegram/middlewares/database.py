"""Database middleware for Telegram bot handlers."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware that provides repo with transaction per update.

    Each Telegram update (message, callback, etc.) gets its own
    database session and transaction.

    Parameterized with repo_factory to support different RequestsRepo implementations.
    """

    def __init__(self, session_pool, repo_factory: Callable) -> None:
        """
        Initialize database middleware.

        Args:
            session_pool: SQLAlchemy async session pool
            repo_factory: Callable that creates RequestsRepo from session
                         Example: lambda session: RequestsRepo(session)
        """
        self.session_pool = session_pool
        self.repo_factory = repo_factory

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        """Wrap handler with database session and transaction."""
        async with self.session_pool() as session:
            async with session.begin():
                # Inject session and repo into handler data
                data["session"] = session
                data["repo"] = self.repo_factory(session)
                result = await handler(event, data)
                # Transaction commits here automatically
        return result

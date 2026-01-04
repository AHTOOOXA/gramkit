"""Generic service middleware for Telegram bots."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message


class ServiceMiddleware(BaseMiddleware):
    """
    Generic service middleware for Telegram bots.

    Creates service aggregator per request using injected factory.
    Each Telegram update gets its own service instance with proper scoping.

    Args:
        service_factory: Callable that creates service aggregator
                        Signature: (repo, bot, **kwargs) -> ServiceAggregator
        **dependencies: Additional dependencies to pass to factory (e.g., arq, redis, producer)

    Usage:
        from app.services.requests import RequestsService

        middleware = ServiceMiddleware(
            service_factory=lambda repo, bot, arq, producer, redis: RequestsService(
                repo=repo,
                bot=bot,
                arq=arq,
                producer=producer,
                redis=redis
            ),
            arq=arq_instance,
            producer=producer_instance,
            redis=redis_instance
        )
        dp.update.outer_middleware(middleware)
    """

    def __init__(self, service_factory: Callable, **dependencies):
        self.service_factory = service_factory
        self.dependencies = dependencies

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        """Create services and inject into handler context."""
        repo = data.get("repo")
        bot = data.get("bot")

        if repo:
            # Create services using injected factory and dependencies
            services = self.service_factory(repo=repo, bot=bot, **self.dependencies)
            data["services"] = services

        return await handler(event, data)

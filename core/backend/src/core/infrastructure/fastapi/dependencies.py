"""The request dependencies every app's endpoints use: the DB session, the services, the user.

Core routers and app routers use the same functions:

    from core.infrastructure.fastapi.dependencies import get_services, get_user

    @router.get("/me")
    async def me(user: UserSchema = Depends(get_user)): ...

An app doesn't reimplement them; ``create_api`` registers what is app-specific on ``app.state``:
``repo_class`` (the app's repo aggregator), ``services_class`` (its service aggregator),
``telegram_auth`` and ``guest_locale`` (auth, see ``core.infrastructure.fastapi.auth``).

They are real dependencies, not stubs to override. ``app.dependency_overrides`` is for tests: while it
has any entry, FastAPI rebuilds the dependency tree of every dependency on every request (re-reading
signatures), about a third of a simple request's Python time. An app that still overrides
``get_user`` / ``get_services`` keeps working, it only pays that.
"""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from aiogram import Bot
from arq.connections import ArqRedis
from fastapi import Depends, Request

from core.infrastructure.config import settings
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.infrastructure.fastapi.auth import resolve_user
from core.infrastructure.rabbit.producer import RabbitMQProducer
from core.infrastructure.redis import RedisClient
from core.schemas.users import UserSchema
from core.services.requests import CoreRequestsService


async def get_repo(request: Request) -> AsyncGenerator[CoreRequestsRepo]:
    """Open the request session: one ``AsyncSession`` and one transaction.

    Apps must configure app.state with:
    - session_pool: AsyncSession factory
    - repo_class: Repository aggregator class (default: CoreRequestsRepo)

    The transaction commits when this dependency exits (rollback on exception). *When* it
    exits is decided where it is used, by the ``Depends`` scope, not here:

    - ``Depends(get_repo, scope="function")`` (the default chain, ``get_services``): the exit
      runs when the endpoint returns, **before the response is sent**. A client that
      refetches right after a 200 reads committed data, and a failing commit (e.g. an
      ``IntegrityError`` raised by the flush on commit) reaches the client as a 500 instead
      of a 200 for data that was never saved.
    - ``Depends(get_repo, scope="request")``: the exit runs **after the response is sent**.
      Only for streaming endpoints (``StreamingResponse``) whose body generator keeps using
      the session after the endpoint returned; the commit then happens after the stream.

    A bare ``Depends(get_repo)`` means request scope, and FastAPI caches the two scopes
    separately: an endpoint that reaches ``get_repo`` at both scopes gets **two** sessions
    (and can block on its own row locks). Pick one scope per endpoint.

    Yields:
        Repository aggregator instance with active session
    """
    session_pool = request.app.state.session_pool
    repo_class = getattr(request.app.state, "repo_class", CoreRequestsRepo)

    async with session_pool() as session:
        async with session.begin():
            yield repo_class(session)


# Process-wide clients. Never build these per request (see core.infrastructure.fastapi.clients).


async def get_bot(request: Request) -> Bot | None:
    """The worker's Bot, created once in create_api's lifespan. None when BOT__TOKEN is empty, or under an
    ASGI test client (no lifespan; tests override this dependency)."""
    return getattr(request.app.state, "bot", None)


async def get_arq_pool(request: Request) -> ArqRedis | None:
    """The worker's arq pool, created once in create_api's lifespan. None under an ASGI test client."""
    return getattr(request.app.state, "arq", None)


_redis_client: RedisClient | None = None


async def get_redis_client() -> RedisClient:
    """One RedisClient per process (it pools its own connections)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient(settings.redis)
    return _redis_client


async def get_rabbit_producer() -> RabbitMQProducer:
    return RabbitMQProducer(settings.rabbit)  # a config holder; it connects only when used


def _services(request: Request, repo, producer, bot, redis, arq) -> Any:
    services_class = getattr(request.app.state, "services_class", None)
    if services_class is None:
        raise NotImplementedError(
            "No services class registered: pass create_api(services_class=RequestsService) "
            "(or override core's get_services, the old way)."
        )
    return services_class(repo, producer, bot, redis, arq)


async def get_services(
    request: Request,
    repo: CoreRequestsRepo = Depends(get_repo, scope="function"),
    producer: RabbitMQProducer = Depends(get_rabbit_producer),
    bot: Bot | None = Depends(get_bot),
    redis: RedisClient = Depends(get_redis_client),
    arq: ArqRedis | None = Depends(get_arq_pool),
) -> CoreRequestsService:
    """The app's service aggregator (``app.state.services_class``) for this request. The transaction commits
    before the response is sent.

    Returns, never yields: FastAPI refuses a ``yield`` dependency (request scope) that depends on a
    function-scoped one, and the function scope is what commits before the response (see ``get_repo``).
    Typed as core's aggregator; an app endpoint annotates its own (``services: RequestsService = ...``).
    """
    return _services(request, repo, producer, bot, redis, arq)


async def get_services_streaming(
    request: Request,
    repo: CoreRequestsRepo = Depends(get_repo, scope="request"),
    producer: RabbitMQProducer = Depends(get_rabbit_producer),
    bot: Bot | None = Depends(get_bot),
    redis: RedisClient = Depends(get_redis_client),
    arq: ArqRedis | None = Depends(get_arq_pool),
) -> CoreRequestsService:
    """``get_services`` whose session stays open while a ``StreamingResponse`` body streams, committing
    after it. Legacy: don't hold a transaction during an LLM answer (``.claude/rules/backend.md``). Pair it
    with ``get_user_streaming``: ``get_user`` goes through ``get_services`` and would open a second session.
    """
    return _services(request, repo, producer, bot, redis, arq)


async def get_user(request: Request, services: CoreRequestsService = Depends(get_services)) -> UserSchema:
    """The request's user: Telegram initData, the session cookie, or the shared guest
    (``core.infrastructure.fastapi.auth.resolve_user``)."""
    return await resolve_user(request, services)


async def get_user_streaming(
    request: Request, services: CoreRequestsService = Depends(get_services_streaming)
) -> UserSchema:
    """``get_user`` on the streaming endpoint's session (``get_services_streaming``)."""
    return await resolve_user(request, services)


async def get_telegram_auth(request: Request):
    """Get Telegram authenticator from app.state.

    Apps must configure app.state.telegram_auth during initialization.
    This is generic TMA infrastructure - verifies Telegram initData.

    Configuration example:
        from core.infrastructure.auth.telegram import TelegramAuthenticator

        telegram_auth = TelegramAuthenticator(bot_token=config.bot_token)
        app.state.telegram_auth = telegram_auth

    Args:
        request: FastAPI request object

    Returns:
        TelegramAuthenticator instance

    Raises:
        AttributeError: If app.state.telegram_auth not configured
    """
    if not hasattr(request.app.state, "telegram_auth"):
        raise AttributeError(
            "app.state.telegram_auth not configured. "
            "Configure TelegramAuthenticator during app initialization. "
            "Example: app.state.telegram_auth = TelegramAuthenticator(bot_token)"
        )
    return request.app.state.telegram_auth


async def get_current_user_id(user=Depends(get_user)) -> UUID | None:
    """Get current user ID if authenticated, None otherwise.

    Extracts user_id from the authenticated user. Returns None for:
    - Unauthenticated requests
    - Mock/guest users

    Args:
        user: User object from get_user dependency

    Returns:
        User ID if authenticated, None otherwise
    """
    if user and hasattr(user, "id") and user.id:
        return user.id
    return None

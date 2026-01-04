"""Generic FastAPI dependency stubs for core routers.

Apps override these with app-specific implementations using:
  app.dependency_overrides[core_deps.get_user] = app_get_user

This module provides base dependencies that core routes can use.
Each app must override these dependencies to provide their specific implementations.

Pattern:
    # In core route
    from core.infrastructure.fastapi.dependencies import get_user

    @router.get("/me")
    async def get_current_user(user=Depends(get_user)):
        return user

    # In app factory
    from core.infrastructure.fastapi import dependencies as core_deps
    app.dependency_overrides[core_deps.get_user] = app_get_user
"""

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Request

from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.services.requests import CoreRequestsService


async def get_repo(request: Request) -> AsyncGenerator[CoreRequestsRepo]:
    """Get repository aggregator from app.state.

    Apps must configure app.state with:
    - session_pool: AsyncSession factory
    - repo_class: Repository aggregator class (default: CoreRequestsRepo)

    This dependency is generic and should work for most apps without override.
    Override only if you need custom repository initialization logic.

    Yields:
        Repository aggregator instance with active session
    """
    session_pool = request.app.state.session_pool
    repo_class = getattr(request.app.state, "repo_class", CoreRequestsRepo)

    async with session_pool() as session:
        async with session.begin():
            yield repo_class(session)


async def get_services(
    repo: CoreRequestsRepo = Depends(get_repo),
) -> CoreRequestsService:
    """Get services aggregator. Apps MUST override with app-specific service.

    Core provides CoreRequestsService, but apps typically need to override with
    their own RequestsService that includes app-specific services.

    Override example:
        from app.services.requests import RequestsService

        async def app_get_services(repo=Depends(get_repo)):
            return RequestsService(repo)

        app.dependency_overrides[core_deps.get_services] = app_get_services

    Raises:
        NotImplementedError: Always raises - app must override this dependency

    Args:
        repo: Repository aggregator from get_repo

    Returns:
        Service aggregator (but raises NotImplementedError)
    """
    raise NotImplementedError(
        "App must override get_services dependency. "
        "Core provides CoreRequestsService, but apps should provide their own "
        "RequestsService with app-specific services."
    )


async def get_user(request: Request):
    """Get authenticated user from request. Apps MUST override.

    Authentication is app-specific (Telegram, JWT, sessions, etc).
    Each app must provide its own implementation.

    Override example:
        from app.webhook.auth import get_user as app_get_user
        app.dependency_overrides[core_deps.get_user] = app_get_user

    Raises:
        NotImplementedError: Always raises - app must override this dependency

    Args:
        request: FastAPI request object

    Returns:
        User object (but raises NotImplementedError)
    """
    raise NotImplementedError(
        "App must override get_user dependency. Authentication is app-specific (Telegram, JWT, sessions, etc)."
    )


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

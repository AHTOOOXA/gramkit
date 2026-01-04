"""Template FastAPI webhook application."""

from collections.abc import Awaitable, Callable
from pathlib import Path

from app.infrastructure import setup_infrastructure

setup_infrastructure()

from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.exceptions import BackendException
from app.infrastructure.database.repo.requests import RequestsRepo
from app.webhook import routers
from app.webhook.auth import get_user as app_get_user
from app.webhook.dependencies.service import get_services as app_get_services
from core.infrastructure.auth.telegram import TelegramAuthenticator
from core.infrastructure.config import settings
from core.infrastructure.fastapi import create_api
from core.infrastructure.fastapi import dependencies as core_deps
from core.infrastructure.fastapi.routers import (
    auth_email,
    auth_telegram,
    auth_telegram_link,
    payments,
    subscriptions,
    users,
    webhooks,
)

# Get version for API documentation
release_version = "unknown"
try:
    from importlib.metadata import version

    release_version = version("template-backend")
except Exception:
    pass


def create_exception_handler(
    status_code: int, initial_detail: str
) -> Callable[[Request, BackendException], Awaitable[JSONResponse]]:
    async def exception_handler(_: Request, exc: BackendException) -> JSONResponse:
        return JSONResponse(
            status_code=status_code, content={"detail": {"message": exc.message, "code": exc.code, "name": exc.name}}
        )

    return exception_handler


# Initialize core auth components with app-specific configuration
from core.infrastructure.auth.telegram import generate_secret_key

telegram_secret = generate_secret_key(settings.bot.token)
telegram_auth = TelegramAuthenticator(secret=telegram_secret)

# Create fully-configured API using factory
app = create_api(
    config=settings.web,
    db_config=settings.db,
    repo_class=RequestsRepo,
    routers=[
        auth_telegram.router,
        auth_email.router,
        auth_telegram_link.router,
        payments.router,
        subscriptions.router,
        users.router,
        webhooks.yookassa_router,
        webhooks.telegram_stars_router,
        routers.base.router,
        routers.admin.router,
        routers.demo.router,
    ],
    title="Template API",
    version=release_version,
    static_path=Path(__file__).parent.parent / "static",
    root_path=settings.web.api_root_path,  # Configurable: "" for subdomain, "/api/template" for path-based
    security_csp=(
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://js.posthog.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        f"connect-src 'self' https://cdn.jsdelivr.net {settings.web.api_url} https://api.posthog.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
)

# Configure core auth components in app state
app.state.telegram_auth = telegram_auth
app.state.settings = settings

# Set up dependency overrides for core routes
app.dependency_overrides[core_deps.get_user] = app_get_user
app.dependency_overrides[core_deps.get_services] = app_get_services

# Add custom exception handlers (if needed)
# Example:
# app.add_exception_handler(
#     exc_class_or_status_code=CustomException,
#     handler=create_exception_handler(status.HTTP_400_BAD_REQUEST, "Custom error message"),
# )

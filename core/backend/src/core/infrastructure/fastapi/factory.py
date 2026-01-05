"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

import sentry_sdk
from fastapi import FastAPI
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.cors import CORSMiddleware

from core.infrastructure.config import settings
from core.infrastructure.database.setup import create_engine, create_session_pool
from core.infrastructure.fastapi.middleware import (
    CachedStaticFiles,
    RequestIdMiddleware,
    RequestTracker,
    RequestTrackerMiddleware,
    SecurityConfig,
    SecurityHeadersMiddleware,
)
from core.infrastructure.fastapi.routers.health import router as health_router
from core.infrastructure.logging import get_logger
from core.infrastructure.redis import RedisClient

logger = get_logger(__name__)


class WebConfig(Protocol):
    """Protocol for web configuration."""

    frontend_url: str


def create_api(
    config: WebConfig,
    db_config,
    repo_class: type,
    routers: list,
    title: str = "API",
    version: str = "unknown",
    static_path: Path | None = None,
    security_csp: str | None = None,
    root_path: str = "",
    on_startup: list | None = None,
) -> FastAPI:
    """
    Create fully-configured FastAPI app with standard infrastructure.

    Sets up automatically:
    - FastAPI with lifespan management (DB cleanup)
    - Security headers middleware (CSP, HSTS, etc.)
    - CORS middleware
    - Rate limiting
    - Static file serving (optional)
    - All routers registered

    Args:
        config: Web configuration (debug, domain)
        db_config: Database configuration
        repo_class: Repository aggregator class
        routers: List of FastAPI routers
        title: API title for docs
        version: API version for docs
        static_path: Path to static files directory (optional)
        security_csp: Content Security Policy string (optional, defaults to strict)
        root_path: Root path for reverse proxy setups (optional)
        on_startup: List of async callbacks to run on startup (optional)

    Returns:
        FastAPI app ready to serve

    Example:
        from pathlib import Path
        from core.infrastructure.fastapi import create_api
        from core.infrastructure.config import settings
        from app.infrastructure.database.repo.requests import RequestsRepo
        from app.webhook import routers

        app = create_api(
            config=settings.web,
            db_config=settings.db,
            repo_class=RequestsRepo,
            routers=[
                routers.auth.router,
                routers.base.router,
                routers.tarot.router,
            ],
            title="Tarot API",
            version="1.0.0",
            static_path=Path(__file__).parent.parent / "static",
            security_csp=(
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            )
        )
    """
    # Initialize Sentry if configured
    if settings.observability.sentry_enabled:
        sentry_sdk.init(
            dsn=settings.observability.sentry_dsn,
            environment=settings.observability.logfire_environment,
            send_default_pii=True,
            traces_sample_rate=1.0,  # 100% - fine for low traffic (<1k DAU)
            profiles_sample_rate=0.5,  # 50% - profiles are heavier
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            release=version,  # Uses the version parameter passed to create_api()
        )

    # Create database engine
    engine = create_engine(db_config)
    session_pool = create_session_pool(engine)

    # Create request tracker for graceful shutdown
    request_tracker = RequestTracker()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Application lifespan management with graceful shutdown."""
        # Lazy import to avoid circular import: rbac -> dependencies -> factory -> rbac
        from core.auth.rbac import sync_owner_roles

        logger.info("🚀 Webhook application starting up...")

        # Store request tracker in app state for health checks
        app.state.request_tracker = request_tracker

        await sync_owner_roles(session_pool)

        # Run app-specific startup callbacks
        if on_startup:
            for callback in on_startup:
                await callback(session_pool)

        logger.info("✅ Webhook application ready")

        yield  # Application runs here

        # Graceful shutdown sequence
        logger.info("🛑 Webhook application shutting down...")

        # 1. Signal shutdown (health check will return 503, new requests rejected)
        request_tracker.start_shutdown()
        logger.info("  ⏸  Marked as shutting down, rejecting new requests")

        # 2. Wait for active requests to drain
        drain_timeout = config.shutdown_drain_timeout
        drained = await request_tracker.wait_for_drain(timeout=drain_timeout)
        if drained:
            logger.info("  ✓ All requests drained successfully")
        else:
            logger.warning(
                f"  ⚠  Drain timeout after {drain_timeout}s, {request_tracker.active_count} requests still active"
            )

        # 3. Close Redis connections
        await RedisClient.close()
        logger.info("  ✓ Redis connections closed")

        # 4. Close database connections
        await engine.dispose()
        logger.info("  ✓ Database connections closed")

        logger.info("✅ Webhook application shutdown complete")

    # Create app
    app_configs = {
        "lifespan": lifespan,
        "title": title,
        "version": version,
        "root_path": root_path,  # For proper URL generation behind proxy
    }

    # Hide docs in production
    if not settings.debug:
        app_configs["openapi_url"] = None

    app = FastAPI(**app_configs)

    # Rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Middleware stack (last added = first executed)
    # Order: RequestId → RequestTracker → Security → CORS

    # Request ID propagation (must be first to set context for all other middleware)
    app.add_middleware(RequestIdMiddleware)

    # Request tracking for graceful shutdown
    app.add_middleware(RequestTrackerMiddleware, tracker=request_tracker)

    # Security headers
    sec_config = SecurityConfig(
        csp=security_csp
        or (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https:; "
            "frame-ancestors 'none'"
        ),
        hsts_enabled=not settings.debug,
    )
    app.add_middleware(SecurityHeadersMiddleware, config=sec_config)

    # CORS
    cors_origins = [config.frontend_url]
    if hasattr(config, "cors_origins") and config.cors_origins:
        cors_origins.extend(config.cors_origins)
    # In debug mode, allow any localhost origin for direct frontend access
    allow_origin_regex = r"^http://localhost:\d+$" if settings.debug else None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    # Always include health check endpoints first (core functionality)
    app.include_router(health_router)
    # Then include app-specific routers
    for router in routers:
        app.include_router(router)

    # Static files
    if static_path and static_path.exists():
        # Long cache for images
        images_path = static_path / "images"
        if images_path.exists():
            app.mount(
                "/static/images",
                CachedStaticFiles(directory=images_path, html=False, cache_max_age=604800),
                name="static_images",
            )

        # Default static files
        app.mount(
            "/static",
            CachedStaticFiles(directory=static_path, html=False, cache_max_age=86400),
            name="static",
        )

    # Store for dependency injection
    app.state.session_pool = session_pool
    app.state.repo_class = repo_class
    app.state.engine = engine

    return app

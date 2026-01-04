"""
Centralized infrastructure setup for the tarot application.

This module provides:
1. Instantiation of all infrastructure components
2. Single setup function for initialization
3. Clear exports for easy importing

Usage:
    # In entry points (webhook/bot/worker)
    from app.infrastructure import setup_infrastructure
    setup_infrastructure()

    # In services/handlers
    from app.infrastructure import file_manager
"""

from pathlib import Path

import sentry_sdk

# App infrastructure
from app.infrastructure.database.setup import create_engine, create_session_pool

# Configuration
from core.infrastructure.config import settings

# Core infrastructure
from core.infrastructure.files import FileManager
from core.infrastructure.i18n import init_i18n
from core.infrastructure.logfire import setup_logfire
from core.infrastructure.logging import setup_logging
from core.infrastructure.posthog import setup_posthog
from core.infrastructure.redis import RedisClient

# ============================================================================
# Path Constants
# ============================================================================

# Get the absolute path to the src directory
# This file: apps/template/backend/src/app/infrastructure/__init__.py
# Parent: apps/template/backend/src/app/
_SRC_PATH = Path(__file__).parent.parent

# ============================================================================
# Infrastructure Components (instantiated once, imported everywhere)
# ============================================================================

# File Manager - Static file handling
file_manager = FileManager(static_path=_SRC_PATH / "static", api_domain=settings.web.api_url)

# Redis Client - Caching and session storage
redis_client = RedisClient(settings.redis)


# Database - Factory functions (instantiated per entry point)
def create_db_engine():
    """Create SQLAlchemy async engine with app configuration."""
    return create_engine(settings.db)


def create_db_session_pool(engine):
    """Create session pool from engine."""
    return create_session_pool(engine)


# ============================================================================
# Infrastructure Setup Function
# ============================================================================


def setup_infrastructure():
    """
    Initialize all infrastructure components.

    Call this once at application startup in:
    - app/webhook/app.py (FastAPI)
    - app/tgbot/bot.py (Telegram bot)
    - app/worker/worker.py (ARQ worker)

    Initializes:
    - Logging system
    - Observability (Logfire, PostHog)
    - Error tracking (Sentry)
    - Internationalization (i18n)
    """
    # Logging - Set up first for debug visibility
    setup_logging()

    # Observability - Monitoring and analytics
    setup_logfire(settings.observability.logfire_token, settings.observability.logfire_environment)
    setup_posthog(settings.observability.posthog_api_key, settings.observability.posthog_host)

    # Error Tracking - Sentry integration
    if settings.observability.sentry_dsn:
        release_version = "unknown"
        try:
            from importlib.metadata import version

            release_version = version("Template")
        except Exception:
            pass

        sentry_sdk.init(
            dsn=settings.observability.sentry_dsn,
            release=release_version,
        )

    # Internationalization - Translation system
    init_i18n(app_locales_dir=_SRC_PATH / "i18n" / "locales")


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Components
    "file_manager",
    "redis_client",
    # Database factories
    "create_db_engine",
    "create_db_session_pool",
    # Setup function
    "setup_infrastructure",
]

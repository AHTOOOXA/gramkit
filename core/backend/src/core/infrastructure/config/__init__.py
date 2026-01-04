# core/backend/src/core/infrastructure/config/__init__.py
"""Configuration system for the monorepo.

Usage (same everywhere - app code, core code, bot, worker):

    from core.infrastructure.config import settings

    settings.db.url
    settings.session.cookie_name
    settings.rbac.owner_ids

Apps define their own Settings class using components from this package.
"""

# Components for apps to build their Settings
# Unified accessor (import this for access)
from core.infrastructure.config.accessor import get_settings, settings
from core.infrastructure.config.components import (
    BotSettings,
    DatabaseSettings,
    EmailSettings,
    ObservabilitySettings,
    OpenAISettings,
    PaymentSettings,
    RabbitSettings,
    RBACSettings,
    RedisSettings,
    SessionSettings,
    WebSettings,
)

__all__ = [
    # Components
    "DatabaseSettings",
    "RedisSettings",
    "RabbitSettings",
    "SessionSettings",
    "BotSettings",
    "WebSettings",
    "PaymentSettings",
    "EmailSettings",
    "OpenAISettings",
    "ObservabilitySettings",
    "RBACSettings",
    # Accessor
    "get_settings",
    "settings",
]

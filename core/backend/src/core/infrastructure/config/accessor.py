# core/backend/src/core/infrastructure/config/accessor.py
"""Unified settings access.

Provides a single import point for all code (app and core).
The actual settings instance comes from the running app.
"""

from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


@lru_cache
def get_settings() -> Any:
    """Get settings from current app.

    Lazily imports from app.config - resolves to whichever app is running
    based on PYTHONPATH.
    """
    from app.config import settings

    return settings


class _SettingsProxy:
    """Proxy for direct attribute access: settings.db.url

    This allows the same import syntax everywhere:
        from core.infrastructure.config import settings
        settings.db.url
    """

    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)

    def __repr__(self) -> str:
        return repr(get_settings())


# The singleton - import this everywhere
settings = _SettingsProxy()

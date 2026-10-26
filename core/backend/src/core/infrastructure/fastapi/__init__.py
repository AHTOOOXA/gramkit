"""FastAPI infrastructure.

``create_api`` loads on first access (PEP 562 ``__getattr__``): importing
``core.infrastructure.fastapi.dependencies`` (core routers, ``core.auth.rbac``, core tests) runs
this file, and must not pull in the factory's web stack (``sentry_sdk``, ``slowapi``), which a
core-only install (core CI) doesn't have. ``from core.infrastructure.fastapi import create_api``
works as before.
"""

import importlib
from typing import Any

from core.infrastructure.fastapi import dependencies
from core.infrastructure.fastapi.middleware import CachedStaticFiles, SecurityConfig, SecurityHeadersMiddleware

# ``create_api`` is served by ``__getattr__`` below (not listed: it isn't a module attribute).
__all__ = [
    "dependencies",
    "CachedStaticFiles",
    "SecurityConfig",
    "SecurityHeadersMiddleware",
]


def __getattr__(name: str) -> Any:
    if name == "create_api":
        return importlib.import_module("core.infrastructure.fastapi.factory").create_api
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

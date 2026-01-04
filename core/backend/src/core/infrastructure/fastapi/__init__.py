"""FastAPI infrastructure."""

from core.infrastructure.fastapi import dependencies
from core.infrastructure.fastapi.factory import create_api
from core.infrastructure.fastapi.middleware import CachedStaticFiles, SecurityConfig, SecurityHeadersMiddleware

__all__ = [
    "create_api",
    "dependencies",
    "CachedStaticFiles",
    "SecurityConfig",
    "SecurityHeadersMiddleware",
]

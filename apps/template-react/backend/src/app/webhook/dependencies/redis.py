"""Re-export: the request dependencies live in core (``core.infrastructure.fastapi.dependencies``)."""

from core.infrastructure.fastapi.dependencies import get_redis_client

__all__ = ["get_redis_client"]

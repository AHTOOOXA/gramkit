"""Re-export: the request dependencies live in core (``core.infrastructure.fastapi.dependencies``)."""

from core.infrastructure.fastapi.dependencies import get_repo

__all__ = ["get_repo"]

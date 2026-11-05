"""Re-export: the request dependencies live in core (``core.infrastructure.fastapi.dependencies``)."""

from core.infrastructure.fastapi.dependencies import get_rabbit_producer

__all__ = ["get_rabbit_producer"]

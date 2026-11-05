"""Re-export: the request dependencies live in core (``core.infrastructure.fastapi.dependencies``)."""

from core.infrastructure.fastapi.dependencies import get_services, get_services_streaming

__all__ = ["get_services", "get_services_streaming"]

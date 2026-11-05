"""Re-export: the request dependencies live in core (``core.infrastructure.fastapi.dependencies``)."""

from core.infrastructure.fastapi.dependencies import get_arq_pool

__all__ = ["get_arq_pool"]

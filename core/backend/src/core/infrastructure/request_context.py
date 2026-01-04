"""Request context for async-safe request-scoped storage."""

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4


@dataclass
class RequestContext:
    """Request context data available throughout request lifecycle."""

    request_id: str
    path: str | None = None
    method: str | None = None
    user_id: str | None = None


# ContextVar for async-safe request-scoped storage
_request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def get_request_context() -> RequestContext | None:
    """Get current request context (returns None outside request lifecycle)."""
    return _request_context.get()


def get_request_id() -> str | None:
    """Get current request ID (convenience function)."""
    ctx = _request_context.get()
    return ctx.request_id if ctx else None


def get_user_id() -> str | None:
    """Get current user ID from request context (convenience function)."""
    ctx = _request_context.get()
    return ctx.user_id if ctx else None


def set_request_context(ctx: RequestContext) -> None:
    """Set request context (called by middleware)."""
    _request_context.set(ctx)


def set_user_context(user_id: str) -> None:
    """Update user ID in current request context (called after authentication).

    Args:
        user_id: User ID to set in the request context

    Raises:
        RuntimeError: If called outside request lifecycle (no context set)
    """
    ctx = _request_context.get()
    if ctx is None:
        raise RuntimeError("Cannot set user context outside request lifecycle")

    # Create new context with updated user_id (dataclasses are immutable by default)
    updated_ctx = RequestContext(
        request_id=ctx.request_id,
        path=ctx.path,
        method=ctx.method,
        user_id=user_id,
    )
    _request_context.set(updated_ctx)


def clear_request_context() -> None:
    """Clear request context (called by middleware on request end)."""
    _request_context.set(None)


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid4())

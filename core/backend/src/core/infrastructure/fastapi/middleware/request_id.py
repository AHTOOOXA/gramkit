"""Request ID middleware for FastAPI."""

from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from core.infrastructure.request_context import (
    RequestContext,
    clear_request_context,
    set_request_context,
)

REQUEST_ID_HEADER = "X-Request-ID"


@dataclass
class RequestIdConfig:
    """Request ID middleware configuration."""

    header_name: str = REQUEST_ID_HEADER
    generate_if_missing: bool = True
    include_in_response: bool = True


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract/generate request IDs and set request context.

    - Extracts X-Request-ID from incoming request header
    - Generates UUID if not present (configurable)
    - Sets ContextVar for request-scoped access
    - Adds X-Request-ID to response header
    """

    def __init__(self, app, config: RequestIdConfig | None = None):
        super().__init__(app)
        self.config = config or RequestIdConfig()

    async def dispatch(self, request: Request, call_next):
        # Extract or generate request ID
        request_id = request.headers.get(self.config.header_name)
        if not request_id and self.config.generate_if_missing:
            request_id = str(uuid4())

        # Set request context
        ctx = RequestContext(
            request_id=request_id or "unknown",
            path=request.url.path,
            method=request.method,
        )
        set_request_context(ctx)

        try:
            response = await call_next(request)

            # Add to response headers
            if self.config.include_in_response and request_id:
                response.headers[self.config.header_name] = request_id

            return response
        finally:
            clear_request_context()

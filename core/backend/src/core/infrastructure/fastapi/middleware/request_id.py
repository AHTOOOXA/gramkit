"""Request ID middleware for FastAPI.

Pure ASGI, not BaseHTTPMiddleware: that one runs the rest of the app in a separate task and pipes the
response body through memory channels on every request (measured: ~1 ms of CPU per request for the two).
"""

from dataclasses import dataclass
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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


class RequestIdMiddleware:
    """Extracts or generates X-Request-ID, sets the request context, echoes the id on the response."""

    def __init__(self, app: ASGIApp, config: RequestIdConfig | None = None):
        self.app = app
        self.config = config or RequestIdConfig()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = Headers(scope=scope).get(self.config.header_name)
        if not request_id and self.config.generate_if_missing:
            request_id = str(uuid4())

        set_request_context(
            RequestContext(request_id=request_id or "unknown", path=scope["path"], method=scope["method"])
        )

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start" and self.config.include_in_response and request_id:
                MutableHeaders(scope=message)[self.config.header_name] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            clear_request_context()

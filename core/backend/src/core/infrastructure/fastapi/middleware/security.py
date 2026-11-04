"""Security headers middleware for FastAPI.

Pure ASGI, not BaseHTTPMiddleware (see request_id.py).
"""

from dataclasses import dataclass

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


@dataclass
class SecurityConfig:
    """Security headers configuration."""

    csp: str
    """Content Security Policy header value"""

    hsts_enabled: bool = True
    """Enable Strict-Transport-Security header in production"""


class SecurityHeadersMiddleware:
    """Adds CSP, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection and (in prod) HSTS to every response."""

    def __init__(self, app: ASGIApp, config: SecurityConfig):
        self.app = app
        self.config = config
        headers = {
            "Content-Security-Policy": config.csp,
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
        }
        if config.hsts_enabled:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        self._headers = list(headers.items())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self._headers:
                    headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)

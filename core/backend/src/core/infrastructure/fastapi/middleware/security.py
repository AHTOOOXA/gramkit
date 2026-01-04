"""Security headers middleware for FastAPI."""

from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class SecurityConfig:
    """Security headers configuration."""

    csp: str
    """Content Security Policy header value"""

    hsts_enabled: bool = True
    """Enable Strict-Transport-Security header in production"""


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Implements defense-in-depth security headers:
    - Content Security Policy (CSP)
    - X-Frame-Options (clickjacking protection)
    - X-Content-Type-Options (MIME sniffing protection)
    - X-XSS-Protection (XSS protection)
    - Strict-Transport-Security (HTTPS enforcement in production)

    Parameterized with SecurityConfig for app-specific CSP and HSTS settings.
    """

    def __init__(self, app, config: SecurityConfig):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application
            config: Security configuration with CSP and HSTS settings
        """
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)

        # Content Security Policy - prevents XSS and injection attacks
        response.headers["Content-Security-Policy"] = self.config.csp

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTPS enforcement in production
        if self.config.hsts_enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

"""Request tracking middleware for graceful shutdown."""

import asyncio
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RequestTracker:
    """Tracks active requests for graceful shutdown coordination.

    This class maintains a count of active requests and provides mechanisms
    to signal shutdown and wait for all active requests to complete.
    """

    def __init__(self):
        self._active_requests = 0
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    @property
    def active_count(self) -> int:
        """Return the current number of active requests."""
        return self._active_requests

    @property
    def is_shutting_down(self) -> bool:
        """Return True if shutdown has been initiated."""
        return self._shutdown_event.is_set()

    def start_shutdown(self):
        """Signal that shutdown has been initiated."""
        self._shutdown_event.set()
        logger.info("Shutdown signal received, will reject new requests")

    async def wait_for_drain(self, timeout: float = 30.0) -> bool:
        """Wait for active requests to complete.

        Args:
            timeout: Maximum time to wait in seconds (default: 30.0)

        Returns:
            True if all requests drained successfully, False if timeout occurred
        """
        start = time.monotonic()
        while self._active_requests > 0:
            if time.monotonic() - start > timeout:
                logger.warning(f"Drain timeout after {timeout}s, {self._active_requests} requests still active")
                return False
            await asyncio.sleep(0.1)
        logger.info("All active requests completed successfully")
        return True


class RequestTrackerMiddleware(BaseHTTPMiddleware):
    """Middleware that tracks active requests and rejects new ones during shutdown.

    During normal operation, this middleware increments/decrements the active
    request counter. During shutdown, it rejects all new requests (except health
    checks) with a 503 Service Unavailable response.
    """

    def __init__(self, app, tracker: RequestTracker):
        super().__init__(app)
        self.tracker = tracker

    async def dispatch(self, request: Request, call_next):
        # Allow health check endpoints during shutdown (for liveness probes)
        if self.tracker.is_shutting_down and request.url.path not in ("/health", "/ready"):
            return Response(status_code=503, content="Service shutting down")

        # Track this request
        async with self.tracker._lock:
            self.tracker._active_requests += 1

        try:
            return await call_next(request)
        finally:
            async with self.tracker._lock:
                self.tracker._active_requests -= 1

"""One log line per HTTP request: method, path, status, duration.

The logging filter adds ``[req:…] [user:…]`` to every line (``get_user`` sets the user in the request
context), so this one line says who called what, how it ended and how long it took. It replaces uvicorn's
access log (run uvicorn with ``--no-access-log``), which has neither the user nor the duration.

The query string is left out on purpose: it can carry the user's own words (a question, a search).
Streaming responses are logged when the stream ends, so their duration is the whole stream.
Pure ASGI, like the other core middlewares, so the request context set downstream is visible here.
"""

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.infrastructure.logging import get_logger

logger = get_logger("core.access")


class AccessLogMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status = 500  # an exception that escapes the app ends as a 500 from the error middleware

        async def send_with_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            ms = (time.perf_counter() - started) * 1000
            logger.info("%s %s %s %.0fms", scope["method"], scope["path"], status, ms)

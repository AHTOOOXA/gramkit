"""Process-wide logging: one line format, written to stdout off the event loop.

``setup_logging()`` puts a ``QueueHandler`` on the root logger and moves the real stdout handler into a
``QueueListener`` thread. A ``StreamHandler.flush()`` is a blocking write to the container's stdout pipe: on the
event loop it was the largest single cost of a simple request (the access-log line). Now the calling thread only
renders the message (and any traceback) and puts the record on a queue; the listener thread formats and writes it.

What stays in the calling thread, on purpose:
- ``RequestContextFilter`` (on the queue handler): the request id and user live in contextvars, which the
  listener thread can't see.
- the message and the traceback text (``QueueHandler.prepare``): args and traceback frames belong to the caller.

Every process that calls ``setup_infrastructure()`` gets this (webhook, bot, worker), and so do scripts
(``ScriptRunner``). ``shutdown_logging()`` drains the queue and goes back to direct writes; it runs from an atexit
hook and at the end of core's FastAPI lifespan.
"""

import atexit
import logging
import queue
import sys
from logging.handlers import QueueHandler, QueueListener

from core.infrastructure.request_context import get_request_id, get_user_id


class RequestContextFilter(logging.Filter):
    """Inject request_id and user_id into all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        record.user_id = get_user_id() or "-"
        return True


COLOR_FORMAT = (
    "\033[1;36m%(filename)s:%(lineno)d\033[0m "
    "#%(levelname)-8s "
    "\033[1;32m[%(asctime)s]\033[0m "
    "\033[1;35m[req:%(request_id)s]\033[0m "
    "\033[1;33m[user:%(user_id)s]\033[0m "
    "- \033[1;34m%(name)s\033[0m "
    "- %(message)s"
)
# Production logs end up in container log files and the Dokploy viewer: no ANSI codes (they made every line
# ~40% longer and broke grep).
PLAIN_FORMAT = "%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] [req:%(request_id)s] [user:%(user_id)s] - %(name)s - %(message)s"

# The running listener, the queue handler that feeds it and the stdout handler it writes with (None until
# setup_logging(), and again after shutdown_logging()).
_listener: QueueListener | None = None
_queue_handler: QueueHandler | None = None
_stream: logging.StreamHandler | None = None
_atexit_registered = False


def _colored() -> bool:
    try:
        from core.infrastructure.config import settings

        return bool(settings.debug)
    except Exception:
        return True


def setup_logging():
    """Configure the root logger. Safe to call again: the previous listener is stopped first, never doubled."""
    global _listener, _queue_handler, _stream, _atexit_registered

    shutdown_logging()

    log_queue: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
    queue_handler = QueueHandler(log_queue)
    # Renders only the message (+ traceback) before queueing; the line format is applied in the listener. Set
    # explicitly, otherwise basicConfig would give this handler the full format and every line would get it twice.
    queue_handler.setFormatter(logging.Formatter())
    queue_handler.addFilter(RequestContextFilter())

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(logging.Formatter(COLOR_FORMAT if _colored() else PLAIN_FORMAT))
    listener = QueueListener(log_queue, stream)
    queue_handler.listener = listener

    logging.basicConfig(level=logging.INFO, force=True, handlers=[queue_handler])
    listener.start()
    _listener, _queue_handler, _stream = listener, queue_handler, stream

    if not _atexit_registered:
        atexit.register(shutdown_logging)
        _atexit_registered = True


def shutdown_logging() -> None:
    """Write out every queued line and stop the listener thread. Idempotent.

    Lines logged afterwards are still printed: the root logger's queue handler is swapped for a direct stdout
    handler with the same format (synchronous again, which no longer matters at shutdown).
    """
    global _listener, _queue_handler, _stream

    listener, queue_handler, stream = _listener, _queue_handler, _stream
    _listener = _queue_handler = _stream = None
    if listener is None or queue_handler is None or stream is None:
        return

    root = logging.getLogger()
    if queue_handler in root.handlers:
        # A second handler on the same stream, with the filter of its own: the listener's handler must not get it,
        # it would overwrite the request id and user with the listener thread's empty context.
        direct = logging.StreamHandler(stream.stream)
        direct.setFormatter(stream.formatter)
        direct.addFilter(RequestContextFilter())
        # Swap first, then stop: whatever was logged before the swap is already queued, and stop() drains it.
        root.addHandler(direct)
        root.removeHandler(queue_handler)
    queue_handler.close()
    # Like logging.shutdown(): at interpreter exit stdout may already be closed; a traceback from an atexit hook
    # would be noise, and nothing can be written anyway.
    try:
        listener.stop()
        stream.flush()
    except (OSError, ValueError):
        pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

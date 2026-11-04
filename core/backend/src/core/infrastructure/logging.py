import logging
import sys

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


def _colored() -> bool:
    try:
        from core.infrastructure.config import settings

        return bool(settings.debug)
    except Exception:
        return True


def setup_logging():
    log_format = COLOR_FORMAT if _colored() else PLAIN_FORMAT

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestContextFilter())

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        force=True,
        handlers=[handler],
        # handlers=[handler, logfire.LogfireLoggingHandler()],
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

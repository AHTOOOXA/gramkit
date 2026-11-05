"""Is this exception the infrastructure failing (DB, Redis, network), not the request or our code?

The answer decides the HTTP status: an infrastructure failure is a 503 the client retries, never a 401
("not logged in") or a guest fallback. Under load, Docker DNS (``[Errno -3] Temporary failure in name
resolution``), a full pool or a restarting Postgres all surface while opening the first connection of a
request, which for most requests is the auth lookup.

What counts:

- SQLAlchemy: ``OperationalError``, ``InterfaceError``, pool ``TimeoutError``, ``DisconnectionError``, and any
  ``DBAPIError`` that invalidated its connection;
- asyncpg (raw, e.g. while connecting): connection errors (class 08), too many connections / out of resources
  (53), operator intervention (57: shutdown, "cannot connect now", statement timeout);
- Redis: ``ConnectionError`` (incl. busy loading) and ``TimeoutError``;
- ``OSError`` from sockets: ``socket.gaierror``, refused/reset connections, timeouts (``asyncio.TimeoutError`` is
  the builtin ``TimeoutError``), "network unreachable", but not the filesystem ``OSError`` subclasses.

The exception's ``__cause__`` chain and SQLAlchemy's ``.orig`` are checked too: SQLAlchemy and redis wrap the
socket error they hit.
"""

import asyncpg.exceptions as asyncpg_exc
import redis.exceptions as redis_exc
import sqlalchemy.exc as sa_exc

_INFRA_ERRORS: tuple[type[BaseException], ...] = (
    sa_exc.OperationalError,
    sa_exc.InterfaceError,
    sa_exc.TimeoutError,
    sa_exc.DisconnectionError,
    asyncpg_exc.PostgresConnectionError,
    asyncpg_exc.InsufficientResourcesError,
    asyncpg_exc.OperatorInterventionError,
    redis_exc.ConnectionError,
    redis_exc.TimeoutError,
)

# OSError subclasses that are a file, not a network, failing.
_FILESYSTEM_ERRORS: tuple[type[OSError], ...] = (
    FileNotFoundError,
    FileExistsError,
    IsADirectoryError,
    NotADirectoryError,
    PermissionError,
)

_MAX_CHAIN = 8


def _is_infra(exc: BaseException) -> bool:
    if isinstance(exc, _INFRA_ERRORS):
        return True
    if isinstance(exc, sa_exc.DBAPIError) and exc.connection_invalidated:
        return True
    return isinstance(exc, OSError) and not isinstance(exc, _FILESYSTEM_ERRORS)


def is_infrastructure_error(exc: BaseException) -> bool:
    """True when ``exc`` (or what it wraps) is the DB, Redis or the network failing: answer 503, not 4xx."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen and len(seen) < _MAX_CHAIN:
        if _is_infra(current):
            return True
        seen.add(id(current))
        orig = getattr(current, "orig", None)  # sqlalchemy.exc.DBAPIError: the driver's exception
        current = orig if isinstance(orig, BaseException) else current.__cause__
    return False

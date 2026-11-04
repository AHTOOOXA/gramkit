from arq.connections import ArqRedis  # not `from arq`: pyright, without the venv, resolves `arq` to this file
from fastapi import Request


async def get_arq_pool(request: Request) -> ArqRedis | None:
    """The worker's arq pool, created once in create_api's lifespan (core.infrastructure.fastapi.clients).

    Never create_pool() per request: that is a new Redis connection (DNS lookup + PING) every time. None
    under an ASGI test client (no lifespan; tests override this dependency).
    """
    return getattr(request.app.state, "arq", None)

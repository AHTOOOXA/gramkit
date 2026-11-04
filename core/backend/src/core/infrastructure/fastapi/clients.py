"""Process-wide clients for the webhook: opened once in create_api's lifespan, read by request dependencies.

A request must not build these itself. aiogram's ``Bot()`` creates an aiohttp session, and with it an SSL
context that loads the whole CA bundle (~7 ms of CPU and a few hundred KB per request; under load the heap
grows with the requests in flight until the container is OOM-killed). ``arq.create_pool()`` opens a new Redis
connection, with a DNS lookup and a PING, every time. Both are made for reuse: one per worker process.

Apps read them through their ``get_bot`` / ``get_arq_pool`` dependencies (``request.app.state``), so tests can
still override those dependencies. ASGI test clients don't run the lifespan; the attributes are then absent and
the dependencies return ``None``.
"""

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from core.infrastructure.config import settings
from core.infrastructure.logging import get_logger
from core.infrastructure.telegram.retry import with_retries

logger = get_logger(__name__)


async def open_clients(app: FastAPI) -> None:
    """Create the worker's Bot (when a token is set) and arq pool and store them on ``app.state``."""
    token = settings.bot.token
    app.state.bot = (
        with_retries(Bot(token=token, default=DefaultBotProperties(parse_mode="Markdown"))) if token else None
    )
    app.state.arq = await create_pool(
        RedisSettings(host=settings.redis.host, port=settings.redis.port, password=settings.redis.password)
    )


async def close_clients(app: FastAPI) -> None:
    arq = getattr(app.state, "arq", None)
    if arq is not None:
        try:
            await arq.close()
        except Exception as e:
            logger.warning(f"arq pool close failed: {e}")
    bot = getattr(app.state, "bot", None)
    if bot is not None:
        try:
            await bot.session.close()
        except Exception as e:
            logger.warning(f"bot session close failed: {e}")

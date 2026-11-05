"""One fallback ``Bot`` per process, for code that has no bot handed to it.

Building an aiogram ``Bot()`` creates an aiohttp session and an SSL context that loads the whole CA
bundle: milliseconds of CPU and a few hundred KB each time (``core.infrastructure.fastapi.clients``).
Code that runs per request or per message must not do it. Prefer the process bot the caller already
has (``services.bot``: ``app.state.bot`` in the webhook, ``ctx["bot"]`` in the worker, the
dispatcher's bot in the bot process). Where there is none (scripts, ASGI tests without the lifespan,
module-level helpers like ``alert_owners``), use ``get_shared_bot()``: it is created on first use and
reused after that.

The bot has no ``DefaultBotProperties``, like the per-call bots it replaces, so callers pass
``parse_mode`` themselves. Its aiohttp session belongs to the event loop it first ran on, so a new
loop (each ``asyncio.run``, each test) gets a fresh bot instead of one bound to a closed loop.
"""

import asyncio

from aiogram import Bot

from core.infrastructure.logging import get_logger
from core.infrastructure.telegram.retry import with_retries

logger = get_logger(__name__)

_bot: Bot | None = None
_loop: asyncio.AbstractEventLoop | None = None


def _running_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def get_shared_bot() -> Bot:
    """The process-wide fallback bot (``with_retries``, token from ``settings.bot.token``)."""
    global _bot, _loop
    loop = _running_loop()
    if _bot is None or (loop is not None and _loop is not None and loop is not _loop):
        # Imported here (not at module level) so tests can patch core.infrastructure.config.settings.
        from core.infrastructure.config import settings

        _bot = with_retries(Bot(token=settings.bot.token))
        _loop = loop
    elif _loop is None:
        _loop = loop
    return _bot


async def close_shared_bot() -> None:
    """Close the fallback bot's session, if one was created on this loop (process shutdown)."""
    global _bot, _loop
    bot, loop = _bot, _loop
    _bot, _loop = None, None
    if bot is None or (loop is not None and loop is not _running_loop()):
        return
    try:
        await bot.session.close()
    except Exception as e:
        logger.warning(f"shared bot session close failed: {e}")

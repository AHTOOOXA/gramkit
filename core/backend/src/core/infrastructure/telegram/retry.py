"""Retries for Telegram Bot API requests.

aiogram doesn't retry anything by itself: a connection reset on the way to api.telegram.org (one
lost a nightly backup on 2026-10-29) or a Telegram 5xx fails the call outright. Every ``Bot`` we
create goes through ``with_retries`` so those are retried a couple of times with a short pause.

What is retried:
- network errors (connection reset/refused, timeouts, DNS) and Telegram 5xx: ``attempts`` tries
  in total, waiting ``base_delay``, then twice that, ...;
- a flood limit (``TelegramRetryAfter``) Telegram asks to wait at most ``max_retry_after``
  seconds for. Longer waits are raised to the caller (``MessageService`` sleeps them out once), so
  a webhook request is never held for minutes here.

Not retried: client errors (bad request, forbidden: they won't change) and ``getUpdates`` (the
polling loop has its own backoff). A timed-out send may still have reached Telegram, so a retry
can, rarely, deliver a message twice; for backups, alerts and notifications that beats losing it.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError
from aiogram.methods import GetUpdates, TelegramMethod
from aiogram.methods.base import Response, TelegramType

logger = logging.getLogger(__name__)


class TelegramRetryMiddleware(BaseRequestMiddleware):
    def __init__(self, attempts: int = 3, base_delay: float = 1.0, max_retry_after: float = 30.0) -> None:
        self.attempts = attempts
        self.base_delay = base_delay
        self.max_retry_after = max_retry_after

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        if isinstance(method, GetUpdates):
            return await make_request(bot, method)

        for attempt in range(1, self.attempts + 1):
            try:
                return await make_request(bot, method)
            except TelegramRetryAfter as e:
                if attempt == self.attempts or e.retry_after > self.max_retry_after:
                    raise
                error: Exception = e
                delay = float(e.retry_after)
            except (TelegramNetworkError, TelegramServerError) as e:
                if attempt == self.attempts:
                    raise
                error = e
                delay = self.base_delay * 2 ** (attempt - 1)
            logger.warning(
                "Telegram %s failed (attempt %d/%d): %s — retrying in %.1fs",
                type(method).__name__,
                attempt,
                self.attempts,
                error,
                delay,
            )
            await asyncio.sleep(delay)
        raise AssertionError("unreachable: the last attempt returns or raises")


def with_retries(bot: Bot) -> Bot:
    """Attach ``TelegramRetryMiddleware`` to the bot's session and return the bot."""
    bot.session.middleware(TelegramRetryMiddleware())
    return bot

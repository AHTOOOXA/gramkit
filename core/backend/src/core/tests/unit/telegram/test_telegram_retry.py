"""TelegramRetryMiddleware: which Bot API failures are retried, how often, and what's left alone.

Regression for 2026-10-29: a connection reset on the upload to api.telegram.org lost a staging
stack's nightly backup — aiogram retried nothing.
"""

from unittest.mock import AsyncMock, patch

import pytest
from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.methods import GetUpdates, SendMessage

from core.infrastructure.telegram.retry import TelegramRetryMiddleware, with_retries

METHOD = SendMessage(chat_id=1, text="hi")
OK = object()


def _make_request(*outcomes):
    """A fake next-in-chain that raises/returns ``outcomes`` in order."""
    calls = AsyncMock(side_effect=list(outcomes))

    async def make_request(bot, method):
        return await calls(bot, method)

    return make_request, calls


@pytest.fixture
def sleep():
    with patch("core.infrastructure.telegram.retry.asyncio.sleep", new=AsyncMock()) as s:
        yield s


async def test_network_error_is_retried_until_it_succeeds(sleep):
    make_request, calls = _make_request(
        TelegramNetworkError(METHOD, "ClientConnectorError: Connection reset by peer"),
        TelegramNetworkError(METHOD, "timeout"),
        OK,
    )
    result = await TelegramRetryMiddleware(attempts=3, base_delay=1.0)(make_request, None, METHOD)
    assert result is OK
    assert calls.await_count == 3
    assert [c.args[0] for c in sleep.await_args_list] == [1.0, 2.0]  # 1s, then twice that


async def test_server_error_is_retried(sleep):
    make_request, calls = _make_request(TelegramServerError(METHOD, "Internal Server Error"), OK)
    assert await TelegramRetryMiddleware()(make_request, None, METHOD) is OK
    assert calls.await_count == 2


async def test_gives_up_after_the_last_attempt(sleep):
    make_request, calls = _make_request(*[TelegramNetworkError(METHOD, "reset")] * 3)
    with pytest.raises(TelegramNetworkError):
        await TelegramRetryMiddleware(attempts=3)(make_request, None, METHOD)
    assert calls.await_count == 3
    assert sleep.await_count == 2


async def test_short_flood_limit_waits_as_asked_then_retries(sleep):
    make_request, calls = _make_request(TelegramRetryAfter(METHOD, "Flood control", retry_after=3), OK)
    assert await TelegramRetryMiddleware(max_retry_after=30)(make_request, None, METHOD) is OK
    assert calls.await_count == 2
    sleep.assert_awaited_once_with(3.0)


async def test_long_flood_limit_is_raised_to_the_caller(sleep):
    """MessageService sleeps long waits out; a webhook request mustn't be held here for minutes."""
    make_request, calls = _make_request(TelegramRetryAfter(METHOD, "Flood control", retry_after=120))
    with pytest.raises(TelegramRetryAfter):
        await TelegramRetryMiddleware(max_retry_after=30)(make_request, None, METHOD)
    assert calls.await_count == 1
    sleep.assert_not_awaited()


async def test_client_errors_are_not_retried(sleep):
    make_request, calls = _make_request(TelegramBadRequest(METHOD, "chat not found"))
    with pytest.raises(TelegramBadRequest):
        await TelegramRetryMiddleware()(make_request, None, METHOD)
    assert calls.await_count == 1
    sleep.assert_not_awaited()


async def test_get_updates_is_left_to_the_polling_loop(sleep):
    get_updates = GetUpdates()
    make_request, calls = _make_request(TelegramNetworkError(get_updates, "reset"))
    with pytest.raises(TelegramNetworkError):
        await TelegramRetryMiddleware()(make_request, None, get_updates)
    assert calls.await_count == 1


async def test_with_retries_attaches_the_middleware():
    bot = with_retries(Bot(token="123456:" + "A" * 35))
    try:
        assert any(isinstance(m, TelegramRetryMiddleware) for m in bot.session.middleware)
    finally:
        await bot.session.close()

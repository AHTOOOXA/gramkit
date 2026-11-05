"""PaymentsService and the Telegram Stars provider must not build an aiogram ``Bot`` per request.

Regression (2026-11, load test): ``GET /payments/products`` spent 13.5 ms of CPU per
request, 76% of it in ``TelegramStarsProvider.__init__`` building ``Bot()`` (aiohttp session + SSL
context with the whole CA bundle), because ``services.payments`` built every provider eagerly.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from aiogram import Bot

from core.infrastructure.database.models.enums import PaymentProvider
from core.infrastructure.telegram import shared_bot
from core.services.payments.providers.telegram_stars import TelegramStarsProvider
from core.services.payments.service import PaymentsService

STARS = PaymentProvider.TELEGRAM_STARS.value
TEST_SETTINGS = SimpleNamespace(bot=SimpleNamespace(token="123:test"))


@pytest.fixture(autouse=True)
def _fresh_shared_bot():
    shared_bot._bot, shared_bot._loop = None, None
    yield
    shared_bot._bot, shared_bot._loop = None, None


def _forbid_bot_construction():
    return patch.object(Bot, "__init__", side_effect=AssertionError("aiogram.Bot() constructed"))


def _payments(bot) -> PaymentsService:
    services = SimpleNamespace(bot=bot)
    return PaymentsService(MagicMock(), None, services, bot, products=MagicMock())


@pytest.mark.regression
class TestNoBotPerRequest:
    def test_constructing_payments_service_builds_no_provider_and_no_bot(self):
        with _forbid_bot_construction(), patch("core.services.payments.service.get_provider") as get_provider:
            payments = _payments(bot=None)
            assert set(payments.providers) == {PaymentProvider.YOOKASSA.value, STARS}
            assert STARS in payments.providers
            assert payments.providers.get(PaymentProvider.GIFT) is None

        get_provider.assert_not_called()

    def test_providers_are_built_once_on_first_lookup(self):
        with patch("core.services.payments.service.get_provider", side_effect=lambda *a: object()) as get_provider:
            payments = _payments(bot=None)
            first = payments.providers[STARS]
            assert payments.providers.get(PaymentProvider.TELEGRAM_STARS) is first

        assert get_provider.call_count == 1

    def test_stars_provider_construction_builds_no_bot(self):
        with _forbid_bot_construction():
            provider = _payments(bot=None).providers[STARS]

        assert isinstance(provider, TelegramStarsProvider)

    def test_stars_provider_uses_the_services_bot(self):
        process_bot = MagicMock(spec=Bot)
        with _forbid_bot_construction():
            provider = _payments(bot=process_bot).providers[STARS]
            assert provider.bot is process_bot

    async def test_without_a_process_bot_every_provider_shares_one_fallback_bot(self):
        with patch("core.infrastructure.config.settings", new=TEST_SETTINGS):
            first = TelegramStarsProvider(MagicMock(), SimpleNamespace(bot=None), MagicMock()).bot
            # Not an aiogram Bot (a test double, an app's null bot): don't reuse it for payments.
            second = TelegramStarsProvider(MagicMock(), SimpleNamespace(bot=object()), MagicMock()).bot

        assert isinstance(first, Bot)
        assert second is first
        await shared_bot.close_shared_bot()

    def test_an_assigned_bot_overrides_the_lazy_one(self):
        provider = TelegramStarsProvider(MagicMock(), SimpleNamespace(bot=MagicMock(spec=Bot)), MagicMock())
        mock = MagicMock()
        provider.bot = mock
        assert provider.bot is mock


@pytest.mark.business_logic
class TestSharedBot:
    async def test_one_bot_per_event_loop(self):
        with patch("core.infrastructure.config.settings", new=TEST_SETTINGS):
            assert shared_bot.get_shared_bot() is shared_bot.get_shared_bot()
        await shared_bot.close_shared_bot()
        assert shared_bot._bot is None

    async def test_a_bot_from_another_loop_is_replaced(self):
        stale = MagicMock(spec=Bot)
        shared_bot._bot, shared_bot._loop = stale, object()  # a loop that is not running
        with patch("core.infrastructure.config.settings", new=TEST_SETTINGS):
            fresh = shared_bot.get_shared_bot()

        assert fresh is not stale and isinstance(fresh, Bot)
        await shared_bot.close_shared_bot()

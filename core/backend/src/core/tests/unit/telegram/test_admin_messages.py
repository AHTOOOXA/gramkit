"""Unit tests for admin-message formatting helpers and the degrading sender.

The sender's contract: an admin alert is never lost to formatting — a rejected rich body
falls back to HTML, rejected HTML falls back to plain text.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest

from core.infrastructure.telegram.admin_messages import (
    alert_owners,
    announce_start,
    bullet_list,
    esc,
    fmt_delta,
    fmt_money,
    fmt_money_map,
    html_to_plain,
    send_admin_message,
    tags,
    user_ref,
    user_tag,
)


def _bad_request(text: str = "can't parse entities") -> TelegramBadRequest:
    return TelegramBadRequest(method=MagicMock(), message=text)


class FakeBot:
    """Records sends; each method can be told to raise."""

    def __init__(self, rich_error: Exception | None = None, html_error: Exception | None = None):
        self.rich_error = rich_error
        self.html_error = html_error
        self.rich: list[dict] = []
        self.sent: list[dict] = []

    async def send_rich_message(self, chat_id, rich_message, **kwargs):
        if self.rich_error:
            raise self.rich_error
        self.rich.append({"chat_id": chat_id, "html": rich_message.html, **kwargs})

    async def send_message(self, chat_id, text, parse_mode=None, **kwargs):
        if parse_mode == "HTML" and self.html_error:
            raise self.html_error
        self.sent.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode, **kwargs})


@pytest.mark.business_logic
class TestFormatting:
    def test_esc_neutralises_html(self):
        assert esc('<3 & "x"') == "&lt;3 &amp; &quot;x&quot;"

    def test_user_ref_links_telegram_handle(self):
        user = SimpleNamespace(tg_username="anna", username="anna_app", telegram_id=42)
        assert user_ref(user) == '<a href="tg://user?id=42">@anna</a>'

    def test_user_ref_without_username_never_renders_at_none(self):
        user = SimpleNamespace(tg_username=None, username=None, display_name="Маша <3", telegram_id=None, id="abc")
        ref = user_ref(user)
        assert "@None" not in ref
        assert ref == "Маша &lt;3"

    def test_user_ref_falls_back_to_short_id(self):
        user = SimpleNamespace(id="0198a1b2-c3d4-7000")
        assert user_ref(user) == "user 0198a1b2"

    def test_fmt_money(self):
        assert fmt_money(1490.0, "RUB") == "1 490 ₽"
        assert fmt_money(150, "XTR") == "150 ⭐"
        assert fmt_money(9.5, "USD") == "9.50 $"

    def test_fmt_money_map_never_sums_currencies(self):
        assert fmt_money_map({"XTR": 50.0, "RUB": 399.0}) == "399 ₽ + 50 ⭐"
        assert fmt_money_map({}) == "0"

    @pytest.mark.parametrize(
        ("current", "previous", "expected"),
        [(112, 100, "▲12%"), (95, 100, "▼5%"), (100, 100, "="), (3, 0, "new"), (0, 0, "=")],
    )
    def test_fmt_delta(self, current, previous, expected):
        assert fmt_delta(current, previous) == expected

    def test_bullet_list_truncates(self):
        out = bullet_list([str(i) for i in range(5)], limit=2)
        assert out.splitlines() == ["• 0", "• 1", "<i>…and 3 more</i>"]

    def test_tags_are_valid_telegram_hashtags(self):
        assert tags("purchase", "u_anna.k-1", "") == "#purchase #u_anna_k_1"

    def test_user_tag_prefers_handle_then_short_id(self):
        assert user_tag(SimpleNamespace(tg_username="anna", username="x")) == "u_anna"
        assert user_tag(SimpleNamespace(tg_username=None, username=None, id="0198a1b2-c3d4")) == "u_0198a1b2"

    def test_html_to_plain(self):
        assert html_to_plain('<b>Hi</b> <a href="x">@a</a> &lt;3<br>bye') == "Hi @a <3\nbye"


@pytest.mark.business_logic
class TestSendAdminMessage:
    async def test_rich_body_is_preferred(self):
        bot = FakeBot()
        sent = await send_admin_message(bot, "<b>fallback</b>", rich_html="<h3>rich</h3>", chat_ids=[1], silent=True)

        assert sent == 1
        assert bot.rich == [{"chat_id": 1, "html": "<h3>rich</h3>", "disable_notification": True}]
        assert bot.sent == []

    async def test_rejected_rich_falls_back_to_html(self):
        bot = FakeBot(rich_error=_bad_request("rich messages are not supported"))
        sent = await send_admin_message(bot, "<b>fallback</b>", rich_html="<h3>rich</h3>", chat_ids=[1])

        assert sent == 1
        assert bot.sent[0]["text"] == "<b>fallback</b>"
        assert bot.sent[0]["parse_mode"] == "HTML"

    async def test_rejected_html_falls_back_to_plain_text(self):
        bot = FakeBot(html_error=_bad_request())
        sent = await send_admin_message(bot, "<b>Purchase</b> &lt;3", chat_ids=[1])

        assert sent == 1
        assert bot.sent == [{"chat_id": 1, "text": "Purchase <3", "parse_mode": None, "disable_notification": False}]

    async def test_one_failing_admin_does_not_block_others(self):
        class FlakyBot(FakeBot):
            async def send_message(self, chat_id, text, parse_mode=None, **kwargs):
                if chat_id == 2:
                    raise RuntimeError("network")
                await super().send_message(chat_id, text, parse_mode=parse_mode, **kwargs)

        bot = FlakyBot()
        sent = await send_admin_message(bot, "hi", chat_ids=[1, 2, 3])

        assert sent == 2
        assert [m["chat_id"] for m in bot.sent] == [1, 3]

    async def test_defaults_to_all_owners(self):
        bot = FakeBot()
        # An explicit `new`: a bare patch() inspects the original — the lazy settings accessor,
        # which imports app.config and fails in core-only CI.
        settings = SimpleNamespace(rbac=SimpleNamespace(owner_ids=[7, 8]))
        with patch("core.infrastructure.config.settings", new=settings):
            sent = await send_admin_message(bot, "hi")

        assert sent == 2
        assert {m["chat_id"] for m in bot.sent} == {7, 8}


def _settings(*, debug: bool) -> SimpleNamespace:
    return SimpleNamespace(
        debug=debug,
        app_name="myapp",
        observability=SimpleNamespace(logfire_environment="production"),
        rbac=SimpleNamespace(owner_ids=[7, 8]),
        bot=SimpleNamespace(token="123:test"),
    )


@pytest.mark.business_logic
class TestAnnounceStart:
    async def test_prod_start_is_announced_silently_to_every_owner(self):
        bot = FakeBot()
        with patch("core.infrastructure.config.settings", new=_settings(debug=False)):
            await announce_start("worker", "1.2.0", bot)

        assert {m["chat_id"] for m in bot.sent} == {7, 8}
        text = bot.sent[0]["text"]
        assert "myapp 1.2.0" in text and "worker started" in text and "#deploy" in text
        assert all(m["disable_notification"] is True for m in bot.sent)

    async def test_debug_start_is_not_announced(self):
        bot = FakeBot()
        with patch("core.infrastructure.config.settings", new=_settings(debug=True)):
            await announce_start("webhook", "1.2.0", bot)

        assert bot.sent == []

    async def test_telegram_failure_does_not_break_startup(self):
        bot = MagicMock()
        bot.send_message.side_effect = RuntimeError("telegram down")
        with patch("core.infrastructure.config.settings", new=_settings(debug=False)):
            await announce_start("bot", "1.2.0", bot)  # must not raise


class _ClosableFakeBot(FakeBot):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.session = MagicMock()
        self.session.close = self._close
        self.closed = False

    async def _close(self):
        self.closed = True


@pytest.mark.business_logic
class TestAlertOwners:
    async def test_prod_alert_reaches_every_owner_with_sound_and_closes_its_bot(self):
        bot = _ClosableFakeBot()
        with (
            patch("core.infrastructure.config.settings", new=_settings(debug=False)),
            patch("core.infrastructure.telegram.admin_messages.Bot", return_value=bot),
        ):
            await alert_owners("🚨 webhook failed")

        assert {m["chat_id"] for m in bot.sent} == {7, 8}
        assert all(m["disable_notification"] is False for m in bot.sent)
        assert bot.closed

    async def test_debug_sends_nothing(self):
        with (
            patch("core.infrastructure.config.settings", new=_settings(debug=True)),
            patch("core.infrastructure.telegram.admin_messages.Bot") as bot_cls,
        ):
            await alert_owners("🚨 webhook failed")

        bot_cls.assert_not_called()

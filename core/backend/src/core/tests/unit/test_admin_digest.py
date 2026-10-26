"""Daily admin digest rendering (core.services.admin_digest) — pure, no DB."""

import re
from datetime import UTC, datetime, timedelta

import pytest

from core.infrastructure.telegram.admin_messages import NBSP
from core.services.admin_digest import DailyDigest, DigestPeriod, render_error, render_rich, render_text
from core.services.admin_metrics import DigestRow


def _digest(**overrides) -> DailyDigest:
    end = datetime(2026, 9, 26, 1, 55, tzinfo=UTC)
    fields = {
        "window_start": end - timedelta(hours=23, minutes=55),
        "window_end": end,
        "day": DigestPeriod({"RUB": 1490.0}, new_users=3, purchases=1, renewals=2),
        "week": DigestPeriod({"RUB": 4980.0, "XTR": 150.0}, new_users=18, purchases=4, renewals=5),
        "prev_week": DigestPeriod({"RUB": 4450.0}, new_users=19, purchases=4, renewals=3),
        "dau": 6,
        "wau": 27,
        "mau": 59,
        "active_subs": 7,
        "app_title": "Demo",
    }
    return DailyDigest(**{**fields, **overrides})


def _labels(rich: str) -> list[str]:
    return re.findall(r"<tr><td>([^<]*)</td>", rich)


@pytest.mark.business_logic
class TestDigestRendering:
    def test_rich_has_table_with_weekly_context(self):
        rich = render_rich(_digest())

        assert rich.startswith("<h3>📊 Demo · Fri 25 Sep</h3>")
        assert "<table bordered striped compact>" in rich
        assert "<tr><th></th><th>Day</th><th>7d</th><th>Δ</th></tr>" in rich
        # Revenue: day, 7d (currencies kept apart), delta on the main currency (RUB 4980 vs 4450).
        assert f'<td>Revenue</td><td align="right">1{NBSP}490{NBSP}₽</td>' in rich
        assert f"4{NBSP}980{NBSP}₽ + 150{NBSP}⭐" in rich
        assert "▲12%" in rich
        assert "<p>👥 DAU 6 · WAU 27 · MAU 59</p><p>💎 7 active subs</p>" in rich
        assert "<footer>#digest · Δ = last 7 days vs the 7 days before</footer>" in rich
        assert _labels(rich) == ["Revenue", "New users", "Purchases", "Renewals", "Expired"]

    def test_bold_is_reserved_for_the_title(self):
        text = render_text(_digest())

        assert "<b>" not in render_rich(_digest())  # title is an <h3>
        assert text.count("<b>") == 1
        assert text.startswith("<b>📊 Demo · Fri 25 Sep</b>")

    def test_text_fallback_is_an_aligned_monospace_table(self):
        text = render_text(_digest(rows=[(30, DigestRow("Orders", 3, 20, 18))]))
        table = text[text.index("<pre>") + 5 : text.index("</pre>")].splitlines()

        assert len({len(line) for line in table}) == 1  # every row padded to the same width
        assert table[0].split() == ["Day", "7d", "Δ"]
        assert [line.split()[0] for line in table[1:]] == [
            "Revenue",
            "New",
            "Orders",
            "Purchases",
            "Renewals",
            "Expired",
        ]

    def test_app_rows_merge_into_the_table_by_order(self):
        rows = [(30, DigestRow("Orders", 3, 20, 18)), (99, DigestRow("Refunds", 0, 1, 0))]
        rich = render_rich(_digest(rows=rows))

        assert _labels(rich) == ["Revenue", "New users", "Orders", "Purchases", "Renewals", "Expired", "Refunds"]
        assert '<td>Orders</td><td align="right">3</td><td align="right">20</td><td align="right">▲11%</td>' in rich

    def test_app_line_renders_under_the_table(self):
        rich = render_rich(_digest(rows=[(100, DigestRow("", line="⭐ <i>12</i> reviews"))]))

        assert "<p>💎 7 active subs</p><p>⭐ <i>12</i> reviews</p>" in rich
        assert _labels(rich) == ["Revenue", "New users", "Purchases", "Renewals", "Expired"]

    def test_app_warnings_come_before_core_ones(self):
        digest = _digest(
            week=DigestPeriod(),
            past_due=2,
            rows=[(30, DigestRow("Orders", warning="No orders today"))],
        )
        rich = render_rich(digest)

        block = rich[rich.index("<blockquote>") : rich.index("</blockquote>")]
        assert block.index("No orders today") < block.index("No revenue in 7 days") < block.index("2 subscriptions")
        assert "2 subscriptions past due — revenue at risk" in block

    def test_one_past_due_subscription_is_singular(self):
        assert "1 subscription past due" in render_rich(_digest(past_due=1))

    def test_app_label_and_warning_are_escaped(self):
        rich = render_rich(_digest(rows=[(30, DigestRow("A<B", warning="x < y & z"))]))

        assert "<td>A&lt;B</td>" in rich
        assert "⚠️ x &lt; y &amp; z" in rich

    def test_canceled_today_is_appended_to_the_subs_line(self):
        assert "💎 7 active subs · 2 turned off auto-renew" in render_text(_digest(canceled_day=2))

    def test_partial_day_is_labelled(self):
        now = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
        digest = _digest(window_start=now - timedelta(hours=10), window_end=now)

        assert "(so far)" in render_rich(digest)
        assert digest.partial is True
        assert _digest().partial is False

    def test_error_digest_escapes_the_exception(self):
        text = render_error(_digest(error="relation <users> does not exist"))

        assert "❌ Failed to gather statistics:" in text
        assert "&lt;users&gt;" in text

    def test_app_title_is_escaped(self):
        assert render_rich(_digest(app_title="A&B")).startswith("<h3>📊 A&amp;B · ")

    @pytest.mark.parametrize("locale", ["en", "ru"])
    def test_every_text_resolves_in_both_locales(self, locale: str):
        digest = _digest(week=DigestPeriod(), past_due=1, canceled_day=1)
        partial = _digest(window_end=_digest().window_start + timedelta(hours=1))

        for rendered in (
            render_rich(digest, locale),
            render_text(digest, locale),
            render_rich(partial, locale),
            render_error(_digest(error="boom"), locale),
        ):
            assert "core.admin.digest" not in rendered

    def test_russian_digest_is_translated(self):
        rich = render_rich(_digest(past_due=3), "ru")

        assert "<td>Выручка</td>" in rich
        assert "Подписок с просроченной оплатой: 3" in rich

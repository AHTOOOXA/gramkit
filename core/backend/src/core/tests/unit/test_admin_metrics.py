"""StatWindows and the Overview-card / digest-row registries (core.services.admin_metrics)."""

from datetime import UTC, datetime, timedelta

import pytest

from core.schemas.statistics import OverviewCard
from core.services import admin_metrics
from core.services.admin_metrics import (
    DigestRow,
    StatWindows,
    digest_row_fns,
    overview_card_fns,
    register_digest_row,
    register_overview_card,
)


@pytest.fixture(autouse=True)
def _empty_registries(monkeypatch):
    monkeypatch.setattr(admin_metrics, "_OVERVIEW_CARDS", {})
    monkeypatch.setattr(admin_metrics, "_DIGEST_ROWS", {})


def _card(key: str):
    async def fn(session, window) -> OverviewCard:
        return OverviewCard(key=key, section="s", label=key, value=1)

    return fn


def _row(label: str):
    async def fn(session, window) -> DigestRow | None:
        return DigestRow(label)

    return fn


@pytest.mark.business_logic
class TestStatWindows:
    def test_before_two_am_the_day_started_yesterday(self):
        windows = StatWindows.anchored(datetime(2026, 9, 26, 1, 59, tzinfo=UTC))

        assert windows.today_start == datetime(2026, 9, 25, 2, 0, tzinfo=UTC)
        assert windows.today_str == "2026-09-25"

    def test_from_two_am_the_day_starts_today(self):
        windows = StatWindows.anchored(datetime(2026, 9, 26, 2, 0, tzinfo=UTC))

        assert windows.today_start == datetime(2026, 9, 26, 2, 0, tzinfo=UTC)
        assert windows.week_ago_start == windows.today_start - timedelta(days=7)
        assert windows.month_ago_start == windows.today_start - timedelta(days=30)

    def test_previous_windows_end_where_the_current_ones_start(self):
        windows = StatWindows.anchored(datetime(2026, 9, 26, 12, 0, tzinfo=UTC))

        assert windows.prev_day_start == windows.today_start - timedelta(days=1)
        assert windows.prev_week_start == windows.week_ago_start - timedelta(days=7)
        assert windows.prev_month_start == windows.month_ago_start - timedelta(days=30)

    def test_partial_until_twenty_three_hours_in(self):
        start = datetime(2026, 9, 25, 2, 0, tzinfo=UTC)

        assert StatWindows.anchored(start + timedelta(hours=10)).partial is True
        assert StatWindows.anchored(start + timedelta(hours=23, minutes=55)).partial is False


@pytest.mark.business_logic
class TestRegistries:
    def test_cards_keep_registration_order_and_a_key_replaces(self):
        first, second, replacement = _card("a"), _card("b"), _card("a2")
        register_overview_card("a", first)
        register_overview_card("b", second)
        register_overview_card("a", replacement)

        assert overview_card_fns() == [replacement, second]

    def test_rows_sorted_by_order_then_registration(self):
        late, early, tie_one, tie_two = _row("late"), _row("early"), _row("t1"), _row("t2")
        register_digest_row("late", late, order=90)
        register_digest_row("tie1", tie_one, order=30)
        register_digest_row("early", early, order=5)
        register_digest_row("tie2", tie_two, order=30)

        assert digest_row_fns() == [(5, early), (30, tie_one), (30, tie_two), (90, late)]

    def test_registering_a_row_again_replaces_it(self):
        old, new = _row("old"), _row("new")
        register_digest_row("x", old, order=30)
        register_digest_row("x", new, order=70)

        assert digest_row_fns() == [(70, new)]

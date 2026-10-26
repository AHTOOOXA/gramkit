"""Unit tests for the marketing-links economics and the code rules (no DB, no app)."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from core.schemas.marketing_links import MarketingLinkCreateRequest, MarketingLinkStats
from core.services.marketing_links import _economics, app_link, bot_link


def _stats(users: int, revenue: float) -> MarketingLinkStats:
    return MarketingLinkStats(users=users, revenue_rub=revenue)


class TestEconomics:
    @pytest.mark.business_logic
    def test_no_price_gives_no_cac_roas_or_verdict(self):
        result = _economics(None, _stats(4, 200.0), datetime.now(UTC), [])
        assert result == {"cac_rub": None, "ltv_rub": 50.0, "roas": None, "payback": None, "payback_days": None}

    @pytest.mark.business_logic
    def test_no_users_gives_no_cac_or_ltv(self):
        result = _economics(1000.0, _stats(0, 0.0), datetime.now(UTC), [])
        assert (result["cac_rub"], result["ltv_rub"], result["roas"]) == (None, None, 0.0)

    @pytest.mark.business_logic
    def test_paid_back_on_the_day_running_revenue_covers_the_price(self):
        start = datetime.now(UTC) - timedelta(days=30)
        payments = [(start + timedelta(days=2), 400.0), (start + timedelta(days=5, hours=3), 700.0)]
        result = _economics(1000.0, _stats(3, 1100.0), start, payments)
        assert result["payback"] == "paid_back"
        assert result["payback_days"] == 6  # day 1 is the start date
        assert result["cac_rub"] == 333.33  # rounded to kopecks
        assert result["roas"] == 1.1

    @pytest.mark.business_logic
    def test_a_payment_before_the_start_counts_as_day_one(self):
        start = datetime.now(UTC)
        result = _economics(100.0, _stats(1, 100.0), start, [(start - timedelta(days=2), 100.0)])
        assert (result["payback"], result["payback_days"]) == ("paid_back", 1)

    @pytest.mark.business_logic
    def test_in_progress_within_14_days_then_not_paid_back(self):
        fresh = _economics(1000.0, _stats(1, 10.0), datetime.now(UTC) - timedelta(days=13), [])
        late = _economics(1000.0, _stats(1, 10.0), datetime.now(UTC) - timedelta(days=14, minutes=1), [])
        assert fresh["payback"] == "in_progress"
        assert late["payback"] == "not_paid_back"

    @pytest.mark.business_logic
    def test_unknown_start_stays_in_progress(self):
        assert _economics(1000.0, _stats(0, 0.0), None, [])["payback"] == "in_progress"


class TestLinks:
    @pytest.mark.business_logic
    def test_link_shapes(self):
        assert app_link("https://t.me/bot/app", "post_1") == "https://t.me/bot/app?startapp=r-post_1"
        assert bot_link("https://t.me/bot", "post_1") == "https://t.me/bot?start=post_1"


class TestCodeRules:
    @pytest.mark.business_logic
    def test_code_is_stripped_and_lowercased(self):
        assert MarketingLinkCreateRequest(code=" Ab_1 ").code == "ab_1"

    @pytest.mark.business_logic
    @pytest.mark.parametrize("bad", ["a-b", "a", "x" * 41, "with space", "кот_1", ""])
    def test_bad_codes_are_rejected(self, bad: str):
        with pytest.raises(ValidationError):
            MarketingLinkCreateRequest(code=bad)

    @pytest.mark.business_logic
    def test_channel_and_price_limits(self):
        with pytest.raises(ValidationError):
            MarketingLinkCreateRequest(code="ok_1", channel="x" * 121)
        with pytest.raises(ValidationError):
            MarketingLinkCreateRequest(code="ok_1", price_rub=-0.01)

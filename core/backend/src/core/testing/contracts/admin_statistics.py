"""Base test class for the core admin Overview + money analytics contract tests.

Covers every endpoint of ``core.infrastructure.fastapi.routers.admin_statistics`` (served under
``/admin`` through ``routers.admin``):

  GET /admin/statistics/overview                 (A)
  GET /admin/analytics/revenue-timeseries        (A)  (422: days > 365, unknown granularity)
  GET /admin/analytics/revenue-kpis              (A)
  GET /admin/analytics/subscription-trend        (A)  (422: weeks > 26)
  GET /admin/analytics/subscription-breakdown    (A)
  GET /admin/analytics/mrr                       (A)

The app's registered Overview cards are asserted by shape only (each app tests its own).

Rule: every endpoint has an ``authenticated_client`` -> 403 test.

Apps inherit this class and provide the fixtures:
- ``authenticated_client``: regular (non-admin) Telegram-authenticated client
- ``admin_client``: from ``core.testing.fixtures`` (needs ``test_app``)
- ``db_session``: the session the app's ``test_app`` is wired to (rolled back after each test)

The database is shared by parallel tests, so totals are asserted as lower bounds and series
by membership, never as exact values.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models.enums import PaymentProvider, PaymentStatus
from core.infrastructure.database.repo.requests import CoreRequestsRepo

ANALYTICS_PATHS = [
    "/admin/analytics/revenue-timeseries",
    "/admin/analytics/revenue-kpis",
    "/admin/analytics/subscription-trend",
    "/admin/analytics/subscription-breakdown",
    "/admin/analytics/mrr",
]


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_optional_number(value: object) -> bool:
    return value is None or _is_number(value)


async def _seed_payment(
    db_session: AsyncSession,
    *,
    amount: float,
    currency: str,
    provider: PaymentProvider,
    status: PaymentStatus = PaymentStatus.SUCCEEDED,
) -> None:
    repo = CoreRequestsRepo(db_session)
    user = await repo.users.create({"username": f"stats_{uuid4().hex[:8]}"})
    await repo.payments.create(
        {
            "user_id": user.id,
            "product_id": "TEST_PRODUCT",
            "provider_id": provider,
            "amount": amount,
            "currency": currency,
            "status": status,
            "is_recurring": False,
            "provider_metadata": {},
        }
    )
    await db_session.flush()


class BaseAdminStatisticsTests:
    """Base class for core admin Overview + analytics contract tests."""

    # =========================================================================
    # Overview
    # =========================================================================

    @pytest.mark.contract
    async def test_overview_shape(self, admin_client: AsyncClient):
        """GET /admin/statistics/overview: core blocks + the app's cards, not degraded."""
        response = await admin_client.get("/admin/statistics/overview")
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["error"] is None
        assert isinstance(data["date"], str)
        for key in (
            "total",
            "new_today",
            "new_this_week",
            "new_this_month",
            "new_prev_day",
            "new_prev_week",
            "new_prev_month",
            "dau",
            "wau",
            "mau",
        ):
            assert isinstance(data["users"][key], int), key
        # Revenue is per-currency dicts (never a scalar sum).
        for key in ("alltime", "today", "this_week", "this_month"):
            assert isinstance(data["revenue"][key], dict), key
        assert isinstance(data["product_sales"]["alltime"], dict)
        assert isinstance(data["product_sales"]["today"], dict)
        assert isinstance(data["subscriptions"]["active_subscribers"], int)

        assert isinstance(data["cards"], list)
        for card in data["cards"]:
            assert isinstance(card["key"], str)
            assert isinstance(card["section"], str)
            assert isinstance(card["label"], str)
            assert card["format"] in ("number", "percent", "currency")
            assert _is_optional_number(card["value"])
            assert _is_optional_number(card["previous"])
            assert isinstance(card["sparkline"], list)

    @pytest.mark.contract
    async def test_overview_counts_seeded_revenue(self, admin_client: AsyncClient, db_session: AsyncSession):
        """A SUCCEEDED RUB payment shows up in the all-time RUB revenue."""
        await _seed_payment(db_session, amount=777.0, currency="RUB", provider=PaymentProvider.YOOKASSA)

        response = await admin_client.get("/admin/statistics/overview")
        assert response.status_code == 200
        assert response.json()["revenue"]["alltime"]["RUB"] >= 777.0

    @pytest.mark.contract
    async def test_overview_non_admin_forbidden(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/admin/statistics/overview")
        assert response.status_code == 403

    # =========================================================================
    # Analytics: gating
    # =========================================================================

    @pytest.mark.contract
    @pytest.mark.parametrize("path", ANALYTICS_PATHS)
    async def test_analytics_admin_gets_200(self, admin_client: AsyncClient, path: str):
        response = await admin_client.get(path)
        assert response.status_code == 200, response.text

    @pytest.mark.contract
    @pytest.mark.parametrize("path", ANALYTICS_PATHS)
    async def test_analytics_non_admin_forbidden(self, authenticated_client: AsyncClient, path: str):
        response = await authenticated_client.get(path)
        assert response.status_code == 403

    # =========================================================================
    # Analytics: shapes
    # =========================================================================

    @pytest.mark.contract
    async def test_revenue_timeseries_shape(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/analytics/revenue-timeseries?granularity=week&days=30")
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "week"
        assert data["days"] == 30
        assert isinstance(data["buckets"], list)
        assert isinstance(data["series"], list)
        for series in data["series"]:
            assert isinstance(series["currency"], str)
            assert isinstance(series["provider"], str)
            assert isinstance(series["is_cash"], bool)
            assert isinstance(series["points"], list)
            # Every series shares the bucket axis.
            assert [p["bucket"] for p in series["points"]] == data["buckets"]

    @pytest.mark.contract
    async def test_subscription_trend_shape(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/analytics/subscription-trend?weeks=8")
        assert response.status_code == 200
        data = response.json()
        assert data["weeks"] == 8
        assert len(data["points"]) == 8
        for point in data["points"]:
            assert isinstance(point["bucket"], str)
            assert isinstance(point["new"], int)
            assert isinstance(point["ended"], int)
            assert isinstance(point["active"], int)

    @pytest.mark.contract
    async def test_revenue_kpis_shape(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/analytics/revenue-kpis")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["kpis"], list)
        assert isinstance(data["growth"], list)
        for row in data["kpis"]:
            assert isinstance(row["currency"], str)
            assert isinstance(row["paying_users"], int)
            assert _is_number(row["revenue"])
            assert isinstance(row["payment_count"], int)
            # arppu / avg_payment are float | None (divide-by-zero guard).
            assert _is_optional_number(row["arppu"])
            assert _is_optional_number(row["avg_payment"])
        for row in data["growth"]:
            assert isinstance(row["currency"], str)
            assert _is_optional_number(row["month_growth_pct"])
            assert _is_optional_number(row["week_growth_pct"])

    @pytest.mark.contract
    async def test_subscription_breakdown_shape(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/analytics/subscription-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["by_status"], dict)
        assert isinstance(data["gifted"], int)
        assert isinstance(data["churn_by_reason"], dict)
        assert isinstance(data["active_paid"], int)
        assert isinstance(data["active_gifted"], int)
        assert data["churn_period_days"] == 30
        assert isinstance(data["churned_in_period"], int)
        assert isinstance(data["active_at_period_start"], int)
        assert _is_optional_number(data["churn_rate"])
        assert isinstance(data["new_in_period"], int)
        assert data["net_new"] == data["new_in_period"] - data["churned_in_period"]

    @pytest.mark.contract
    async def test_mrr_shape(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/analytics/mrr")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["rows"], list)
        assert isinstance(data["excluded"], int)
        for row in data["rows"]:
            assert isinstance(row["currency"], str)
            assert _is_number(row["mrr"])
            assert _is_number(row["mrr_prev"])
            assert _is_optional_number(row["growth_pct"])
            assert isinstance(row["subscriptions"], int)

    # =========================================================================
    # Analytics: bounds (FastAPI Query validation)
    # =========================================================================

    @pytest.mark.contract
    async def test_days_over_max_rejected(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/analytics/revenue-timeseries?days=366")
        assert response.status_code == 422

    @pytest.mark.contract
    async def test_unknown_granularity_rejected(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/analytics/revenue-timeseries?granularity=month")
        assert response.status_code == 422

    @pytest.mark.contract
    async def test_weeks_over_max_rejected(self, admin_client: AsyncClient):
        response = await admin_client.get("/admin/analytics/subscription-trend?weeks=27")
        assert response.status_code == 422

    # =========================================================================
    # Money is per currency
    # =========================================================================

    @pytest.mark.contract
    async def test_stars_and_cash_are_separate_series(self, admin_client: AsyncClient, db_session: AsyncSession):
        """An XTR (Telegram Stars) payment and a RUB (YooKassa) one land in distinct series;
        Stars are non-cash and stay out of the cash KPIs."""
        await _seed_payment(db_session, amount=42.0, currency="XTR", provider=PaymentProvider.TELEGRAM_STARS)
        await _seed_payment(db_session, amount=500.0, currency="RUB", provider=PaymentProvider.YOOKASSA)

        response = await admin_client.get("/admin/analytics/revenue-timeseries?days=7")
        assert response.status_code == 200
        series = response.json()["series"]
        xtr = [s for s in series if s["currency"] == "XTR"]
        rub = [s for s in series if s["currency"] == "RUB" and s["provider"] == PaymentProvider.YOOKASSA]
        assert xtr and all(s["is_cash"] is False for s in xtr)
        assert rub and all(s["is_cash"] is True for s in rub)
        assert sum(p["amount"] for s in xtr for p in s["points"]) >= 42.0
        assert sum(p["amount"] for s in rub for p in s["points"]) >= 500.0

        kpis = (await admin_client.get("/admin/analytics/revenue-kpis")).json()["kpis"]
        assert all(row["currency"] != "XTR" for row in kpis)

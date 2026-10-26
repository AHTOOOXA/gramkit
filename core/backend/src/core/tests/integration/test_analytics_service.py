"""AnalyticsService (admin money analytics) on the core aggregator (no app installed).

Builds ``CoreRequestsService(CoreRequestsRepo(db_session), redis=InMemoryRedis(), products=...)``
directly: the cache and the product catalog are constructor values. The database may hold other
tests' rows, so totals are lower bounds unless the test uses its own currency.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models.enums import PaymentProvider, PaymentStatus, SubscriptionStatus
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.services.requests import CoreRequestsService
from core.testing.fixtures.redis import InMemoryRedis


@dataclass
class _Price:
    amount: float
    currency: str


@dataclass
class _Product:
    product_id: str
    duration_days: int
    recurring: bool = True
    prices: dict[str, _Price] = field(default_factory=dict)


class _Catalog:
    def __init__(self, *products: _Product):
        self._products = {p.product_id: p for p in products}

    def get_product(self, product_id: str):
        return self._products.get(product_id)


CATALOG = _Catalog(
    _Product("AN_MONTH", 30, prices={"RUB": _Price(555.0, "RUB"), "ZZE": _Price(10.0, "ZZE")}),
    _Product("AN_WEEK", 7, prices={"RUB": _Price(222.0, "RUB")}),
)


@pytest.fixture
def redis() -> InMemoryRedis:
    return InMemoryRedis()


@pytest.fixture
def core_services(db_session: AsyncSession, redis: InMemoryRedis) -> CoreRequestsService:
    return CoreRequestsService(CoreRequestsRepo(db_session), redis=redis, products=CATALOG)  # type: ignore[arg-type]


async def _user(services: CoreRequestsService):
    return await services.repo.users.create({"username": f"an_{uuid4().hex[:8]}"})


async def _pay(
    services: CoreRequestsService,
    user_id,
    *,
    amount: float,
    currency: str,
    provider: PaymentProvider,
    status: PaymentStatus = PaymentStatus.SUCCEEDED,
) -> None:
    await services.repo.payments.create(
        {
            "user_id": user_id,
            "product_id": "AN_MONTH",
            "provider_id": provider,
            "amount": amount,
            "currency": currency,
            "status": status,
            "is_recurring": False,
            "provider_metadata": {},
        }
    )
    await services.repo.session.flush()


async def _subscribe(
    services: CoreRequestsService,
    *,
    product_id: str,
    provider: PaymentProvider = PaymentProvider.YOOKASSA,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    currency: str = "RUB",
    days_left: int = 20,
) -> None:
    user = await _user(services)
    now = datetime.now(UTC)
    await services.repo.subscriptions.create(
        {
            "user_id": user.id,
            "product_id": product_id,
            "provider_id": provider,
            "status": status,
            "currency": currency,
            "start_date": now - timedelta(days=2),
            "end_date": now + timedelta(days=days_left),
            "recurring_details": {},
        }
    )
    await services.repo.session.flush()


class TestRevenueTimeseries:
    @pytest.mark.business_logic
    async def test_stars_and_cash_are_separate_series_never_summed(self, core_services: CoreRequestsService):
        user = await _user(core_services)
        await _pay(core_services, user.id, amount=500.0, currency="RUB", provider=PaymentProvider.YOOKASSA)
        await _pay(core_services, user.id, amount=42.0, currency="XTR", provider=PaymentProvider.TELEGRAM_STARS)

        result = await core_services.analytics.revenue_timeseries(granularity="day", days=30)

        rub = [s for s in result.series if s.currency == "RUB"]
        xtr = [s for s in result.series if s.currency == "XTR"]
        assert rub and all(s.is_cash for s in rub)
        assert xtr and all(not s.is_cash for s in xtr)
        assert sum(p.amount for s in rub for p in s.points) >= 500.0
        assert sum(p.amount for s in xtr for p in s.points) >= 42.0

    @pytest.mark.business_logic
    async def test_failed_payments_excluded(self, core_services: CoreRequestsService):
        user = await _user(core_services)
        await _pay(
            core_services,
            user.id,
            amount=7.0,
            currency="ZZA",
            provider=PaymentProvider.YOOKASSA,
            status=PaymentStatus.FAILED,
        )

        result = await core_services.analytics.revenue_timeseries(granularity="day", days=30)

        assert all(s.currency != "ZZA" for s in result.series)

    @pytest.mark.business_logic
    async def test_days_clamped_to_max(self, core_services: CoreRequestsService):
        result = await core_services.analytics.revenue_timeseries(granularity="day", days=100_000)
        assert result.days == 365

    @pytest.mark.business_logic
    async def test_second_call_is_served_from_the_cache(self, core_services: CoreRequestsService, redis: InMemoryRedis):
        first = await core_services.analytics.revenue_timeseries(granularity="day", days=7)
        assert await redis.exists("admin:analytics:revenue:day:7") == 1

        user = await _user(core_services)
        await _pay(core_services, user.id, amount=12345.0, currency="RUB", provider=PaymentProvider.YOOKASSA)

        second = await core_services.analytics.revenue_timeseries(granularity="day", days=7)
        assert second.model_dump() == first.model_dump()


class TestSubscriptionTrend:
    @pytest.mark.business_logic
    async def test_weeks_clamped_and_cached(self, core_services: CoreRequestsService, redis: InMemoryRedis):
        result = await core_services.analytics.subscription_trend(weeks=100_000)
        assert result.weeks == 26
        assert len(result.points) == 26

        await core_services.analytics.subscription_trend(weeks=4)
        assert await redis.exists("admin:analytics:subtrend:4") == 1


class TestSubscriptionBreakdown:
    @pytest.mark.business_logic
    async def test_gifted_and_paid_active_split(self, core_services: CoreRequestsService):
        await _subscribe(core_services, product_id="AN_GIFT", provider=PaymentProvider.GIFT)
        await _subscribe(core_services, product_id="AN_MONTH")

        breakdown = await core_services.analytics.subscription_breakdown()

        assert breakdown.gifted >= 1
        assert breakdown.active_gifted >= 1
        assert breakdown.active_paid >= 1
        assert breakdown.by_status.get(SubscriptionStatus.ACTIVE.value, 0) >= 2

    @pytest.mark.business_logic
    async def test_churn_rate_is_a_float_or_none_and_net_new_is_signed(self, core_services: CoreRequestsService):
        breakdown = await core_services.analytics.subscription_breakdown()

        assert breakdown.churn_period_days == 30
        assert breakdown.churn_rate is None or isinstance(breakdown.churn_rate, float)
        assert breakdown.net_new == breakdown.new_in_period - breakdown.churned_in_period


class TestRevenueKpis:
    @pytest.mark.business_logic
    async def test_arppu_and_avg_payment_per_currency(self, core_services: CoreRequestsService):
        user = await _user(core_services)
        await _pay(core_services, user.id, amount=300.0, currency="ZZB", provider=PaymentProvider.YOOKASSA)
        await _pay(core_services, user.id, amount=100.0, currency="ZZB", provider=PaymentProvider.YOOKASSA)

        result = await core_services.analytics.revenue_kpis()

        [row] = [r for r in result.kpis if r.currency == "ZZB"]
        assert (row.paying_users, row.payment_count, row.revenue) == (1, 2, 400.0)
        assert row.arppu == 400.0
        assert row.avg_payment == 200.0
        [growth] = [g for g in result.growth if g.currency == "ZZB"]
        assert growth.this_week == 400.0
        assert growth.last_week == 0.0
        assert growth.week_growth_pct is None  # growth from zero is undefined

    @pytest.mark.business_logic
    async def test_non_cash_excluded(self, core_services: CoreRequestsService):
        user = await _user(core_services)
        await _pay(core_services, user.id, amount=55.0, currency="XTR", provider=PaymentProvider.TELEGRAM_STARS)
        await _pay(core_services, user.id, amount=10.0, currency="ZZC", provider=PaymentProvider.GIFT)

        result = await core_services.analytics.revenue_kpis()

        assert all(r.currency not in ("XTR", "ZZC") for r in result.kpis)
        assert all(g.currency not in ("XTR", "ZZC") for g in result.growth)


class TestMrr:
    @pytest.mark.business_logic
    async def test_per_currency_from_the_injected_catalog(self, core_services: CoreRequestsService):
        await _subscribe(core_services, product_id="AN_MONTH")
        await _subscribe(core_services, product_id="AN_WEEK", days_left=5)

        result = await core_services.analytics.mrr()

        rub = next(r for r in result.rows if r.currency == "RUB")
        assert rub.mrr >= 555.0 + 222.0 * (30 / 7) - 0.5
        assert rub.subscriptions >= 2

    @pytest.mark.business_logic
    async def test_unknown_product_and_foreign_currency_are_excluded(self, core_services: CoreRequestsService):
        before = (await core_services.analytics.mrr()).excluded
        await _subscribe(core_services, product_id="AN_UNKNOWN")
        await _subscribe(core_services, product_id="AN_MONTH", currency="USD")  # no USD price

        result = await core_services.analytics.mrr()

        assert result.excluded >= before + 2
        assert all(r.currency != "USD" for r in result.rows)

    @pytest.mark.business_logic
    async def test_gifted_subscriptions_are_not_mrr(self, core_services: CoreRequestsService):
        await _subscribe(core_services, product_id="AN_MONTH", provider=PaymentProvider.GIFT, currency="ZZE")

        result = await core_services.analytics.mrr()

        # Priceable in ZZE, but a gift brings no recurring cash: filtered out in SQL, not excluded.
        assert all(r.currency != "ZZE" for r in result.rows)

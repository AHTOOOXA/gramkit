"""Admin money analytics: revenue, subscriptions, MRR (``/admin/analytics/*``).

Wraps ``AnalyticsRepo`` and shapes its raw aggregate rows into the API schemas. These are
DB-native financial numbers (paying users, ARPPU, MRR, churn, period-over-period revenue) —
the complement to an event-analytics tool, not a re-implementation of it. Three cross-cutting
rules live here so they have one home:

1. **Bounds.** Every windowed read clamps its lookback (``days<=365``, ``weeks<=26``)
   before touching the DB — there are no indexes on the hot columns yet (deferred), so
   unbounded scans are the risk we mitigate with bounded params + caching, not indexes.
2. **Money is per-currency, never summed.** Revenue is folded into one series per
   ``(currency, provider_id)``. The non-cash providers (``NON_CASH_PROVIDERS``: TELEGRAM_STARS
   / XTR and GIFT) stay their own series (``is_cash=False``), never merged into headline cash
   revenue.
3. **MRR is derived, never fabricated.** Each ACTIVE PAID subscription is priced from the
   app's injected product catalog (``services.products``: price + ``duration_days``) and
   normalized to a monthly equivalent. Rows whose product/price can't be resolved are
   EXCLUDED and counted — never priced with a guess.

The two heavy reads — revenue-timeseries, subscription-trend — are Redis-cached with a
short TTL via ``self.services.redis`` (``get`` -> bytes / ``set(key, json, ex=ttl)``). Cache
keys embed the clamped params so different windows don't collide. The keys are not
app-prefixed: each app's stack has its own Redis. A redis hiccup degrades to a live read.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from core.domain.products import product_price_in
from core.infrastructure.database.repo.analytics import NON_CASH_PROVIDERS
from core.infrastructure.logging import get_logger
from core.schemas.analytics import (
    MrrCurrencyRow,
    MrrSchema,
    RevenueKpiRow,
    RevenueKpisSchema,
    RevenuePeriodGrowthRow,
    RevenuePoint,
    RevenueSeries,
    RevenueTimeseriesSchema,
    SubscriptionBreakdownSchema,
    SubscriptionTrendPoint,
    SubscriptionTrendSchema,
)
from core.services.base import BaseService

logger = get_logger(__name__)

# Bound clamps (see module docstring). Heavy reads can't outrun these.
_MAX_DAYS = 365
_MAX_WEEKS = 26

# Short cache TTLs (seconds) for the heavy reads.
_TTL_REVENUE = 120
_TTL_SUB_TREND = 300

# Trailing window the churn rate + net-new subscribers are measured over.
_CHURN_PERIOD_DAYS = 30
# Days in the monthly-equivalent normalization for MRR.
_MRR_MONTH_DAYS = 30


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _growth_pct(current: float, previous: float) -> float | None:
    """Period-over-period growth %, or None when the prior window is zero.

    Growth from zero is undefined (not "infinite"), so we surface None rather than
    fabricating a number. A 0.0 prior with a 0.0 current is also None (no movement
    measurable)."""
    if previous == 0:
        return None
    return (current - previous) / previous * 100.0


def _week_start(moment: datetime) -> datetime:
    """Monday 00:00 UTC of the week containing ``moment`` (matches date_trunc('week'))."""
    day = moment.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


class AnalyticsService(BaseService):
    # ── cache helpers ───────────────────────────────────────────────────────

    async def _cache_get(self, key: str) -> dict | None:
        try:
            raw = await self.services.redis.get(key)
        except Exception as e:  # pragma: no cover - redis hiccup degrades to live read
            logger.warning(f"analytics cache get failed for {key}: {e}")
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def _cache_set(self, key: str, payload: dict, ttl: int) -> None:
        try:
            await self.services.redis.set(key, json.dumps(payload), ex=ttl)
        except Exception as e:  # pragma: no cover - cache write best-effort
            logger.warning(f"analytics cache set failed for {key}: {e}")

    # ── revenue timeseries (cached) ─────────────────────────────────────────

    async def revenue_timeseries(self, *, granularity: str, days: int) -> RevenueTimeseriesSchema:
        gran = "week" if granularity == "week" else "day"
        days = _clamp(days, 1, _MAX_DAYS)
        key = f"admin:analytics:revenue:{gran}:{days}"

        cached = await self._cache_get(key)
        if cached is not None:
            return RevenueTimeseriesSchema.model_validate(cached)

        result = await self._build_revenue_timeseries(granularity=gran, days=days)
        await self._cache_set(key, result.model_dump(), _TTL_REVENUE)
        return result

    async def _build_revenue_timeseries(self, *, granularity: str, days: int) -> RevenueTimeseriesSchema:
        now = datetime.now(UTC)
        since = now - timedelta(days=days)
        rows = await self.repo.analytics.revenue_timeseries(since=since, granularity=granularity)

        # Shared, ordered bucket axis (ISO date strings).
        bucket_keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            b = row["bucket"].date().isoformat()
            if b not in seen:
                seen.add(b)
                bucket_keys.append(b)
        bucket_keys.sort()

        # series_map[(currency, provider)] -> {bucket -> (amount, count)}
        series_map: dict[tuple[str, str], dict[str, tuple[float, int]]] = {}
        for row in rows:
            currency = str(row["currency"])
            provider = str(row["provider_id"])
            b = row["bucket"].date().isoformat()
            series_map.setdefault((currency, provider), {})[b] = (float(row["amount"]), int(row["count"]))

        series: list[RevenueSeries] = []
        for (currency, provider), buckets in sorted(series_map.items()):
            points = [
                RevenuePoint(
                    bucket=b,
                    amount=buckets.get(b, (0.0, 0))[0],
                    count=buckets.get(b, (0.0, 0))[1],
                )
                for b in bucket_keys
            ]
            series.append(
                RevenueSeries(
                    currency=currency,
                    provider=provider,
                    is_cash=provider not in {p.value for p in NON_CASH_PROVIDERS},
                    points=points,
                )
            )

        return RevenueTimeseriesSchema(
            granularity=granularity,
            days=days,
            buckets=bucket_keys,
            series=series,
        )

    # ── revenue KPIs: paying users / ARPPU / avg payment + growth (live) ─────

    async def revenue_kpis(self) -> RevenueKpisSchema:
        """Per-currency cash KPIs (paying users, ARPPU, avg payment) + month/week growth.

        ARPPU and avg-payment guard divide-by-zero with None (a 0 would lie). Growth %
        is None when the prior window is zero. Currencies are never summed; non-cash
        XTR/GIFT are excluded entirely (these are cash KPIs)."""
        kpi_rows_raw = await self.repo.analytics.revenue_kpis_by_currency()
        kpis: list[RevenueKpiRow] = []
        for row in kpi_rows_raw:
            paying = int(row["paying_users"])
            revenue = float(row["revenue"])
            count = int(row["payment_count"])
            kpis.append(
                RevenueKpiRow(
                    currency=str(row["currency"]),
                    paying_users=paying,
                    revenue=revenue,
                    payment_count=count,
                    arppu=(revenue / paying) if paying else None,
                    avg_payment=(revenue / count) if count else None,
                )
            )
        kpis.sort(key=lambda r: r.currency)

        growth = await self._revenue_growth()
        return RevenueKpisSchema(kpis=kpis, growth=growth)

    async def _revenue_growth(self) -> list[RevenuePeriodGrowthRow]:
        """Current-vs-previous cash revenue per currency for the calendar month AND a
        rolling 7-day week, with growth %."""
        now = datetime.now(UTC)

        # Calendar-month windows: this month [month_start, now), last month
        # [prev_month_start, month_start).
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_end = month_start
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # Rolling-week windows: last 7 days vs the 7 days before that.
        week_start = now - timedelta(days=7)
        prev_week_start = now - timedelta(days=14)

        this_month = await self.repo.analytics.cash_revenue_in_range_by_currency(since=month_start, until=now)
        last_month = await self.repo.analytics.cash_revenue_in_range_by_currency(
            since=prev_month_start, until=prev_month_end
        )
        this_week = await self.repo.analytics.cash_revenue_in_range_by_currency(since=week_start, until=now)
        last_week = await self.repo.analytics.cash_revenue_in_range_by_currency(since=prev_week_start, until=week_start)

        currencies = sorted(set(this_month) | set(last_month) | set(this_week) | set(last_week))
        rows: list[RevenuePeriodGrowthRow] = []
        for currency in currencies:
            tm = this_month.get(currency, 0.0)
            lm = last_month.get(currency, 0.0)
            tw = this_week.get(currency, 0.0)
            lw = last_week.get(currency, 0.0)
            rows.append(
                RevenuePeriodGrowthRow(
                    currency=currency,
                    this_month=tm,
                    last_month=lm,
                    month_growth_pct=_growth_pct(tm, lm),
                    this_week=tw,
                    last_week=lw,
                    week_growth_pct=_growth_pct(tw, lw),
                )
            )
        return rows

    # ── subscription trend (cached) ─────────────────────────────────────────

    async def subscription_trend(self, *, weeks: int) -> SubscriptionTrendSchema:
        weeks = _clamp(weeks, 1, _MAX_WEEKS)
        key = f"admin:analytics:subtrend:{weeks}"

        cached = await self._cache_get(key)
        if cached is not None:
            return SubscriptionTrendSchema.model_validate(cached)

        result = await self._build_subscription_trend(weeks=weeks)
        await self._cache_set(key, result.model_dump(), _TTL_SUB_TREND)
        return result

    async def _build_subscription_trend(self, *, weeks: int) -> SubscriptionTrendSchema:
        now = datetime.now(UTC)
        this_week = _week_start(now)
        first_week = this_week - timedelta(weeks=weeks - 1)
        # ended window extends one week past the last bucket so end_date < until is inclusive.
        until = this_week + timedelta(weeks=1)

        week_axis = [first_week + timedelta(weeks=i) for i in range(weeks)]

        started = await self.repo.analytics.subscriptions_started_by_week(since=first_week)
        ended = await self.repo.analytics.subscriptions_ended_by_week(since=first_week, until=until)

        # Normalize DB bucket datetimes to UTC dates for keying.
        def _norm(d: dict[datetime, int]) -> dict[str, int]:
            out: dict[str, int] = {}
            for moment, count in d.items():
                out[moment.astimezone(UTC).date().isoformat()] = count
            return out

        started_n = _norm(started)
        ended_n = _norm(ended)

        points: list[SubscriptionTrendPoint] = []
        for week in week_axis:
            iso = week.date().isoformat()
            # "active" snapshot at the END of the bucket week.
            active = await self.repo.analytics.active_subscriptions_as_of(week + timedelta(weeks=1))
            points.append(
                SubscriptionTrendPoint(
                    bucket=iso,
                    new=started_n.get(iso, 0),
                    ended=ended_n.get(iso, 0),
                    active=active,
                )
            )

        return SubscriptionTrendSchema(weeks=weeks, points=points)

    # ── subscription breakdown + churn rate + net-new (live) ────────────────

    async def subscription_breakdown(self) -> SubscriptionBreakdownSchema:
        by_status = await self.repo.analytics.subscription_status_counts()
        gifted = await self.repo.analytics.gifted_subscriptions_count()
        churn = await self.repo.analytics.churn_by_reason()

        now = datetime.now(UTC)
        period_start = now - timedelta(days=_CHURN_PERIOD_DAYS)

        # ACTIVE gift-vs-paid split right now.
        active_paid, active_gifted = await self.repo.analytics.active_split_paid_vs_gift(now)

        # Churn rate over the trailing window: churned-in-period / active-at-start.
        active_at_start = await self.repo.analytics.active_subscriptions_as_of(period_start)
        churned = await self.repo.analytics.subscriptions_ended_in_range(since=period_start, until=now)
        new_in_period = await self.repo.analytics.subscriptions_started_in_range(since=period_start, until=now)
        # Divide-by-zero guard: a 0% rate when nobody was active would mislead -> None.
        churn_rate = (churned / active_at_start * 100.0) if active_at_start else None

        return SubscriptionBreakdownSchema(
            by_status=by_status,
            gifted=gifted,
            churn_by_reason=churn,
            active_paid=active_paid,
            active_gifted=active_gifted,
            churn_period_days=_CHURN_PERIOD_DAYS,
            churned_in_period=churned,
            active_at_period_start=active_at_start,
            churn_rate=churn_rate,
            new_in_period=new_in_period,
            net_new=new_in_period - churned,
        )

    # ── MRR + month-over-month growth (live, per currency) ───────────────────

    async def mrr(self) -> MrrSchema:
        """Per-currency monthly recurring revenue + MoM growth, from ACTIVE PAID subs.

        Each subscription is priced from the app's product catalog (``services.products``) and
        normalized to a monthly-equivalent (``price * 30 / duration_days``). Rows whose product/price
        can't be resolved are EXCLUDED and counted — never fabricated."""
        now = datetime.now(UTC)
        prev = now - timedelta(days=_MRR_MONTH_DAYS)

        current_rows = await self.repo.analytics.active_paid_subscriptions_as_of(now)
        prev_rows = await self.repo.analytics.active_paid_subscriptions_as_of(prev)

        current_mrr, current_subs, excluded = self._fold_mrr(current_rows)
        prev_mrr, _, _ = self._fold_mrr(prev_rows)

        currencies = sorted(set(current_mrr) | set(prev_mrr))
        rows: list[MrrCurrencyRow] = []
        for currency in currencies:
            cur = current_mrr.get(currency, 0.0)
            pre = prev_mrr.get(currency, 0.0)
            rows.append(
                MrrCurrencyRow(
                    currency=currency,
                    mrr=round(cur, 2),
                    mrr_prev=round(pre, 2),
                    growth_pct=_growth_pct(cur, pre),
                    subscriptions=current_subs.get(currency, 0),
                )
            )
        return MrrSchema(rows=rows, excluded=excluded)

    def _fold_mrr(self, rows: list[dict]) -> tuple[dict[str, float], dict[str, int], int]:
        """Fold raw (product_id, currency, count) rows into per-currency monthly MRR.

        Returns (mrr_by_currency, subs_by_currency, excluded_count). A row is excluded
        (and never priced) when its product is unknown (or there is no catalog), non-recurring,
        has no ``duration_days``, or has no price in the row's currency."""
        catalog = self.services.products
        mrr_by_currency: dict[str, float] = {}
        subs_by_currency: dict[str, int] = {}
        excluded = 0
        for row in rows:
            product_id = row["product_id"]
            currency = row["currency"]
            count = int(row["count"])

            product = catalog.get_product(product_id) if catalog is not None else None
            if product is None or not product.recurring or not product.duration_days:
                excluded += count
                continue
            price = product_price_in(product, currency)
            if price is None:
                # No price in the subscription's OWN currency -> can't price honestly.
                excluded += count
                continue

            monthly_equiv = price.amount * (_MRR_MONTH_DAYS / product.duration_days)
            mrr_by_currency[currency] = mrr_by_currency.get(currency, 0.0) + monthly_equiv * count
            subs_by_currency[currency] = subs_by_currency.get(currency, 0) + count
        return mrr_by_currency, subs_by_currency, excluded

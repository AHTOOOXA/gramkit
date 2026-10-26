"""Schemas for the admin money analytics (``/admin/analytics/*``).

Money is PER-CURRENCY and NEVER summed across currencies (``amount`` is a Float +
multi-currency with no base currency). Revenue surfaces therefore carry a *list* of
per-currency series; the non-cash providers (TELEGRAM_STARS / XTR and GIFT) surface as
their OWN series (separated by ``provider_id``), never folded into the headline cash totals.

These are DB-native financial numbers (paying users, ARPPU, MRR, churn, period-over-period
growth) — the complement to an event-analytics tool, not a re-implementation of it.

The heavy reads (revenue-timeseries, subscription-trend) are Redis-cached in the service
with a short TTL and bounded params (``days<=365``, ``weeks<=26``) — there are no DB
indexes on the hot columns yet (deferred).
"""

from __future__ import annotations

from pydantic import BaseModel

# ── Revenue timeseries ──────────────────────────────────────────────────────


class RevenuePoint(BaseModel):
    """One bucket of revenue for a single (currency, provider) series."""

    bucket: str  # ISO date of the bucket start (day or ISO-week Monday)
    amount: float
    count: int


class RevenueSeries(BaseModel):
    """A revenue series for one currency + provider.

    ``is_cash`` is False for the non-cash providers (TELEGRAM_STARS / GIFT) so the
    frontend can render them as clearly-separate, non-headline series.
    """

    currency: str
    provider: str
    is_cash: bool
    points: list[RevenuePoint]


class RevenueTimeseriesSchema(BaseModel):
    granularity: str  # "day" | "week"
    days: int  # the (clamped) lookback window actually used
    buckets: list[str]  # shared bucket axis (ISO dates), oldest -> newest
    series: list[RevenueSeries]  # one per (currency, provider) — NEVER summed


# ── Revenue KPIs (paying users / ARPPU / avg payment, per currency) ──────────


class RevenueKpiRow(BaseModel):
    """Cash KPIs for ONE currency. Built only from SUCCEEDED *cash* payments
    (non-cash XTR/GIFT excluded); never summed across currencies."""

    currency: str
    paying_users: int  # distinct users with >=1 SUCCEEDED cash payment in this currency
    revenue: float  # total SUCCEEDED cash revenue in this currency
    payment_count: int  # number of SUCCEEDED cash payments in this currency
    # revenue / paying_users — None when paying_users == 0 (divide-by-zero guard).
    arppu: float | None = None
    # revenue / payment_count — None when payment_count == 0 (divide-by-zero guard).
    avg_payment: float | None = None


class RevenuePeriodGrowthRow(BaseModel):
    """Current-vs-previous cash revenue for one currency + the growth %.

    Two windows are surfaced: calendar month (this month vs last) and rolling 7-day
    week (this week vs prior week). ``*_growth_pct`` is None when the prior window is
    zero (growth from zero is undefined, not "infinite") — never fabricate a number.
    """

    currency: str
    this_month: float
    last_month: float
    month_growth_pct: float | None = None
    this_week: float
    last_week: float
    week_growth_pct: float | None = None


class RevenueKpisSchema(BaseModel):
    # Per-currency cash KPIs (paying users / ARPPU / avg payment).
    kpis: list[RevenueKpiRow]
    # Per-currency period-over-period cash revenue growth (month + week).
    growth: list[RevenuePeriodGrowthRow]


# ── Subscription trend ──────────────────────────────────────────────────────


class SubscriptionTrendPoint(BaseModel):
    bucket: str  # ISO-week Monday
    new: int  # subscriptions started in the bucket
    ended: int  # subscriptions whose end_date fell in the bucket
    active: int  # entitled subscriptions live at the bucket end


class SubscriptionTrendSchema(BaseModel):
    weeks: int  # the (clamped) number of weeks actually used
    points: list[SubscriptionTrendPoint]


# ── Subscription status breakdown + churn ───────────────────────────────────


class SubscriptionBreakdownSchema(BaseModel):
    # status -> count over ALL subscription rows.
    by_status: dict[str, int]
    # gift subs are GIFT-provider rows; counted separately (non-cash).
    gifted: int
    # cancellation_reason -> count over CANCELED/EXPIRED rows (churn reasons).
    churn_by_reason: dict[str, int]

    # ── ACTIVE gift-vs-paid split (entitled subscriptions right now) ─────────
    active_paid: int  # active & entitled, NON-gift (real paying subscribers)
    active_gifted: int  # active & entitled, GIFT provider (non-cash, comped)

    # ── Churn rate + net-new over the trailing 30 days ───────────────────────
    churn_period_days: int  # window the churn rate / net-new are measured over (30)
    churned_in_period: int  # subscriptions that ended (CANCELED/EXPIRED) in the window
    active_at_period_start: int  # entitled subscriptions live at the window start
    # churned_in_period / active_at_period_start — None when nobody was active at
    # the window start (divide-by-zero guard); a rate of 0% would mislead.
    churn_rate: float | None = None
    new_in_period: int  # subscriptions started in the window
    net_new: int  # new_in_period - churned_in_period (can be negative)


# ── Monthly Recurring Revenue (MRR) ─────────────────────────────────────────


class MrrCurrencyRow(BaseModel):
    """Monthly-equivalent recurring revenue for ONE currency, now vs 30 days ago.

    Built from ACTIVE PAID (non-gift) subscriptions only. Each subscription's product
    is resolved from the app's injected product catalog (``services.products.get_product``) and its
    per-currency price normalized to a monthly-equivalent amount
    (``price * 30 / duration_days``), then summed per currency. Currencies are NEVER
    summed together. ``growth_pct`` is None when MRR 30 days ago was zero.
    """

    currency: str
    mrr: float  # current monthly-equivalent recurring revenue
    mrr_prev: float  # the same figure computed as-of 30 days ago (for MoM growth)
    growth_pct: float | None = None
    subscriptions: int  # active paid subs counted into the current MRR for this currency


class MrrSchema(BaseModel):
    """Per-currency MRR + month-over-month growth.

    MRR is derived from product pricing (``duration_days`` + per-currency price), NOT
    from a stored amount on the subscription. Subscriptions whose product/price cannot
    be resolved are EXCLUDED and counted in ``excluded`` (never priced with a guess).
    """

    rows: list[MrrCurrencyRow]
    # Active paid subscriptions dropped because their product/price was unresolvable
    # (unknown product_id, no price for the row's currency, or non-recurring product).
    excluded: int

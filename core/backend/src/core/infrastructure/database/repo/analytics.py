"""Read-only aggregations for the admin money analytics (``/admin/analytics/*``).

Every method is a pure SELECT (no flush/commit). Buckets are computed in Postgres via
``date_trunc`` so the grouping happens in the DB. Money is grouped by
``(currency, provider_id)`` and NEVER summed across currencies. Cash is every provider
except the non-cash ones (``NON_CASH_PROVIDERS``: TELEGRAM_STARS / XTR and GIFT), so a
new real-money provider counts as cash by default. Heavy reads are bounded by the caller
(the service clamps ``days``/``weeks``) and Redis-cached; no DB indexes on the hot
columns yet.

App-specific engagement numbers (funnels over app tables, feature usage) stay in the app.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from core.infrastructure.database.models.enums import (
    PaymentProvider,
    PaymentStatus,
    SubscriptionStatus,
)
from core.infrastructure.database.models.payments import Payment
from core.infrastructure.database.models.subscriptions import Subscription
from core.infrastructure.database.repo.base import BaseRepo
from core.infrastructure.database.repo.subscriptions import SubscriptionRepo

# Providers whose payments are not real money: Telegram Stars (XTR) and admin gifts.
# Everything else is cash.
NON_CASH_PROVIDERS = (PaymentProvider.TELEGRAM_STARS, PaymentProvider.GIFT)


class AnalyticsRepo(BaseRepo[Payment]):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = Payment

    # ── Revenue timeseries (per currency + provider) ────────────────────────

    async def revenue_timeseries(
        self,
        *,
        since: datetime,
        granularity: str,
    ) -> list[dict]:
        """Bucketed revenue grouped by (bucket, currency, provider_id).

        ``granularity`` is "day" or "week" (validated/clamped by the service).
        Only SUCCEEDED payments count. Returns raw rows; the service folds them
        into per-(currency, provider) series so currencies are never summed.
        """
        trunc_unit = "week" if granularity == "week" else "day"
        bucket = func.date_trunc(trunc_unit, Payment.created_at).label("bucket")

        stmt = (
            select(
                bucket,
                Payment.currency,
                Payment.provider_id,
                func.coalesce(func.sum(Payment.amount), 0.0).label("amount"),
                func.count().label("count"),
            )
            .where(Payment.status == PaymentStatus.SUCCEEDED)
            .where(Payment.created_at >= since)
            .group_by(bucket, Payment.currency, Payment.provider_id)
            .order_by(bucket)
        )
        result = await self.session.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    # ── Revenue KPIs: paying users / ARPPU inputs (per currency) ─────────────

    async def revenue_kpis_by_currency(self) -> list[dict]:
        """Per-currency CASH KPIs over all-time SUCCEEDED payments.

        Returns one row per currency with: distinct paying users, total revenue, and
        payment count. Only SUCCEEDED *cash* payments count (``NON_CASH_PROVIDERS`` are
        excluded via ``provider_id``). Currencies are never summed — the service turns
        each row into ARPPU / avg-payment per currency.
        """
        stmt = (
            select(
                Payment.currency,
                func.count(func.distinct(Payment.user_id)).label("paying_users"),
                func.coalesce(func.sum(Payment.amount), 0.0).label("revenue"),
                func.count().label("payment_count"),
            )
            .where(Payment.status == PaymentStatus.SUCCEEDED)
            .where(Payment.provider_id.notin_(NON_CASH_PROVIDERS))
            .group_by(Payment.currency)
        )
        result = await self.session.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def cash_revenue_in_range_by_currency(self, *, since: datetime, until: datetime) -> dict[str, float]:
        """Total SUCCEEDED CASH revenue per currency in ``[since, until)``.

        Non-cash XTR/GIFT excluded. Used for period-over-period (month / week) growth.
        """
        stmt = (
            select(Payment.currency, func.coalesce(func.sum(Payment.amount), 0.0))
            .where(Payment.status == PaymentStatus.SUCCEEDED)
            .where(Payment.provider_id.notin_(NON_CASH_PROVIDERS))
            .where(Payment.created_at >= since)
            .where(Payment.created_at < until)
            .group_by(Payment.currency)
        )
        result = await self.session.execute(stmt)
        return {str(currency): float(amount) for currency, amount in result.all()}

    # ── Subscription trend (new / ended / active per week) ──────────────────

    async def subscriptions_started_by_week(self, *, since: datetime) -> dict[datetime, int]:
        bucket = func.date_trunc("week", Subscription.start_date).label("bucket")
        stmt = select(bucket, func.count()).where(Subscription.start_date >= since).group_by(bucket)
        result = await self.session.execute(stmt)
        return {row[0]: int(row[1]) for row in result.all()}

    async def subscriptions_ended_by_week(self, *, since: datetime, until: datetime) -> dict[datetime, int]:
        """Subscriptions whose end_date fell in [since, until) AND that are no longer
        entitled (CANCELED/EXPIRED) — i.e. actually churned in that bucket."""
        bucket = func.date_trunc("week", Subscription.end_date).label("bucket")
        stmt = (
            select(bucket, func.count())
            .where(Subscription.end_date >= since)
            .where(Subscription.end_date < until)
            .where(Subscription.status.in_([SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED]))
            .group_by(bucket)
        )
        result = await self.session.execute(stmt)
        return {row[0]: int(row[1]) for row in result.all()}

    async def active_subscriptions_as_of(self, moment: datetime) -> int:
        """Entitled subscriptions live at ``moment`` (started before, ending after)."""
        stmt = select(func.count(func.distinct(Subscription.user_id))).where(
            Subscription.start_date <= moment,
            Subscription.end_date > moment,
            Subscription.status.in_(SubscriptionRepo.ENTITLED_STATUSES),
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def subscriptions_started_in_range(self, *, since: datetime, until: datetime) -> int:
        """Subscriptions whose start_date fell in ``[since, until)`` (new-in-period)."""
        stmt = select(func.count()).where(Subscription.start_date >= since).where(Subscription.start_date < until)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def subscriptions_ended_in_range(self, *, since: datetime, until: datetime) -> int:
        """Subscriptions that churned (CANCELED/EXPIRED) with end_date in ``[since, until)``."""
        stmt = (
            select(func.count())
            .where(Subscription.end_date >= since)
            .where(Subscription.end_date < until)
            .where(Subscription.status.in_([SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED]))
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def active_split_paid_vs_gift(self, moment: datetime) -> tuple[int, int]:
        """(active_paid, active_gifted) entitled subscriptions live at ``moment``.

        Gifted = GIFT-provider rows (non-cash, comped); paid = everything else.
        """
        is_gift = Subscription.provider_id == PaymentProvider.GIFT
        stmt = (
            select(is_gift.label("is_gift"), func.count())
            .where(Subscription.start_date <= moment)
            .where(Subscription.end_date > moment)
            .where(Subscription.status.in_(SubscriptionRepo.ENTITLED_STATUSES))
            .group_by(is_gift)
        )
        result = await self.session.execute(stmt)
        paid = gifted = 0
        for is_gift_val, count in result.all():
            if is_gift_val:
                gifted = int(count)
            else:
                paid += int(count)
        return paid, gifted

    async def active_paid_subscriptions_as_of(self, moment: datetime) -> list[dict]:
        """ACTIVE PAID (non-gift) entitled subscriptions live at ``moment``.

        Returns one row per (product_id, currency) with a count, so the service can
        resolve each product's price + billing interval and compute MRR per currency.
        Gifted (GIFT-provider) subs are excluded — they contribute no recurring cash.
        """
        stmt = (
            select(Subscription.product_id, Subscription.currency, func.count())
            .where(Subscription.start_date <= moment)
            .where(Subscription.end_date > moment)
            .where(Subscription.status.in_(SubscriptionRepo.ENTITLED_STATUSES))
            .where(Subscription.provider_id != PaymentProvider.GIFT)
            .group_by(Subscription.product_id, Subscription.currency)
        )
        result = await self.session.execute(stmt)
        return [
            {"product_id": str(product_id), "currency": str(currency), "count": int(count)}
            for product_id, currency, count in result.all()
        ]

    # ── Subscription status breakdown + churn ───────────────────────────────

    async def subscription_status_counts(self) -> dict[str, int]:
        stmt = select(Subscription.status, func.count()).group_by(Subscription.status)
        result = await self.session.execute(stmt)
        return {str(status): int(count) for status, count in result.all()}

    async def gifted_subscriptions_count(self) -> int:
        stmt = select(func.count()).where(Subscription.provider_id == PaymentProvider.GIFT)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def churn_by_reason(self) -> dict[str, int]:
        """Cancellation reasons over churned (CANCELED/EXPIRED) rows."""
        reason = func.coalesce(Subscription.cancellation_reason, "unknown")
        stmt = (
            select(reason, func.count())
            .where(Subscription.status.in_([SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED]))
            .group_by(reason)
        )
        result = await self.session.execute(stmt)
        return {str(r): int(c) for r, c in result.all()}

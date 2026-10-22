from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from core.infrastructure.database.models.payments import (
    Payment,
    PaymentEvent,
    PaymentStatus,
)
from core.infrastructure.database.repo.base import BaseRepo


class PaymentRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = Payment

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> Payment | None:
        stmt = select(self.model_type).where(self.model_type.provider_payment_id == provider_payment_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_succeeded_since(self, user_id: UUID, product_ids: list[str], since: datetime) -> int:
        """Succeeded payments of these products by this user created since ``since``."""
        if not product_ids:
            return 0
        stmt = select(func.count()).where(
            self.model_type.user_id == user_id,
            self.model_type.product_id.in_(product_ids),
            self.model_type.status == PaymentStatus.SUCCEEDED,
            self.model_type.created_at >= since,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def get_by_user_id(self, user_id: UUID) -> list[Payment]:
        stmt = select(self.model_type).where(self.model_type.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_by_user_id(self, user_id: UUID) -> list[Payment]:
        stmt = select(self.model_type).where(
            (self.model_type.user_id == user_id)
            & (self.model_type.status.in_([PaymentStatus.PENDING, PaymentStatus.WAITING_FOR_CAPTURE]))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_succeeded_renewal_for_period(self, idempotency_key: str) -> Payment | None:
        """A SUCCEEDED renewal already exists for this billing period -> do not re-charge.

        Only SUCCEEDED blocks the renewal: a prior FAILED attempt must stay retryable so the
        dunning budget can advance. The idempotency key is deterministic per (subscription,
        end_date), so it uniquely identifies the period. order_by + limit keeps this
        duplicate-tolerant (returns the latest) instead of raising on a key collision.
        """
        stmt = (
            select(self.model_type)
            .where(
                (self.model_type.idempotency_key == idempotency_key)
                & (self.model_type.status == PaymentStatus.SUCCEEDED)
            )
            .order_by(self.model_type.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_nonterminal_renewal_for_period(self, idempotency_key: str) -> Payment | None:
        """Latest non-terminal (CREATED/WAITING_FOR_ACTION) renewal payment for this period key.

        Used to recover a renewal stranded mid-flow (process died between the provider call and
        the result write): its row sits non-terminal and — because it keeps the period key — its
        presence in uq_payment_idempotency_key would block any fresh attempt. The deterministic
        key makes the recovery re-charge idempotent on YooKassa's side, so resolving it cannot
        double-charge within the provider's idempotency window.
        """
        stmt = (
            select(self.model_type)
            .where(
                (self.model_type.idempotency_key == idempotency_key)
                & (self.model_type.status.in_([PaymentStatus.CREATED, PaymentStatus.WAITING_FOR_ACTION]))
            )
            .order_by(self.model_type.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # Statistics methods
    async def get_total_revenue_by_currency(self) -> dict[str, float]:
        """Get total revenue grouped by currency for successful payments"""
        stmt = (
            select(self.model_type.currency, func.sum(self.model_type.amount))
            .where(self.model_type.status == PaymentStatus.SUCCEEDED)
            .group_by(self.model_type.currency)
        )

        result = await self.session.execute(stmt)
        return {currency: float(amount) for currency, amount in result.all()}

    async def get_revenue_by_currency_and_date(self, currency: str, from_dt, to_dt=None) -> Decimal:
        """Get total revenue for a specific currency between dates"""
        to_dt = to_dt if to_dt else datetime.now(UTC)

        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            and_(
                Payment.status == PaymentStatus.SUCCEEDED,
                Payment.currency == currency,
                Payment.created_at >= from_dt,
                Payment.created_at <= to_dt,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_revenue_by_all_currencies_and_date(self, from_dt, to_dt=None) -> dict[str, float]:
        """Get total revenue grouped by currency for successful payments between dates"""
        to_dt = to_dt if to_dt else datetime.now(UTC)

        stmt = (
            select(self.model_type.currency, func.sum(self.model_type.amount))
            .where(
                and_(
                    self.model_type.status == PaymentStatus.SUCCEEDED,
                    self.model_type.created_at >= from_dt,
                    self.model_type.created_at <= to_dt,
                )
            )
            .group_by(self.model_type.currency)
        )

        result = await self.session.execute(stmt)
        return {currency: float(amount) for currency, amount in result.all()}

    async def get_product_sales_stats(self) -> dict[str, int]:
        """Get count of successful payments grouped by product_id"""
        stmt = (
            select(self.model_type.product_id, func.count())
            .where(self.model_type.status == PaymentStatus.SUCCEEDED)
            .group_by(self.model_type.product_id)
        )

        result = await self.session.execute(stmt)
        return {product_id: int(count) for product_id, count in result.all()}

    async def get_product_sales_stats_by_date(self, from_dt, to_dt=None) -> dict[str, int]:
        """Get count of successful payments grouped by product_id for a specific date range"""
        to_dt = to_dt if to_dt else datetime.now(UTC)

        stmt = (
            select(self.model_type.product_id, func.count())
            .where(
                and_(
                    self.model_type.status == PaymentStatus.SUCCEEDED,
                    self.model_type.created_at >= from_dt,
                    self.model_type.created_at <= to_dt,
                )
            )
            .group_by(self.model_type.product_id)
        )

        result = await self.session.execute(stmt)
        return {product_id: int(count) for product_id, count in result.all()}

    async def get_succeeded_counts_by_kind(self, from_dt, to_dt=None) -> dict[str, int]:
        """Successful payments between dates, split into first purchases vs recurring renewals."""
        to_dt = to_dt if to_dt else datetime.now(UTC)

        stmt = (
            select(self.model_type.is_recurring, func.count())
            .where(
                and_(
                    self.model_type.status == PaymentStatus.SUCCEEDED,
                    self.model_type.created_at >= from_dt,
                    self.model_type.created_at <= to_dt,
                )
            )
            .group_by(self.model_type.is_recurring)
        )

        result = await self.session.execute(stmt)
        counts = {bool(is_recurring): int(count) for is_recurring, count in result.all()}
        return {"first": counts.get(False, 0), "recurring": counts.get(True, 0)}


class PaymentEventRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = PaymentEvent

    async def get_by_payment_id(self, payment_id: UUID) -> list[PaymentEvent]:
        stmt = select(self.model_type).where(self.model_type.payment_id == payment_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_unprocessed(self) -> list[PaymentEvent]:
        stmt = select(self.model_type).where(not self.model_type.processed)
        result = await self.session.execute(stmt)
        return result.scalars().all()

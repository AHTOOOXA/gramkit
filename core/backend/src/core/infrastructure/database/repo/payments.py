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

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select

from core.infrastructure.database.models.subscriptions import (
    Subscription,
    SubscriptionStatus,
)
from core.infrastructure.database.repo.base import BaseRepo


class SubscriptionRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = Subscription

    async def get_by_user_id(self, user_id: UUID) -> list[Subscription]:
        stmt = select(self.model_type).where(self.model_type.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_by_user_id(self, user_id: UUID) -> Subscription | None:
        stmt = select(self.model_type).where(
            (self.model_type.user_id == user_id)
            & (
                or_(
                    self.model_type.status == SubscriptionStatus.ACTIVE,
                    self.model_type.status == SubscriptionStatus.CANCELED,
                )
            )
            & (self.model_type.end_date > datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_expiring_subscriptions(self, expiration_threshold: datetime) -> list[Subscription]:
        stmt = select(self.model_type).where(
            (self.model_type.status == SubscriptionStatus.ACTIVE) & (self.model_type.end_date <= expiration_threshold)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def expire_outdated_subscriptions(self, now: datetime) -> int:
        """Expire subscriptions past their end date.

        Transaction commits at dependency layer.
        """
        stmt = select(self.model_type).where(
            (self.model_type.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELED]))
            & (self.model_type.end_date <= now)
        )
        result = await self.session.execute(stmt)
        subscriptions = result.scalars().all()
        for subscription in subscriptions:
            subscription.status = SubscriptionStatus.EXPIRED
            subscription.canceled_at = datetime.now(UTC)
        await self.session.flush()
        return len(subscriptions)

    async def get_active_subscribers_count(self) -> int:
        """Get the count of users with active subscriptions (ACTIVE or CANCELED but not expired)"""
        stmt = select(func.count(func.distinct(self.model_type.user_id))).where(
            (
                or_(
                    self.model_type.status == SubscriptionStatus.ACTIVE,
                    self.model_type.status == SubscriptionStatus.CANCELED,
                )
            )
            & (self.model_type.end_date > datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

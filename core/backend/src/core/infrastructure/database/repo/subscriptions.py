from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select

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

    # Statuses that still grant access: ACTIVE, PAST_DUE (in dunning grace), CANCELED (until end).
    ENTITLED_STATUSES = (
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.CANCELED,
    )

    async def get_active_by_user_id(self, user_id: UUID) -> Subscription | None:
        stmt = (
            select(self.model_type)
            .where(
                (self.model_type.user_id == user_id)
                & (self.model_type.status.in_(self.ENTITLED_STATUSES))
                & (self.model_type.end_date > datetime.now(UTC))
            )
            # Duplicate-tolerant: degrade gracefully on pre-existing dup rows instead of raising
            # MultipleResultsFound (the partial unique index is only added in a later commit).
            .order_by(self.model_type.end_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_renewable_by_user_id(self, user_id: UUID) -> Subscription | None:
        """Find the most recent ACTIVE/PAST_DUE subscription regardless of end_date.

        Unlike get_active_by_user_id, this includes subs whose end_date has passed
        but haven't been marked EXPIRED yet. Used for renewal to prevent creating
        duplicate subscriptions after downtime. PAST_DUE is included so a fresh manual
        payment renews the existing dunning row instead of creating a duplicate.
        """
        stmt = (
            select(self.model_type)
            .where(
                (self.model_type.user_id == user_id)
                & (self.model_type.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE]))
            )
            .order_by(self.model_type.end_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recently_canceled_by_user_id(self, user_id: UUID, since: datetime) -> Subscription | None:
        """Most recent user-CANCELED subscription whose period ended on/after ``since``.

        Resurrection backstop for ``top_up_subscription``: a late provider auto-renewal can arrive
        just after a canceled sub's ``end_date`` has passed, at which point ``get_active_by_user_id``
        (filters ``end_date > now``) and ``get_renewable_by_user_id`` (excludes CANCELED) both miss
        it — so the renewal would otherwise create a brand-new ACTIVE sub, resurrecting exactly what
        the user canceled. The ``since`` window scopes this to an *adjacent* renewal (one period +
        slack), so an ancient cancellation can't block an unrelated future charge.
        """
        stmt = (
            select(self.model_type)
            .where(
                (self.model_type.user_id == user_id)
                & (self.model_type.status == SubscriptionStatus.CANCELED)
                & (self.model_type.end_date >= since)
            )
            .order_by(self.model_type.end_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_chargeable_subscriptions(self, expiration_threshold: datetime) -> list[Subscription]:
        """Subscriptions the renewal job should attempt to charge: ACTIVE or PAST_DUE (dunning
        retry) whose end_date is within the threshold window."""
        stmt = select(self.model_type).where(
            (self.model_type.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE]))
            & (self.model_type.end_date <= expiration_threshold)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_expirable_subscriptions(self, now: datetime, past_due_cutoff: datetime) -> list[Subscription]:
        """Subscriptions to expire: ACTIVE past end_date now, OR PAST_DUE whose grace window has
        elapsed (end_date <= now - grace). The grace cutoff is the dunning safety-net that
        guarantees a PAST_DUE row cannot grant free access forever if the renewal job stops
        selecting it (product removed, repeated errors, etc.)."""
        stmt = select(self.model_type).where(
            ((self.model_type.status == SubscriptionStatus.ACTIVE) & (self.model_type.end_date <= now))
            | ((self.model_type.status == SubscriptionStatus.PAST_DUE) & (self.model_type.end_date <= past_due_cutoff))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_subscribers_count(self) -> int:
        """Count users entitled to a subscription (ACTIVE / PAST_DUE / CANCELED, not yet expired)."""
        stmt = select(func.count(func.distinct(self.model_type.user_id))).where(
            (self.model_type.status.in_(self.ENTITLED_STATUSES)) & (self.model_type.end_date > datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_status(self, status: SubscriptionStatus) -> int:
        stmt = select(func.count()).select_from(self.model_type).where(self.model_type.status == status)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_ended_between(self, status: SubscriptionStatus, from_dt, to_dt=None) -> int:
        """Subscriptions now in ``status`` (CANCELED / EXPIRED) whose ``canceled_at`` falls in the window.

        Expiry overwrites ``canceled_at``, so a CANCELED count is only reliable for recent windows
        (a canceled sub that has since expired is counted as EXPIRED instead).
        """
        to_dt = to_dt if to_dt else datetime.now(UTC)
        stmt = (
            select(func.count())
            .select_from(self.model_type)
            .where(
                (self.model_type.status == status)
                & (self.model_type.canceled_at >= from_dt)
                & (self.model_type.canceled_at <= to_dt)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

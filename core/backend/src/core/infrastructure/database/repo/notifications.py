from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from core.infrastructure.database.models import NotificationDelivery
from core.infrastructure.database.repo.base import BaseRepo


class NotificationDeliveryRepo(BaseRepo[NotificationDelivery]):
    """The notification delivery log. Batched reads for the per-template caps (no N+1)."""

    def __init__(self, session):
        super().__init__(session)
        self.model_type = NotificationDelivery

    async def record(
        self,
        *,
        user_id: UUID,
        template: str,
        message_key: str,
        slot: str,
        delivered: bool,
        error_code: str | None = None,
        sent_at: datetime | None = None,
    ) -> NotificationDelivery:
        row = NotificationDelivery(
            user_id=user_id,
            template=template,
            message_key=message_key,
            slot=slot,
            delivered=delivered,
            error_code=error_code,
        )
        if sent_at is not None:
            row.sent_at = sent_at
        self.session.add(row)
        await self.session.flush()
        return row

    async def delivered_user_ids(
        self, template: str, message_key: str, user_ids: Iterable[UUID] | None = None
    ) -> set[UUID]:
        """Users with a DELIVERED row of ``template`` + ``message_key`` (optionally only among ``user_ids``).

        A send-now run logs every recipient under its own message key, so a re-run of the same
        job (arq retries a cancelled job from the start) skips whoever already got it.
        """
        stmt = select(NotificationDelivery.user_id).where(
            NotificationDelivery.template == template,
            NotificationDelivery.message_key == message_key,
            NotificationDelivery.delivered.is_(True),
        )
        if user_ids is not None:
            ids = list(user_ids)
            if not ids:
                return set()
            stmt = stmt.where(NotificationDelivery.user_id.in_(ids))
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    async def count_for_key(self, template: str, message_key: str) -> int:
        """Rows (any outcome) logged for ``template`` + ``message_key``: > 0 means the run already started."""
        stmt = select(func.count()).where(
            NotificationDelivery.template == template, NotificationDelivery.message_key == message_key
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def last_sent_by_user(
        self, template: str, user_ids: Iterable[UUID], *, delivered_only: bool = True
    ) -> dict[UUID, datetime]:
        """``user_id -> sent_at`` of the latest delivery of ``template`` (users without one are absent)."""
        ids = list(user_ids)
        if not ids:
            return {}
        stmt = (
            select(NotificationDelivery.user_id, func.max(NotificationDelivery.sent_at))
            .where(NotificationDelivery.template == template, NotificationDelivery.user_id.in_(ids))
            .group_by(NotificationDelivery.user_id)
        )
        if delivered_only:
            stmt = stmt.where(NotificationDelivery.delivered.is_(True))
        result = await self.session.execute(stmt)
        return {user_id: sent_at for user_id, sent_at in result.all()}

    async def sent_times_by_user(
        self, template: str, user_ids: Iterable[UUID], *, since: datetime | None = None, delivered_only: bool = True
    ) -> dict[UUID, list[datetime]]:
        """``user_id -> [sent_at, …]`` (ascending) of ``template`` deliveries, optionally since a time.

        For caps that count per user from a per-user boundary (e.g. "since the last activity"):
        fetch from the earliest boundary once, then count in Python.
        """
        ids = list(user_ids)
        if not ids:
            return {}
        stmt = (
            select(NotificationDelivery.user_id, NotificationDelivery.sent_at)
            .where(NotificationDelivery.template == template, NotificationDelivery.user_id.in_(ids))
            .order_by(NotificationDelivery.sent_at)
        )
        if delivered_only:
            stmt = stmt.where(NotificationDelivery.delivered.is_(True))
        if since is not None:
            stmt = stmt.where(NotificationDelivery.sent_at >= since)
        result = await self.session.execute(stmt)
        times: dict[UUID, list[datetime]] = {}
        for user_id, sent_at in result.all():
            times.setdefault(user_id, []).append(sent_at)
        return times

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, or_, select, update

from core.infrastructure.database.models import PromotionalBroadcast
from core.infrastructure.database.models.enums import NotificationTimeSlot
from core.infrastructure.database.repo.base import BaseRepo


class PromotionalBroadcastRepo(BaseRepo[PromotionalBroadcast]):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = PromotionalBroadcast

    async def get_active_by_time_slot(self, time_slot: NotificationTimeSlot) -> Sequence[PromotionalBroadcast]:
        """Get all active promotional broadcasts for a specific time slot"""
        stmt = (
            select(PromotionalBroadcast)
            .where(
                PromotionalBroadcast.time_slot == time_slot,
                PromotionalBroadcast.is_active,
                PromotionalBroadcast.deadline > datetime.now(UTC),
            )
            .order_by(PromotionalBroadcast.priority.desc(), PromotionalBroadcast.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_all_active(self) -> Sequence[PromotionalBroadcast]:
        """Get all active promotional broadcasts"""
        stmt = (
            select(PromotionalBroadcast)
            .where(
                PromotionalBroadcast.is_active,
                PromotionalBroadcast.deadline > datetime.now(UTC),
            )
            .order_by(PromotionalBroadcast.time_slot, PromotionalBroadcast.priority.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_creator(self, creator_telegram_id: int) -> Sequence[PromotionalBroadcast]:
        """Get all promotional broadcasts created by a specific admin.

        ``created_by_user_id`` stores the creator's Telegram id (int) — see the model
        note. Previously this took a UUID, which could never match the int column.
        """
        stmt = (
            select(PromotionalBroadcast)
            .where(PromotionalBroadcast.created_by_user_id == creator_telegram_id)
            .order_by(PromotionalBroadcast.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def expire_outdated_broadcasts(self) -> int:
        """Mark broadcasts past their deadline as inactive.

        Transaction commits at dependency layer.
        """
        stmt = (
            update(PromotionalBroadcast)
            .where(
                PromotionalBroadcast.is_active,
                PromotionalBroadcast.deadline <= datetime.now(UTC),
            )
            .values(
                is_active=False,
                completed_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def deactivate_broadcast(self, broadcast_id: int) -> bool:
        """Manually deactivate a promotional broadcast.

        Transaction commits at dependency layer.
        """
        stmt = update(PromotionalBroadcast).where(PromotionalBroadcast.id == broadcast_id).values(is_active=False)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def get_completed_broadcasts(self, limit: int = 50) -> Sequence[PromotionalBroadcast]:
        """Get recently completed promotional broadcasts.

        Uses a SQL ``.is_(False)`` predicate: ``not PromotionalBroadcast.is_active`` would be
        Python truthiness on a Column (always ``False`` at query-build time), silently
        dropping the filter.
        """
        stmt = (
            select(PromotionalBroadcast)
            .where(
                PromotionalBroadcast.is_active.is_(False),
                PromotionalBroadcast.completed_at.isnot(None),
            )
            .order_by(PromotionalBroadcast.completed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_for_admin(self, *, active: bool | None, limit: int = 100) -> Sequence[PromotionalBroadcast]:
        """List broadcasts for the admin panel, newest first.

        ``active=True`` → active rows whose deadline is still ahead (the ones a slot can still
        send); ``active=False`` → cancelled, completed or expired rows; ``None`` → all rows.
        An expired row may still have ``is_active`` set (it's only flipped after a send cycle),
        so the deadline decides here.
        """
        now = datetime.now(UTC)
        stmt = select(PromotionalBroadcast)
        if active is True:
            stmt = stmt.where(PromotionalBroadcast.is_active.is_(True), PromotionalBroadcast.deadline > now)
        elif active is False:
            stmt = stmt.where(or_(PromotionalBroadcast.is_active.is_(False), PromotionalBroadcast.deadline <= now))
        stmt = stmt.order_by(PromotionalBroadcast.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_active_by_time_slot(self) -> dict[str, int]:
        """Count active, not-yet-expired broadcasts grouped by time_slot.

        Used by the admin UI to warn when >1 active broadcast share a slot (only the
        highest-priority one actually sends per cycle).
        """
        stmt = (
            select(PromotionalBroadcast.time_slot, func.count())
            .where(
                PromotionalBroadcast.is_active.is_(True),
                PromotionalBroadcast.deadline > datetime.now(UTC),
            )
            .group_by(PromotionalBroadcast.time_slot)
        )
        result = await self.session.execute(stmt)
        return {str(slot): count for slot, count in result.all()}

    async def record_send_result(self, broadcast_id: int, success: int, fail: int, *, new_cycle: bool = True) -> None:
        """Increment delivery counters after a broadcast send cycle (or one chunk of it).

        Adds ``success + fail`` to ``sent_count``, increments the per-outcome counters,
        counts one more cycle when ``new_cycle`` (send-now records per chunk and counts the
        cycle on its first chunk only), and stamps ``last_sent_at`` = ``datetime.now(UTC)``.
        Read receipts / CTR are impossible on Telegram, so only these counters are tracked.
        """
        stmt = (
            update(PromotionalBroadcast)
            .where(PromotionalBroadcast.id == broadcast_id)
            .values(
                sent_count=PromotionalBroadcast.sent_count + success + fail,
                success_count=PromotionalBroadcast.success_count + success,
                fail_count=PromotionalBroadcast.fail_count + fail,
                cycles_run=PromotionalBroadcast.cycles_run + (1 if new_cycle else 0),
                last_sent_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

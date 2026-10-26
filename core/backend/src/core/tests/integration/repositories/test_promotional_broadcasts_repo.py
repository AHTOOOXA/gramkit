"""PromotionalBroadcastRepo against real Postgres (``db_session``, rolled back per test). No app."""

import random
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models import PromotionalBroadcast
from core.infrastructure.database.models.enums import NotificationTimeSlot
from core.infrastructure.database.repo.requests import CoreRequestsRepo

pytestmark = pytest.mark.business_logic


async def _row(
    repo: CoreRequestsRepo,
    *,
    slot: NotificationTimeSlot = NotificationTimeSlot.MORNING,
    priority: int = 80,
    deadline: datetime | None = None,
    **extra,
) -> PromotionalBroadcast:
    return await repo.promotional_broadcasts.create(
        {
            "message_type": "text",
            "message_text": "x",
            "message_html": "x",
            "has_text_formatting": False,
            "time_slot": slot,
            "deadline": deadline or datetime.now(UTC) + timedelta(days=1),
            "priority": priority,
            "created_by_user_id": random.randint(10_000_000, 99_999_999),
            **extra,
        }
    )


@pytest.fixture
def repo(db_session: AsyncSession) -> CoreRequestsRepo:
    return CoreRequestsRepo(db_session)


class TestRecordSendResult:
    async def test_increments_counters_and_stamps_last_sent(self, repo):
        row = await _row(repo)

        await repo.promotional_broadcasts.record_send_result(row.id, success=8, fail=2)

        await repo.session.refresh(row)
        assert (row.success_count, row.fail_count, row.sent_count, row.cycles_run) == (8, 2, 10, 1)
        assert row.last_sent_at is not None

    async def test_accumulates_across_cycles(self, repo):
        row = await _row(repo)

        await repo.promotional_broadcasts.record_send_result(row.id, success=5, fail=0)
        await repo.promotional_broadcasts.record_send_result(row.id, success=3, fail=1)

        await repo.session.refresh(row)
        assert (row.success_count, row.fail_count, row.sent_count, row.cycles_run) == (8, 1, 9, 2)


class TestGetCompletedBroadcasts:
    async def test_is_false_filter_returns_only_completed(self, repo):
        """Regression: ``not Column.is_active`` truthiness silently dropped the filter;
        with ``.is_(False)`` only inactive + completed_at rows come back."""
        active = await _row(repo, is_active=True)
        completed = await _row(repo, is_active=False, completed_at=datetime.now(UTC))

        rows = await repo.promotional_broadcasts.get_completed_broadcasts(limit=100)

        ids = {r.id for r in rows}
        assert completed.id in ids
        assert active.id not in ids
        assert all(r.is_active is False and r.completed_at is not None for r in rows)


class TestActiveBySlot:
    async def test_orders_by_priority_and_skips_expired_and_inactive(self, repo):
        low = await _row(repo, slot=NotificationTimeSlot.EVENING, priority=10)
        high = await _row(repo, slot=NotificationTimeSlot.EVENING, priority=900)
        expired = await _row(
            repo, slot=NotificationTimeSlot.EVENING, priority=999, deadline=datetime.now(UTC) - timedelta(hours=1)
        )
        cancelled = await _row(repo, slot=NotificationTimeSlot.EVENING, priority=998, is_active=False)
        other_slot = await _row(repo, slot=NotificationTimeSlot.MORNING, priority=999)

        rows = await repo.promotional_broadcasts.get_active_by_time_slot(NotificationTimeSlot.EVENING)

        ids = [r.id for r in rows]
        assert ids.index(high.id) < ids.index(low.id)
        assert not {expired.id, cancelled.id, other_slot.id} & set(ids)

    async def test_count_active_by_time_slot(self, repo):
        before = await repo.promotional_broadcasts.count_active_by_time_slot()
        await _row(repo, slot=NotificationTimeSlot.MORNING)
        await _row(repo, slot=NotificationTimeSlot.MORNING)
        await _row(repo, slot=NotificationTimeSlot.EVENING, deadline=datetime.now(UTC) - timedelta(hours=1))

        after = await repo.promotional_broadcasts.count_active_by_time_slot()

        morning = str(NotificationTimeSlot.MORNING)
        evening = str(NotificationTimeSlot.EVENING)
        assert after.get(morning, 0) - before.get(morning, 0) == 2
        assert after.get(evening, 0) == before.get(evening, 0)


class TestListForAdmin:
    async def test_active_and_cancelled_split(self, repo):
        active = await _row(repo)
        cancelled = await _row(repo, is_active=False, completed_at=datetime.now(UTC))

        active_ids = {r.id for r in await repo.promotional_broadcasts.list_for_admin(active=True)}
        inactive_ids = {r.id for r in await repo.promotional_broadcasts.list_for_admin(active=False)}

        assert active.id in active_ids and active.id not in inactive_ids
        assert cancelled.id in inactive_ids and cancelled.id not in active_ids

    async def test_an_expired_row_counts_as_completed(self, repo):
        """Its is_active is only flipped after a send cycle; the deadline decides for the admin list."""
        expired = await _row(repo, deadline=datetime.now(UTC) - timedelta(minutes=1))

        active_ids = {r.id for r in await repo.promotional_broadcasts.list_for_admin(active=True)}
        inactive_ids = {r.id for r in await repo.promotional_broadcasts.list_for_admin(active=False)}

        assert expired.is_active is True
        assert expired.id in inactive_ids and expired.id not in active_ids

    async def test_new_cycle_false_keeps_the_cycle_count(self, repo):
        row = await _row(repo)

        await repo.promotional_broadcasts.record_send_result(row.id, success=2, fail=1)
        await repo.promotional_broadcasts.record_send_result(row.id, success=4, fail=0, new_cycle=False)

        await repo.session.refresh(row)
        assert (row.success_count, row.fail_count, row.sent_count, row.cycles_run) == (6, 1, 7, 1)

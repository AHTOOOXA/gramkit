"""Integration tests for AdminTasksService on the core aggregator (no app installed).

Builds ``CoreRequestsService(CoreRequestsRepo(db_session))`` directly (core has no
``services`` fixture). Tasks are registered on an empty registry per test.

The audit-row shape is locked here on purpose: app tasks read it back (a once-only
guard queries ``action = 'admin_task:<name>' AND detail->'result'->>'applied' = 'true'``).
"""

import random
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AdminTaskNotFoundException
from core.infrastructure.database.models import AuditLog
from core.infrastructure.database.models.enums import UserRole
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.schemas.admin_tasks import AdminTaskInfo
from core.schemas.users import UserSchema
from core.services import admin_tasks
from core.services.admin_tasks import admin_task
from core.services.requests import CoreRequestsService


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(admin_tasks, "_REGISTRY", {})


@pytest.fixture
def core_services(db_session: AsyncSession) -> CoreRequestsService:
    return CoreRequestsService(CoreRequestsRepo(db_session))


async def _owner(services: CoreRequestsService) -> UserSchema:
    user = await services.repo.users.create(
        {
            "telegram_id": random.randint(10_000_000, 99_999_999),
            "username": f"owner_{uuid4().hex[:8]}",
            "role": UserRole.OWNER,
        }
    )
    await services.repo.session.flush()
    return UserSchema.model_validate(user)


async def _audit_rows(services: CoreRequestsService, action: str) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.action == action)
    return list((await services.repo.session.execute(stmt)).scalars().all())


def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


class TestRun:
    @pytest.mark.business_logic
    async def test_passes_request_session_and_dry_run(self, core_services: CoreRequestsService, db_session):
        name = _unique("seen")
        seen: list[tuple[object, bool]] = []

        @admin_task(name, "Records its arguments.")
        async def _task(session, *, dry_run: bool) -> dict:
            seen.append((session, dry_run))
            return {"applied": False}

        actor = await _owner(core_services)
        await core_services.admin_tasks.run(actor, name, dry_run=True)
        await core_services.admin_tasks.run(actor, name, dry_run=False)

        assert len(seen) == 2
        assert seen[0][0] is db_session
        assert [dry_run for _, dry_run in seen] == [True, False]

    @pytest.mark.business_logic
    async def test_returns_result_and_writes_exact_audit_shape(self, core_services: CoreRequestsService):
        name = _unique("shape")

        @admin_task(name, "Applies when not a dry run.", destructive=True)
        async def _task(session, *, dry_run: bool) -> dict:
            return {"applied": not dry_run, "count": 3}

        actor = await _owner(core_services)
        outcome = await core_services.admin_tasks.run(actor, name, dry_run=False)

        assert outcome.task == name
        assert outcome.dry_run is False
        assert outcome.result == {"applied": True, "count": 3}

        rows = await _audit_rows(core_services, f"admin_task:{name}")
        assert len(rows) == 1
        row = rows[0]
        assert row.actor_user_id == actor.id
        assert row.actor_role == "owner"
        assert row.target_type == "admin_task"
        assert row.target_id == name
        assert row.detail == {"dry_run": False, "result": {"applied": True, "count": 3}}

    @pytest.mark.business_logic
    async def test_applied_flag_is_queryable_as_jsonb(self, core_services: CoreRequestsService):
        """The exact query app once-only guards use finds an applied run (and not a dry one)."""
        name = _unique("guard")

        @admin_task(name, "Guarded.", destructive=True)
        async def _task(session, *, dry_run: bool) -> dict:
            return {"applied": not dry_run}

        actor = await _owner(core_services)
        guard = text(
            "SELECT count(*) FROM admin_audit_logs WHERE action = :action AND detail->'result'->>'applied' = 'true'"
        )

        await core_services.admin_tasks.run(actor, name, dry_run=True)
        dry = await core_services.repo.session.scalar(guard, {"action": f"admin_task:{name}"})
        await core_services.admin_tasks.run(actor, name, dry_run=False)
        applied = await core_services.repo.session.scalar(guard, {"action": f"admin_task:{name}"})

        assert dry == 0
        assert applied == 1

    @pytest.mark.business_logic
    async def test_unknown_task_raises_not_found(self, core_services: CoreRequestsService):
        actor = await _owner(core_services)

        with pytest.raises(AdminTaskNotFoundException, match="^Unknown task: x$"):
            await core_services.admin_tasks.run(actor, "x", dry_run=True)

    @pytest.mark.business_logic
    async def test_failing_task_propagates_and_writes_no_audit_row(self, core_services: CoreRequestsService):
        name = _unique("boom")

        @admin_task(name, "Always fails.", destructive=True)
        async def _task(session, *, dry_run: bool) -> dict:
            raise RuntimeError("task failed")

        actor = await _owner(core_services)

        with pytest.raises(RuntimeError, match="task failed"):
            await core_services.admin_tasks.run(actor, name, dry_run=False)

        assert await _audit_rows(core_services, f"admin_task:{name}") == []


class TestListTasks:
    @pytest.mark.business_logic
    def test_returns_task_info_sorted_by_name(self, core_services: CoreRequestsService):
        async def _noop(session, *, dry_run: bool) -> dict:
            return {"applied": False}

        admin_task("b_task", "B.", destructive=True)(_noop)
        admin_task("a_task", "A.")(_noop)

        assert core_services.admin_tasks.list_tasks() == [
            AdminTaskInfo(name="a_task", description="A.", destructive=False),
            AdminTaskInfo(name="b_task", description="B.", destructive=True),
        ]

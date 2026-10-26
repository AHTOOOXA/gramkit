"""Integration tests for AuditLogRepo (real PostgreSQL via testcontainers).

Covers create, the action / actor / target filters, free-text search, the date range,
and ``ON DELETE SET NULL`` on the actor FK (the trail outlives the user).
Each test seeds its own rows with unique values; the transaction rolls back after it.
"""

import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models import AuditLog, User
from core.infrastructure.database.models.enums import UserRole
from core.infrastructure.database.repo.audit_log import AuditLogRepo
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.schemas.admin_common import AdminListParams


def _params(**overrides) -> AdminListParams:
    base = dict(page=1, page_size=25, sort_by=None, sort_dir="desc", search=None, date_from=None, date_to=None)
    base.update(overrides)
    return AdminListParams(**base)


async def _seed_user(db_session: AsyncSession, role: UserRole = UserRole.ADMIN) -> User:
    user = await CoreRequestsRepo(db_session).users.create(
        {
            "telegram_id": random.randint(10_000_000, 99_999_999),
            "username": f"actor_{uuid4().hex[:8]}",
            "role": role,
        }
    )
    await db_session.flush()
    return user


async def _row(repo: AuditLogRepo, actor: User | None, action: str, **extra) -> AuditLog:
    return await repo.create(
        {
            "actor_user_id": actor.id if actor else None,
            "actor_telegram_id": actor.telegram_id if actor else None,
            "actor_username": actor.username if actor else None,
            "actor_role": "admin",
            "action": action,
            **extra,
        }
    )


@pytest.fixture
def audit_repo(db_session: AsyncSession) -> AuditLogRepo:
    return AuditLogRepo(db_session)


class TestAuditLogRepoCreate:
    @pytest.mark.contract
    async def test_create_persists_row_with_id_and_timestamp(self, audit_repo: AuditLogRepo, db_session):
        actor = await _seed_user(db_session)

        row = await _row(audit_repo, actor, "gift_subscription", target_type="user", target_id="abc", detail={"a": 1})

        assert isinstance(row.id, int)
        assert row.created_at is not None
        assert row.actor_user_id == actor.id
        assert row.detail == {"a": 1}


class TestAuditLogRepoFilters:
    @pytest.mark.contract
    async def test_action_filter_returns_only_that_action(self, audit_repo: AuditLogRepo, db_session):
        actor = await _seed_user(db_session)
        action = f"act_{uuid4().hex[:8]}"
        await _row(audit_repo, actor, action)
        await _row(audit_repo, actor, action)
        await _row(audit_repo, actor, f"other_{uuid4().hex[:8]}")

        rows, total = await audit_repo.list_filtered(_params(), action=action)

        assert total == 2
        assert {r.action for r in rows} == {action}

    @pytest.mark.contract
    async def test_actor_filter_returns_only_that_actor(self, audit_repo: AuditLogRepo, db_session):
        actor = await _seed_user(db_session)
        other = await _seed_user(db_session)
        await _row(audit_repo, actor, "change_role")
        await _row(audit_repo, other, "change_role")

        rows, total = await audit_repo.list_filtered(_params(), actor_user_id=actor.id)

        assert total == 1
        assert rows[0].actor_user_id == actor.id

    @pytest.mark.contract
    async def test_target_user_filter_matches_user_targets_only(self, audit_repo: AuditLogRepo, db_session):
        actor = await _seed_user(db_session)
        target_id = str(uuid4())
        await _row(audit_repo, actor, "gift_subscription", target_type="user", target_id=target_id)
        # Same id string but a different target type must not match.
        await _row(audit_repo, actor, "admin_task:x", target_type="admin_task", target_id=target_id)

        rows, total = await audit_repo.list_filtered(_params(), target_user_id=target_id)

        assert total == 1
        assert rows[0].target_type == "user"
        assert rows[0].target_id == target_id

    @pytest.mark.contract
    async def test_search_matches_action_case_insensitively(self, audit_repo: AuditLogRepo, db_session):
        actor = await _seed_user(db_session)
        marker = uuid4().hex[:8]
        await _row(audit_repo, actor, f"needle_{marker}")
        await _row(audit_repo, actor, f"hay_{uuid4().hex[:8]}")

        rows, total = await audit_repo.list_filtered(_params(search=f"NEEDLE_{marker.upper()}"))

        assert total == 1
        assert rows[0].action == f"needle_{marker}"

    @pytest.mark.contract
    async def test_search_like_metacharacters_match_literally(self, audit_repo: AuditLogRepo, db_session):
        """``_`` and ``%`` in the search term are literal characters, not LIKE pattern characters."""
        actor = await _seed_user(db_session)
        marker = uuid4().hex[:8]
        literal = await _row(audit_repo, actor, f"lit_{marker}_x")
        await _row(audit_repo, actor, f"lit_{marker}Zx")  # would match if "_" were a LIKE pattern character

        rows, total = await audit_repo.list_filtered(_params(search=f"{marker}_x"))
        assert total == 1
        assert rows[0].id == literal.id

        _, total = await audit_repo.list_filtered(_params(search=f"lit_{marker}%x"))
        assert total == 0

    @pytest.mark.contract
    async def test_date_range_bounds_created_at(self, audit_repo: AuditLogRepo, db_session):
        actor = await _seed_user(db_session)
        action = f"dated_{uuid4().hex[:8]}"
        now = datetime.now(UTC)
        await _row(audit_repo, actor, action, created_at=now - timedelta(days=10))
        inside = await _row(audit_repo, actor, action, created_at=now - timedelta(days=5))
        await _row(audit_repo, actor, action, created_at=now - timedelta(days=1))

        rows, total = await audit_repo.list_filtered(
            _params(date_from=now - timedelta(days=6), date_to=now - timedelta(days=4)),
            action=action,
        )

        assert total == 1
        assert rows[0].id == inside.id

    @pytest.mark.contract
    async def test_pagination_returns_unpaginated_total(self, audit_repo: AuditLogRepo, db_session):
        actor = await _seed_user(db_session)
        action = f"paged_{uuid4().hex[:8]}"
        for _ in range(3):
            await _row(audit_repo, actor, action)

        rows, total = await audit_repo.list_filtered(_params(page=2, page_size=2), action=action)

        assert total == 3
        assert len(rows) == 1


class TestAuditLogActorDeletion:
    @pytest.mark.contract
    async def test_actor_deleted_sets_actor_user_id_null_and_keeps_row(self, audit_repo: AuditLogRepo, db_session):
        """ON DELETE SET NULL: the trail survives the actor; the snapshot fields stay."""
        actor = await _seed_user(db_session)
        row = await _row(audit_repo, actor, "reset_user", target_type="user", target_id=str(uuid4()))
        telegram_id = actor.telegram_id

        await db_session.execute(delete(User).where(User.id == actor.id))
        await db_session.flush()
        await db_session.refresh(row)

        assert row.actor_user_id is None
        assert row.actor_telegram_id == telegram_id
        assert row.action == "reset_user"


class TestAuditLogDistinctActions:
    @pytest.mark.contract
    async def test_distinct_actions_sorted_and_deduplicated(self, audit_repo: AuditLogRepo, db_session):
        actor = await _seed_user(db_session)
        marker = uuid4().hex[:8]
        for action in (f"{marker}_b", f"{marker}_a", f"{marker}_b"):
            await _row(audit_repo, actor, action)

        actions = await audit_repo.distinct_actions()

        mine = [a for a in actions if a.startswith(marker)]
        assert mine == [f"{marker}_a", f"{marker}_b"]
        assert len(actions) == len(set(actions))

    @pytest.mark.contract
    async def test_distinct_actions_respects_limit(self, audit_repo: AuditLogRepo, db_session):
        actor = await _seed_user(db_session)
        for i in range(3):
            await _row(audit_repo, actor, f"lim_{uuid4().hex[:8]}_{i}")

        assert len(await audit_repo.distinct_actions(limit=2)) == 2

"""Integration tests for AdminUsersRepo (real PostgreSQL via testcontainers).

Covers the role / user_type filters, search, the sort whitelist fallback, the
per-user sub-lists, and the active-subscription definition used by the detail page.
Rows carry a per-test marker in the username, and searches are scoped to it.
"""

import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models import User
from core.infrastructure.database.models.enums import (
    PaymentProvider,
    PaymentStatus,
    SubscriptionStatus,
    UserRole,
    UserType,
)
from core.infrastructure.database.repo.admin_users import AdminUsersRepo
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.schemas.admin_common import AdminListParams


def _params(**overrides) -> AdminListParams:
    base = dict(page=1, page_size=25, sort_by=None, sort_dir="desc", search=None, date_from=None, date_to=None)
    base.update(overrides)
    return AdminListParams(**base)


async def _seed_user(
    db_session: AsyncSession,
    marker: str,
    *,
    role: UserRole = UserRole.USER,
    user_type: UserType = UserType.REGISTERED,
    suffix: str = "",
) -> User:
    user = await CoreRequestsRepo(db_session).users.create(
        {
            "telegram_id": random.randint(10_000_000, 99_999_999),
            "username": f"{marker}_{suffix or uuid4().hex[:6]}",
            "role": role,
            "user_type": user_type,
        }
    )
    await db_session.flush()
    return user


async def _seed_subscription(db_session: AsyncSession, user: User, status: SubscriptionStatus, end_in_days: int):
    now = datetime.now(UTC)
    sub = await CoreRequestsRepo(db_session).subscriptions.create(
        {
            "user_id": user.id,
            "product_id": "TEST_SUB",
            "provider_id": PaymentProvider.GIFT,
            "status": status,
            "currency": "RUB",
            "start_date": now - timedelta(days=30),
            "end_date": now + timedelta(days=end_in_days),
        }
    )
    await db_session.flush()
    return sub


@pytest.fixture
def admin_users_repo(db_session: AsyncSession) -> AdminUsersRepo:
    return AdminUsersRepo(db_session)


@pytest.fixture
def marker() -> str:
    return f"m{uuid4().hex[:10]}"


class TestSearchUsers:
    @pytest.mark.contract
    async def test_search_scopes_rows_and_total(self, admin_users_repo: AdminUsersRepo, db_session, marker):
        await _seed_user(db_session, marker)
        await _seed_user(db_session, marker)
        await _seed_user(db_session, f"x{uuid4().hex[:10]}")

        rows, total = await admin_users_repo.search_users(_params(search=marker))

        assert total == 2
        assert all(r.username.startswith(marker) for r in rows)

    @pytest.mark.contract
    async def test_role_filter_returns_only_that_role(self, admin_users_repo: AdminUsersRepo, db_session, marker):
        admin = await _seed_user(db_session, marker, role=UserRole.ADMIN)
        await _seed_user(db_session, marker, role=UserRole.USER)

        rows, total = await admin_users_repo.search_users(_params(search=marker), role="admin")

        assert total == 1
        assert rows[0].id == admin.id

    @pytest.mark.contract
    async def test_user_type_filter_returns_only_that_type(self, admin_users_repo: AdminUsersRepo, db_session, marker):
        guest = await _seed_user(db_session, marker, user_type=UserType.GUEST)
        await _seed_user(db_session, marker, user_type=UserType.REGISTERED)

        rows, total = await admin_users_repo.search_users(_params(search=marker), user_type="GUEST")

        assert total == 1
        assert rows[0].id == guest.id

    @pytest.mark.contract
    async def test_whitelisted_sort_is_honoured(self, admin_users_repo: AdminUsersRepo, db_session, marker):
        await _seed_user(db_session, marker, suffix="b")
        await _seed_user(db_session, marker, suffix="a")
        await _seed_user(db_session, marker, suffix="c")

        rows, _ = await admin_users_repo.search_users(_params(search=marker, sort_by="username", sort_dir="asc"))

        assert [r.username for r in rows] == [f"{marker}_a", f"{marker}_b", f"{marker}_c"]

    @pytest.mark.contract
    async def test_unknown_sort_column_falls_back_to_default(
        self, admin_users_repo: AdminUsersRepo, db_session, marker
    ):
        """A bogus sort_by doesn't error: the default sort (created_at) is used."""
        for _ in range(2):
            await _seed_user(db_session, marker)

        rows, total = await admin_users_repo.search_users(_params(search=marker, sort_by="password; DROP TABLE"))

        assert total == 2
        assert len(rows) == 2


class TestPerUserSubLists:
    @pytest.mark.contract
    async def test_list_payments_scoped_to_user(self, admin_users_repo: AdminUsersRepo, db_session, marker):
        user = await _seed_user(db_session, marker)
        other = await _seed_user(db_session, marker)
        repo = CoreRequestsRepo(db_session)
        for owner in (user, user, other):
            await repo.payments.create(
                {
                    "user_id": owner.id,
                    "product_id": "TEST_PRODUCT",
                    "provider_id": PaymentProvider.YOOKASSA,
                    "amount": 100.0,
                    "currency": "RUB",
                    "status": PaymentStatus.SUCCEEDED,
                    "provider_metadata": {},
                }
            )
        await db_session.flush()

        rows, total = await admin_users_repo.list_payments(user.id, _params())

        assert total == 2
        assert {p.user_id for p in rows} == {user.id}
        assert await admin_users_repo.count_payments(user.id) == 2

    @pytest.mark.contract
    async def test_list_subscriptions_newest_first(self, admin_users_repo: AdminUsersRepo, db_session, marker):
        user = await _seed_user(db_session, marker)
        await _seed_subscription(db_session, user, SubscriptionStatus.EXPIRED, end_in_days=-1)
        await _seed_subscription(db_session, user, SubscriptionStatus.ACTIVE, end_in_days=10)

        rows = await admin_users_repo.list_subscriptions(user.id)

        assert len(rows) == 2
        assert rows[0].start_date >= rows[1].start_date


class TestActiveSubscription:
    @pytest.mark.contract
    @pytest.mark.parametrize(
        ("status", "end_in_days", "is_active"),
        [
            (SubscriptionStatus.ACTIVE, 10, True),
            (SubscriptionStatus.PAST_DUE, 10, True),
            # A canceled sub still runs to its end date.
            (SubscriptionStatus.CANCELED, 10, True),
            (SubscriptionStatus.EXPIRED, 10, False),
            (SubscriptionStatus.ACTIVE, -1, False),
        ],
    )
    async def test_active_subscription_definition(
        self, admin_users_repo: AdminUsersRepo, db_session, marker, status, end_in_days, is_active
    ):
        user = await _seed_user(db_session, marker)
        sub = await _seed_subscription(db_session, user, status, end_in_days)

        active = await admin_users_repo.get_active_subscription(user.id)

        if is_active:
            assert active is not None
            assert active.id == sub.id
        else:
            assert active is None

    @pytest.mark.contract
    async def test_latest_ending_entitled_subscription_wins(self, admin_users_repo: AdminUsersRepo, db_session, marker):
        user = await _seed_user(db_session, marker)
        await _seed_subscription(db_session, user, SubscriptionStatus.CANCELED, end_in_days=5)
        later = await _seed_subscription(db_session, user, SubscriptionStatus.ACTIVE, end_in_days=40)

        active = await admin_users_repo.get_active_subscription(user.id)

        assert active is not None
        assert active.id == later.id

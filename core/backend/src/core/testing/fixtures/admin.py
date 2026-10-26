"""Admin-role HTTP client fixtures for the admin contract tests.

Each fixture authenticates a fresh Telegram user through the app (so the user row is
created by the real auth flow), then flips its DB role. RBAC reads the role off the
freshly loaded user on every request, and its config override only forces OWNER for
telegram ids in ``RBAC__OWNER_IDS`` (empty in tests), so the DB role governs.

Requires the app's ``test_app`` fixture (dependency overrides wired to ``db_session``)
and core's ``db_session``. Apps import these into their conftest and add them to
``__all__`` so pytest discovers them.
"""

import random
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import UserRole
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.testing.fixtures.auth import generate_telegram_init_data


async def _client_with_role(test_app, db_session: AsyncSession, role: UserRole) -> AsyncGenerator[AsyncClient]:
    telegram_user_id = random.randint(100000, 9999999)
    username = f"{role.value}_{uuid4().hex[:8]}"
    init_data = generate_telegram_init_data(
        user_id=telegram_user_id,
        username=username,
        bot_token=settings.bot.token,
    )
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers={"initData": init_data},
    ) as c:
        # Materialize the user, then promote it.
        me = await c.get("/users/me")
        assert me.status_code == 200
        repo = CoreRequestsRepo(db_session)
        user = await repo.users.get_by_telegram_id(telegram_user_id)
        await repo.users.update_user(user.id, {"role": role})
        await db_session.flush()
        yield c


@pytest_asyncio.fixture
async def admin_client(test_app, db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """HTTP client whose backing user has been promoted to the ADMIN role."""
    async for c in _client_with_role(test_app, db_session, UserRole.ADMIN):
        yield c


@pytest_asyncio.fixture
async def owner_client(test_app, db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """HTTP client whose backing user has been promoted to the OWNER role."""
    async for c in _client_with_role(test_app, db_session, UserRole.OWNER):
        yield c

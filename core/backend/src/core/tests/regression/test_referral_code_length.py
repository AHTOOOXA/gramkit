"""Regression test: over-long /start deep-link payload crashes the bot.

Date: 2026-06-05
Impact: High (any /start with a payload longer than 40 chars crashed the
        aiogram update handler in production).
Root Cause: ``UserService.process_referral`` wrote the raw ``/start`` deep-link
        payload (Telegram allows up to 64 chars) straight into the
        ``users.referral_code`` column, which is ``String(40)``. asyncpg then
        raised ``StringDataRightTruncationError: value too long for type
        character varying(40)`` and the handler crashed.
Fix: ``process_referral`` now guards on length (and empty/whitespace) and skips
        storing over-long values, letting onboarding proceed normally.

Uses a real PostgreSQL testcontainer (via ``db_session``) so the truncation
behaviour is reproduced against production-parity Postgres, not a mock.
"""

from typing import Any, cast

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models.users import User
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.services.users import MAX_REFERRAL_CODE_LENGTH, UserService


async def _make_user(db_session: AsyncSession) -> User:
    """Create a bare user directly via the repo and return it."""
    repo = CoreRequestsRepo(db_session)
    return await repo.users.get_or_create_user({"username": "ref_test_user"})


def _make_service(db_session: AsyncSession) -> UserService:
    """Build a UserService with a real repo (producer/services/bot unused here)."""
    repo = CoreRequestsRepo(db_session)
    # process_referral only uses self.repo; services/bot are unused here.
    return UserService(repo=repo, producer=None, services=cast(Any, None), bot=cast(Any, None))


async def _persisted_referral_code(db_session: AsyncSession, user_id) -> str | None:
    """Re-read the user from the DB and return its stored referral_code."""
    result = await db_session.execute(select(User).where(User.id == user_id))
    return result.scalar_one().referral_code


@pytest.mark.regression
async def test_overlong_referral_code_does_not_crash_or_persist(db_session: AsyncSession):
    """A 41+ char /start payload must NOT raise and must NOT be persisted.

    Reproduces the prod StringDataRightTruncationError and proves it's fixed.
    """
    # Arrange: user with no referral code yet + an over-long payload (Telegram
    # allows up to 64 chars; the column is String(40)).
    user = await _make_user(db_session)
    overlong = "a" * (MAX_REFERRAL_CODE_LENGTH + 1)  # 41 chars -> would truncate
    service = _make_service(db_session)

    # Act: must not raise (previously crashed with StringDataRightTruncationError)
    await service.process_referral(overlong, user.id)

    # Assert: nothing stored, column stays None
    assert await _persisted_referral_code(db_session, user.id) is None


@pytest.mark.regression
async def test_normal_referral_code_still_persists(db_session: AsyncSession):
    """A normal short code (e.g. r-123456) is still stored as before."""
    # Arrange
    user = await _make_user(db_session)
    service = _make_service(db_session)

    # Act
    await service.process_referral("r-123456", user.id)

    # Assert
    assert await _persisted_referral_code(db_session, user.id) == "r-123456"


@pytest.mark.regression
async def test_existing_referral_code_is_not_overwritten(db_session: AsyncSession):
    """A user who already has a referral_code keeps it (existing behaviour)."""
    # Arrange: user already attributed to "r-111"
    user = await _make_user(db_session)
    service = _make_service(db_session)
    await service.process_referral("r-111", user.id)

    # Act: a second /start with a different code
    await service.process_referral("r-222", user.id)

    # Assert: first attribution wins
    assert await _persisted_referral_code(db_session, user.id) == "r-111"

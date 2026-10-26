"""``seen_features`` merge on the core aggregator (no app installed).

Covers the correctness guarantee of the primitive: the atomic JSONB ``||`` merge keeps the
other top-level keys (no lost updates), and a record-valued key is replaced whole.
Builds ``CoreRequestsService(CoreRequestsRepo(db_session))`` directly (core has no
``services`` fixture).
"""

import random
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models import User
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.services.requests import CoreRequestsService


@pytest.fixture
def core_services(db_session: AsyncSession) -> CoreRequestsService:
    return CoreRequestsService(CoreRequestsRepo(db_session))


async def _seed_user(services: CoreRequestsService) -> User:
    user = await services.repo.users.create(
        {"telegram_id": random.randint(10_000_000, 99_999_999), "username": f"seen_{uuid4().hex[:8]}"}
    )
    await services.repo.session.flush()
    return user


@pytest.mark.business_logic
class TestSeenFeaturesMerge:
    async def test_default_is_empty(self, core_services: CoreRequestsService):
        user = await _seed_user(core_services)
        fetched = await core_services.users.get_user_by_id(user.id)
        assert fetched.seen_features == {}

    async def test_merge_adds_key(self, core_services: CoreRequestsService):
        user = await _seed_user(core_services)
        updated = await core_services.users.merge_seen_features(user.id, {"reveal.profile_tab": True})
        assert updated.seen_features == {"reveal.profile_tab": True}

    async def test_merge_preserves_other_keys(self, core_services: CoreRequestsService):
        # The core guarantee: a later merge must not clobber an earlier key.
        user = await _seed_user(core_services)
        await core_services.users.merge_seen_features(user.id, {"reveal.profile_tab": True})
        updated = await core_services.users.merge_seen_features(user.id, {"whatsnew.dashboard": {"v": 2}})
        assert updated.seen_features == {"reveal.profile_tab": True, "whatsnew.dashboard": {"v": 2}}

    async def test_merge_same_key_overwrites_wholesale(self, core_services: CoreRequestsService):
        # Record-valued keys are replaced as a unit (callers send the full value).
        user = await _seed_user(core_services)
        await core_services.users.merge_seen_features(
            user.id, {"nudge.push_optin": {"n": 1, "at": "2026-06-01T00:00:00Z"}}
        )
        updated = await core_services.users.merge_seen_features(
            user.id, {"nudge.push_optin": {"n": 2, "at": "2026-06-08T00:00:00Z", "ack": "dismissed"}}
        )
        assert updated.seen_features["nudge.push_optin"] == {
            "n": 2,
            "at": "2026-06-08T00:00:00Z",
            "ack": "dismissed",
        }

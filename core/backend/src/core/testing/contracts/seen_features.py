"""Base test class for the ``seen_features`` endpoint contract tests.

Covers ``PATCH /users/me/seen-features`` (``core.infrastructure.fastapi.routers.users``):

- the patch is merged into ``user.seen_features`` (other keys kept, a record replaced whole),
  and ``GET /users/me`` reflects it;
- invalid keys are rejected (422);
- the shared GUEST user (every logged-out web visitor) can't write (403).

The merge itself and the body validation are unit/DB-tested in core
(``core/tests/unit/test_seen_features_patch.py``,
``core/tests/integration/repositories/test_users_seen_features.py``).

Apps inherit this class and provide the fixtures:
- ``authenticated_client``: a Telegram-authenticated client for a fresh user
- ``client``: an unauthenticated client (resolved to the GUEST user by the app's ``get_user``)

Keys are unique per test, so the suite stays parallel-safe on a shared database.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

URL = "/users/me/seen-features"


def _suffix() -> str:
    return uuid4().hex[:10]


class BaseSeenFeaturesTests:
    """Base class for ``seen_features`` endpoint contract tests."""

    @pytest.mark.contract
    async def test_mark_seen_features_merges(self, authenticated_client: AsyncClient):
        """Patches merge by top-level key; a record-valued key is replaced whole."""
        reveal, whatsnew, nudge = (f"reveal.t_{_suffix()}", f"whatsnew.t_{_suffix()}", f"nudge.t_{_suffix()}")

        first = await authenticated_client.patch(URL, json={reveal: True})
        assert first.status_code == 200, first.text
        assert first.json()["seen_features"][reveal] is True

        second = await authenticated_client.patch(URL, json={whatsnew: {"v": 2}})
        assert second.status_code == 200, second.text
        features = second.json()["seen_features"]
        assert features[reveal] is True
        assert features[whatsnew] == {"v": 2}

        await authenticated_client.patch(URL, json={nudge: {"n": 1, "at": "2026-06-01T00:00:00Z"}})
        third = await authenticated_client.patch(URL, json={nudge: {"n": 2, "ack": "dismissed"}})
        assert third.status_code == 200, third.text
        assert third.json()["seen_features"][nudge] == {"n": 2, "ack": "dismissed"}

        me = (await authenticated_client.get("/users/me")).json()["seen_features"]
        assert me[reveal] is True
        assert me[whatsnew] == {"v": 2}
        assert me[nudge] == {"n": 2, "ack": "dismissed"}

    @pytest.mark.contract
    async def test_mark_seen_features_rejects_invalid_key(self, authenticated_client: AsyncClient):
        """Keys must be dotted lowercase identifiers."""
        response = await authenticated_client.patch(URL, json={"Bad Key": True})

        assert response.status_code == 422

    @pytest.mark.contract
    async def test_mark_seen_features_forbidden_for_guest(self, client: AsyncClient):
        """The GUEST row is shared by every logged-out visitor, so it never stores gating state."""
        key = f"reveal.t_{_suffix()}"

        response = await client.patch(URL, json={key: True})

        assert response.status_code == 403
        me = (await client.get("/users/me")).json()
        assert me["user_type"] == "GUEST"
        assert key not in me["seen_features"]

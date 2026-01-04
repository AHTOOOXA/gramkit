"""Base test class for authentication contract tests.

Tests cover:
- Telegram Mini App authentication via initData header
- Guest user fallback for unauthenticated requests
- Security boundaries (invalid signatures, tampered data)
- User isolation between different telegram_ids

Apps inherit this class - fixtures are provided by app's conftest.py.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from core.infrastructure.config import settings
from core.testing.fixtures.auth import generate_telegram_init_data


class BaseAuthTests:
    """Base class for auth contract tests. Apps inherit and provide fixtures."""

    # =========================================================================
    # Telegram Auth Tests
    # =========================================================================

    @pytest.mark.contract
    async def test_valid_init_data_authenticates_user(self, authenticated_client: AsyncClient):
        """Valid signed initData creates registered user."""
        response = await authenticated_client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["user_type"] == "REGISTERED"
        assert "id" in data

    @pytest.mark.contract
    async def test_same_telegram_id_returns_same_user(self, authenticated_client: AsyncClient):
        """Idempotent user creation: same telegram_id returns same user."""
        r1 = await authenticated_client.get("/users/me")
        r2 = await authenticated_client.get("/users/me")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]

    @pytest.mark.contract
    async def test_invalid_signature_returns_401(self, test_app):
        """Tampered initData (invalid HMAC) is rejected with 401."""
        tampered_init_data = "user=%7B%22id%22%3A123%7D&auth_date=1234567890&hash=invalid"

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
            headers={"initData": tampered_init_data},
        ) as client:
            response = await client.get("/users/me")

        assert response.status_code == 401

    # =========================================================================
    # Guest Auth Tests
    # =========================================================================

    @pytest.mark.contract
    async def test_missing_init_data_returns_guest(self, client: AsyncClient):
        """No initData header returns guest user."""
        response = await client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["user_type"] == "GUEST"
        assert data["id"] is not None

    # =========================================================================
    # User Isolation Tests
    # =========================================================================

    @pytest.mark.contract
    async def test_different_telegram_ids_create_different_users(self, test_app):
        """Two different telegram_ids create two different users."""
        init_data_1 = generate_telegram_init_data(
            user_id=111111111,
            username="user_one",
            bot_token=settings.bot.token,
        )
        init_data_2 = generate_telegram_init_data(
            user_id=222222222,
            username="user_two",
            bot_token=settings.bot.token,
        )

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
            headers={"initData": init_data_1},
        ) as client1:
            user1 = (await client1.get("/users/me")).json()

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
            headers={"initData": init_data_2},
        ) as client2:
            user2 = (await client2.get("/users/me")).json()

        assert user1["id"] != user2["id"]
        assert user1["telegram_id"] != user2["telegram_id"]

    # =========================================================================
    # Regression Tests
    # =========================================================================

    @pytest.mark.regression
    @pytest.mark.issue(1)
    async def test_invalid_init_data_returns_401_not_500(self, test_app):
        """
        Regression: Invalid initData should return 401, not crash with 500.

        Root cause: Auth middleware didn't handle malformed initData gracefully.
        Fix: Added try/except around initData parsing, return 401 on failure.
        """
        malformed_data = "this-is-not-valid-init-data"

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
            headers={"initData": malformed_data},
        ) as client:
            response = await client.get("/users/me")

        assert response.status_code == 401

    @pytest.mark.regression
    @pytest.mark.issue(2)
    async def test_empty_init_data_returns_guest_not_crash(self, test_app):
        """
        Regression: Empty initData header should return guest user, not crash.

        Root cause: Empty string passed to URL parser caused ValueError.
        Fix: Check for empty/None initData before parsing.
        """
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
            headers={"initData": ""},
        ) as client:
            response = await client.get("/users/me")

        assert response.status_code == 200
        assert response.json()["user_type"] == "GUEST"

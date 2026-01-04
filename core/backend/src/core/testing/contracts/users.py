"""Base test class for user endpoint contract tests.

Tests cover:
- User profile retrieval (GET /users/me)
- User profile updates (PATCH /users/me)
- User data isolation between different users

Apps inherit this class - fixtures are provided by app's conftest.py.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from core.infrastructure.config import settings
from core.testing.fixtures.auth import generate_telegram_init_data


class BaseUserTests:
    """Base class for user endpoint contract tests."""

    # =========================================================================
    # User Profile Tests
    # =========================================================================

    @pytest.mark.contract
    async def test_get_user_returns_profile(self, authenticated_client: AsyncClient):
        """GET /users/me returns complete user profile."""
        response = await authenticated_client.get("/users/me")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "id" in data
        assert "telegram_id" in data
        assert "username" in data
        assert "user_type" in data
        assert "created_at" in data

    @pytest.mark.contract
    async def test_user_profile_reflects_telegram_data(self, authenticated_client: AsyncClient):
        """User profile contains data from Telegram initData."""
        response = await authenticated_client.get("/users/me")
        data = response.json()

        assert data["username"].startswith("test_")
        assert data["user_type"] == "REGISTERED"

    # =========================================================================
    # User Update Tests
    # =========================================================================

    @pytest.mark.contract
    async def test_update_user_persists_changes(self, authenticated_client: AsyncClient):
        """PATCH /users/me persists profile updates."""
        update_response = await authenticated_client.patch(
            "/users/me",
            json={"display_name": "Updated Name"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["display_name"] == "Updated Name"

        # Verify persisted
        get_response = await authenticated_client.get("/users/me")
        assert get_response.json()["display_name"] == "Updated Name"

    @pytest.mark.contract
    async def test_update_user_onboarding(self, authenticated_client: AsyncClient):
        """PATCH /users/me with is_onboarded=true works."""
        response = await authenticated_client.patch(
            "/users/me",
            json={"is_onboarded": True},
        )

        assert response.status_code == 200
        assert response.json()["is_onboarded"] is True

    # =========================================================================
    # User Isolation Tests
    # =========================================================================

    @pytest.mark.contract
    async def test_users_cannot_see_each_other(self, test_app):
        """Each user only sees their own profile via /users/me."""
        init_data_a = generate_telegram_init_data(
            user_id=333333333,
            username="user_alpha",
            bot_token=settings.bot.token,
        )
        init_data_b = generate_telegram_init_data(
            user_id=444444444,
            username="user_beta",
            bot_token=settings.bot.token,
        )

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
            headers={"initData": init_data_a},
        ) as client_a:
            user_a = (await client_a.get("/users/me")).json()

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
            headers={"initData": init_data_b},
        ) as client_b:
            user_b = (await client_b.get("/users/me")).json()

        assert user_a["username"] == "user_alpha"
        assert user_b["username"] == "user_beta"
        assert user_a["id"] != user_b["id"]

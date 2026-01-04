"""Contract tests for Telegram deep link authentication.

Note: These tests require full infrastructure (Redis for sessions/tokens).
They are marked to be skipped in lightweight test mode.
Full integration tests should be run with the Docker infrastructure.
"""

import pytest
from httpx import AsyncClient

SKIP_REASON = "Requires full infrastructure (Redis for sessions/tokens)"


@pytest.mark.contract
class TestTelegramLinkAuthStart:
    """Tests for POST /auth/telegram/link/start."""

    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_start_returns_token_and_bot_url(self, client: AsyncClient):
        """Should return token and bot URL."""
        response = await client.post("/auth/telegram/link/start")

        assert response.status_code == 200

        data = response.json()
        assert "token" in data
        assert "bot_url" in data
        assert "expires_in" in data

        assert len(data["token"]) > 20
        assert data["bot_url"].startswith("https://t.me/")
        assert "start=auth_" in data["bot_url"]
        assert data["expires_in"] == 300


@pytest.mark.contract
class TestTelegramLinkAuthCheck:
    """Tests for GET /auth/telegram/link/check."""

    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_check_pending_token(self, client: AsyncClient):
        """Pending token should return pending status."""
        start_response = await client.post("/auth/telegram/link/start")
        token = start_response.json()["token"]

        response = await client.get(f"/auth/telegram/link/check?token={token}")

        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_check_invalid_token_returns_410(self, client: AsyncClient):
        """Invalid/expired token should return 410 Gone."""
        response = await client.get("/auth/telegram/link/check?token=nonexistent_token")

        assert response.status_code == 410

    @pytest.mark.skip(reason=SKIP_REASON)
    async def test_check_missing_token_returns_422(self, client: AsyncClient):
        """Missing token param should return 422."""
        response = await client.get("/auth/telegram/link/check")

        assert response.status_code == 422

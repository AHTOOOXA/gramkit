"""
Contract tests for admin_broadcast_job.

Tests the actual job logic with real database and captured messages.
"""

from unittest.mock import patch

import pytest

from app.worker.jobs import admin_broadcast_job


@pytest.mark.contract
class TestAdminBroadcastJob:
    """Tests for admin broadcast job."""

    async def test_sends_to_all_admins(self, worker_ctx, mock_bot):
        """Job sends message to all configured admins."""
        with patch("core.infrastructure.config.settings") as mock_settings:
            mock_settings.rbac.owner_ids = [111, 222, 333]

            result = await admin_broadcast_job(worker_ctx.ctx_dict, "Test broadcast")

        assert result["sent"] == 3
        assert len(mock_bot.messages) == 3
        assert all(m.text == "Test broadcast" for m in mock_bot.messages)
        assert {m.chat_id for m in mock_bot.messages} == {111, 222, 333}

    async def test_handles_empty_admin_list(self, worker_ctx, mock_bot):
        """Job handles empty admin list gracefully."""
        with patch("core.infrastructure.config.settings") as mock_settings:
            mock_settings.rbac.owner_ids = []

            result = await admin_broadcast_job(worker_ctx.ctx_dict, "Test")

        assert result["sent"] == 0
        assert len(mock_bot.messages) == 0

    async def test_continues_on_send_failure(self, worker_ctx):
        """Job continues sending even if one admin fails."""
        # Create bot that fails for one admin
        from unittest.mock import AsyncMock

        fail_bot = AsyncMock()
        call_count = [0]

        async def send_message(chat_id, text, **kwargs):
            call_count[0] += 1
            if chat_id == 222:
                raise Exception("Send failed")
            return AsyncMock(message_id=call_count[0])

        fail_bot.send_message = send_message
        worker_ctx.ctx_dict["bot"] = fail_bot

        with patch("core.infrastructure.config.settings") as mock_settings:
            mock_settings.rbac.owner_ids = [111, 222, 333]

            result = await admin_broadcast_job(worker_ctx.ctx_dict, "Test")

        # 2 succeeded, 1 failed
        assert result["sent"] == 2

    async def test_returns_sent_count(self, worker_ctx, mock_bot):
        """Job returns count of successfully sent messages."""
        with patch("core.infrastructure.config.settings") as mock_settings:
            mock_settings.rbac.owner_ids = [111, 222]

            result = await admin_broadcast_job(worker_ctx.ctx_dict, "Test")

        assert "sent" in result
        assert result["sent"] == 2

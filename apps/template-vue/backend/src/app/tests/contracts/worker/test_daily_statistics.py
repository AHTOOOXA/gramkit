"""
Contract tests for daily_admin_statistics_job.

Tests the actual job logic with real database and captured messages.
"""

from unittest.mock import patch

import pytest

from app.worker.jobs import daily_admin_statistics_job


@pytest.mark.contract
class TestDailyAdminStatisticsJob:
    """Tests for daily statistics job."""

    async def test_sends_statistics_to_admins(self, worker_ctx, mock_bot):
        """Job gathers statistics and sends to admins."""
        with patch("core.infrastructure.config.settings") as mock_settings:
            mock_settings.rbac.owner_ids = [111, 222]

            result = await daily_admin_statistics_job(worker_ctx.ctx_dict)

        assert result["sent"] == 2
        assert len(mock_bot.messages) == 2

    async def test_formats_statistics_message(self, worker_ctx, mock_bot):
        """Job formats statistics into readable message."""
        with patch("core.infrastructure.config.settings") as mock_settings:
            mock_settings.rbac.owner_ids = [111]

            await daily_admin_statistics_job(worker_ctx.ctx_dict)

        # Message should contain some statistics content
        msg = mock_bot.messages[0].text
        assert msg is not None
        assert len(msg) > 0

    async def test_handles_empty_admin_list(self, worker_ctx, mock_bot):
        """Job handles empty admin list."""
        with patch("core.infrastructure.config.settings") as mock_settings:
            mock_settings.rbac.owner_ids = []

            result = await daily_admin_statistics_job(worker_ctx.ctx_dict)

        assert result["sent"] == 0

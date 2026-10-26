"""
Contract tests for daily_admin_statistics_job (core's job, registered by this app's worker).

Tests the actual job logic with real database and captured messages.
"""

from unittest.mock import patch

import pytest

from app.worker.jobs import daily_admin_statistics_job
from core.infrastructure.config import settings


@pytest.mark.contract
class TestDailyAdminStatisticsJob:
    """Tests for the daily owner digest job."""

    async def test_sends_one_silent_rich_digest_per_owner(self, worker_ctx, mock_bot):
        """Job gathers the digest and sends it to every owner, as a rich table, without sound."""
        with patch.object(settings.rbac, "owner_ids", [111, 222]):
            result = await daily_admin_statistics_job(worker_ctx.ctx_dict)

        assert result["sent"] == 2
        assert [m.chat_id for m in mock_bot.rich_messages] == [111, 222]
        assert mock_bot.messages == []  # rich accepted -> no fallback sent
        digest = mock_bot.rich_messages[0]
        assert digest.kwargs["disable_notification"] is True
        assert "<table" in digest.text
        assert "<td>Revenue</td>" in digest.text
        assert "<footer>#digest" in digest.text

    async def test_handles_empty_admin_list(self, worker_ctx, mock_bot):
        """Job handles empty admin list."""
        with patch.object(settings.rbac, "owner_ids", []):
            result = await daily_admin_statistics_job(worker_ctx.ctx_dict)

        assert result["sent"] == 0
        assert mock_bot.rich_messages == []

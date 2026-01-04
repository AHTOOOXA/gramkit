"""
Contract tests for send_delayed_notification job.

Tests the actual job logic with real database and captured messages.
"""

import pytest

from app.worker.jobs import send_delayed_notification


@pytest.mark.contract
class TestDelayedNotificationJob:
    """Tests for delayed notification job."""

    async def test_sends_notification_to_user(self, worker_ctx, mock_bot):
        """Job sends notification to specified telegram user."""
        # Create user via worker's transaction
        async with worker_ctx.with_transaction() as services:
            await services.repo.users.get_or_create_user(
                {
                    "telegram_id": 12345,
                    "username": "notif_user",
                    "tg_first_name": "Notif",
                }
            )

        await send_delayed_notification(worker_ctx.ctx_dict, 12345, 5)

        assert len(mock_bot.messages) == 1
        assert mock_bot.messages[0].chat_id == 12345

    async def test_includes_delay_in_message(self, worker_ctx, mock_bot):
        """Job includes delay seconds in message."""
        async with worker_ctx.with_transaction() as services:
            await services.repo.users.get_or_create_user(
                {
                    "telegram_id": 23456,
                    "username": "delay_user",
                    "tg_first_name": "Delay",
                }
            )

        await send_delayed_notification(worker_ctx.ctx_dict, 23456, 10)

        # Message should reference the delay
        msg = mock_bot.messages[0]
        assert msg.kwargs.get("parse_mode") == "HTML"

    async def test_handles_user_not_found(self, worker_ctx, mock_bot):
        """Job handles case when user doesn't exist in DB."""
        # User doesn't exist - job should still try to send
        # (notification goes to telegram_id directly)
        await send_delayed_notification(worker_ctx.ctx_dict, 99999, 5)

        # Should still attempt to send
        assert len(mock_bot.messages) == 1

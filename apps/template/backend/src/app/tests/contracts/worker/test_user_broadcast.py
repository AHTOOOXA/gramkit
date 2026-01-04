"""
Contract tests for user_broadcast_job.

Tests the actual job logic with real database and captured messages.
"""

import pytest

from app.worker.jobs import user_broadcast_job


@pytest.mark.contract
class TestUserBroadcastJob:
    """Tests for user broadcast job."""

    async def test_sends_text_to_all_users(self, worker_ctx, mock_bot):
        """Job sends text message to all users with telegram_id."""
        # Create test users via worker's transaction (like production)
        async with worker_ctx.with_transaction() as services:
            await services.repo.users.get_or_create_user(
                {
                    "telegram_id": 111,
                    "username": "user1",
                    "tg_first_name": "User1",
                }
            )
            await services.repo.users.get_or_create_user(
                {
                    "telegram_id": 222,
                    "username": "user2",
                    "tg_first_name": "User2",
                }
            )

        broadcast_data = {
            "message_type": "text",
            "message_text": "Hello everyone!",
            "has_formatting": False,
        }

        result = await user_broadcast_job(worker_ctx.ctx_dict, broadcast_data, 999)

        assert result["sent"] == 2
        assert result["total"] == 2
        assert result["success_rate"] == 100.0
        assert len(mock_bot.messages) == 3  # 2 users + 1 completion notification

    async def test_sends_photo_to_all_users(self, worker_ctx, mock_bot):
        """Job sends photo with caption to all users."""
        async with worker_ctx.with_transaction() as services:
            await services.repo.users.get_or_create_user(
                {
                    "telegram_id": 333,
                    "username": "user3",
                    "tg_first_name": "User3",
                }
            )

        broadcast_data = {
            "message_type": "photo",
            "photo_file_id": "AgACAgIAAxkBAAI...",
            "caption": "Check this out!",
            "has_caption_formatting": False,
        }

        result = await user_broadcast_job(worker_ctx.ctx_dict, broadcast_data, 999)

        assert result["sent"] == 1
        assert len(mock_bot.photos) == 1
        assert mock_bot.photos[0].photo == "AgACAgIAAxkBAAI..."
        assert mock_bot.photos[0].text == "Check this out!"

    async def test_returns_success_rate(self, worker_ctx, mock_bot):
        """Job calculates and returns success rate."""
        async with worker_ctx.with_transaction() as services:
            await services.repo.users.get_or_create_user(
                {
                    "telegram_id": 444,
                    "username": "user4",
                    "tg_first_name": "User4",
                }
            )

        broadcast_data = {
            "message_type": "text",
            "message_text": "Test",
        }

        result = await user_broadcast_job(worker_ctx.ctx_dict, broadcast_data, 999)

        assert "success_rate" in result
        assert isinstance(result["success_rate"], float)

    async def test_sends_completion_notification(self, worker_ctx, mock_bot):
        """Job sends completion notification to requester."""
        async with worker_ctx.with_transaction() as services:
            await services.repo.users.get_or_create_user(
                {
                    "telegram_id": 555,
                    "username": "user5",
                    "tg_first_name": "User5",
                }
            )

        requester_id = 999

        broadcast_data = {
            "message_type": "text",
            "message_text": "Test",
        }

        await user_broadcast_job(worker_ctx.ctx_dict, broadcast_data, requester_id)

        # Last message should be completion notification to requester
        completion_msg = [m for m in mock_bot.messages if m.chat_id == requester_id]
        assert len(completion_msg) == 1
        assert "Broadcast complete" in completion_msg[0].text

    async def test_handles_html_formatting(self, worker_ctx, mock_bot):
        """Job handles HTML formatted messages."""
        async with worker_ctx.with_transaction() as services:
            await services.repo.users.get_or_create_user(
                {
                    "telegram_id": 666,
                    "username": "user6",
                    "tg_first_name": "User6",
                }
            )

        broadcast_data = {
            "message_type": "text",
            "message_html": "<b>Bold</b> message",
            "has_formatting": True,
        }

        await user_broadcast_job(worker_ctx.ctx_dict, broadcast_data, 999)

        user_msg = [m for m in mock_bot.messages if m.chat_id == 666][0]
        assert user_msg.text == "<b>Bold</b> message"
        assert user_msg.kwargs.get("parse_mode") == "HTML"

    async def test_handles_no_users(self, worker_ctx, mock_bot):
        """Job handles case with no users gracefully."""
        broadcast_data = {
            "message_type": "text",
            "message_text": "Test",
        }

        result = await user_broadcast_job(worker_ctx.ctx_dict, broadcast_data, 999)

        assert result["sent"] == 0
        assert result["total"] == 0

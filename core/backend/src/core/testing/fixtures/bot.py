"""Bot testing fixtures for Telegram bot handler tests.

Provides:
- Mock bot instances (AsyncMock)
- Message factory functions for creating test messages
- Update factory functions for simulating Telegram updates
- Callback query helpers for testing inline keyboard interactions
"""

import random
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
from aiogram.types import CallbackQuery, Chat, Message, Update, User


@pytest.fixture
def mock_bot():
    """
    Mock Telegram Bot API client for testing bot handlers.

    Provides AsyncMock for all bot methods:
    - send_message
    - send_photo
    - answer_callback_query
    - etc.

    Usage:
        async def test_start_command(mock_bot):
            await start_command(message, bot=mock_bot)
            mock_bot.send_message.assert_called_once()
    """
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=True)
    bot.send_photo = AsyncMock(return_value=True)
    bot.answer_callback_query = AsyncMock(return_value=True)
    bot.delete_message = AsyncMock(return_value=True)
    bot.edit_message_text = AsyncMock(return_value=True)
    bot.edit_message_reply_markup = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def message_factory(mock_bot):
    """
    Factory for creating Telegram Message objects for testing.

    Creates realistic Message objects with all required fields.
    Each message has unique IDs to ensure test isolation.

    Usage:
        def test_handler(message_factory):
            message = message_factory(text="/start r-test123")
            await handler(message)
    """

    def _create(
        text: str = "",
        user_id: int | None = None,
        username: str | None = None,
        first_name: str = "Test",
        last_name: str | None = "User",
        language_code: str = "en",
        chat_id: int | None = None,
        message_id: int | None = None,
    ) -> Message:
        """Create a test Message object.

        Args:
            text: Message text
            user_id: Telegram user ID (random if not provided)
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            language_code: User's language code
            chat_id: Chat ID (defaults to user_id if not provided)
            message_id: Message ID (random if not provided)

        Returns:
            Message object ready for testing
        """
        # Generate unique IDs for isolation
        if user_id is None:
            user_id = random.randint(100000000, 999999999)
        if chat_id is None:
            chat_id = user_id
        if message_id is None:
            message_id = random.randint(1, 999999)

        # Create User object
        user = User(
            id=user_id,
            is_bot=False,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
        )

        # Create Chat object
        chat = Chat(id=chat_id, type="private")

        # Create Message object
        message = Message(
            message_id=message_id,
            date=datetime.now(UTC),
            chat=chat,
            from_user=user,
            text=text,
        )

        # Attach bot to message (required for message.answer())
        # Use object.__setattr__ to bypass Pydantic's frozen model restriction
        object.__setattr__(message, "_bot", mock_bot)

        # Mock the answer() method to call mock_bot.send_message
        async def mock_answer(text: str, **kwargs):
            return await mock_bot.send_message(chat.id, text, **kwargs)

        object.__setattr__(message, "answer", mock_answer)

        return message

    return _create


@pytest.fixture
def update_factory(message_factory):
    """
    Factory for creating Telegram Update objects for testing.

    Creates Update objects containing messages or callback queries.

    Usage:
        def test_handler(update_factory):
            update = update_factory(text="/start")
            await dispatcher.process_update(update)
    """

    def _create(
        text: str = "",
        user_id: int | None = None,
        username: str | None = None,
        update_id: int | None = None,
        **message_kwargs: Any,
    ) -> Update:
        """Create a test Update object with a message.

        Args:
            text: Message text
            user_id: Telegram user ID
            username: Telegram username
            update_id: Update ID (random if not provided)
            **message_kwargs: Additional arguments passed to message_factory

        Returns:
            Update object ready for testing
        """
        if update_id is None:
            update_id = random.randint(1, 999999)

        message = message_factory(text=text, user_id=user_id, username=username, **message_kwargs)

        return Update(update_id=update_id, message=message)

    return _create


@pytest.fixture
def callback_query_factory(message_factory):
    """
    Factory for creating Telegram CallbackQuery objects for testing.

    Creates callback queries from inline keyboard button presses.

    Usage:
        def test_callback(callback_query_factory):
            callback = callback_query_factory(data="spread_type:THREE_CARD")
            await callback_handler(callback)
    """

    def _create(
        data: str,
        user_id: int | None = None,
        username: str | None = None,
        message_text: str = "",
        callback_id: str | None = None,
        **message_kwargs: Any,
    ) -> CallbackQuery:
        """Create a test CallbackQuery object.

        Args:
            data: Callback data (e.g., "spread_type:SINGLE_CARD")
            user_id: Telegram user ID
            username: Telegram username
            message_text: Original message text
            callback_id: Callback query ID
            **message_kwargs: Additional arguments passed to message_factory

        Returns:
            CallbackQuery object ready for testing
        """
        if callback_id is None:
            callback_id = str(random.randint(1, 999999999))

        message = message_factory(text=message_text, user_id=user_id, username=username, **message_kwargs)

        # Create User object
        user = message.from_user

        return CallbackQuery(
            id=callback_id,
            from_user=user,
            chat_instance=str(random.randint(1, 999999)),
            data=data,
            message=message,
        )

    return _create

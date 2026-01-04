"""Worker testing fixtures for ARQ background job tests.

Provides:
- Transaction management helpers
- Background job execution utilities
- Bot message/photo capture helpers
- Time freezing utilities
- Mock bot with message capture
- Worker context setup utilities
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from core.infrastructure.arq import WorkerContext
from core.infrastructure.database.setup import create_session_pool


class CapturedMessage:
    """Captured bot message for assertions.

    Provides convenient access to message properties for test assertions.

    Attributes:
        chat_id: Telegram chat ID
        text: Message text or caption
        photo: Photo file ID (for send_photo calls)
        kwargs: Additional arguments passed to send method
    """

    def __init__(self, chat_id: int, text: str = None, photo: str = None, **kwargs):
        self.chat_id = chat_id
        self.text = text
        self.photo = photo
        self.kwargs = kwargs


class MockBot:
    """Mock bot that captures sent messages and photos.

    Provides a realistic bot interface for testing worker jobs that send
    Telegram messages. Captures all calls for assertion.

    Attributes:
        messages: List of CapturedMessage objects from send_message calls
        photos: List of CapturedMessage objects from send_photo calls

    Usage:
        async def test_notification(worker_ctx, mock_bot):
            await notification_job(worker_ctx.ctx_dict)
            assert len(mock_bot.messages) == 1
            assert mock_bot.messages[0].chat_id == 123
            assert "Hello" in mock_bot.messages[0].text
    """

    def __init__(self):
        self.messages: list[CapturedMessage] = []
        self.photos: list[CapturedMessage] = []

    async def send_message(self, chat_id: int, text: str, **kwargs):
        """Capture send_message call and return mock result."""
        self.messages.append(CapturedMessage(chat_id, text=text, **kwargs))
        return MagicMock(message_id=len(self.messages))

    async def send_photo(self, chat_id: int, photo: str, caption: str = None, **kwargs):
        """Capture send_photo call and return mock result."""
        self.photos.append(CapturedMessage(chat_id, text=caption, photo=photo, **kwargs))
        return MagicMock(message_id=len(self.photos))


@pytest_asyncio.fixture
async def worker_mock_bot():
    """Mock bot that captures messages and photos for worker tests.

    Returns MockBot instance with empty message/photo lists.
    Use worker_mock_bot.messages and worker_mock_bot.photos for assertions.

    Note: Use this in worker tests instead of the regular mock_bot fixture
    from bot.py, which is for testing bot handlers.
    """
    return MockBot()


@pytest.fixture
def captured_bot_messages(mock_bot):
    """
    Capture bot.send_message calls for assertion.

    Returns list of all send_message calls with chat_id and text.

    Usage:
        async def test_notification(worker_context, captured_bot_messages):
            await morning_notification_job(ctx)
            assert len(captured_bot_messages) == 5
            assert captured_bot_messages[0]["chat_id"] == 123456789
            assert "Good morning" in captured_bot_messages[0]["text"]
    """
    messages = []

    async def capture_message(chat_id: int, text: str, **kwargs):
        messages.append({"chat_id": chat_id, "text": text, "kwargs": kwargs})
        return True

    mock_bot.send_message.side_effect = capture_message

    return messages


@pytest.fixture
def captured_bot_photos(mock_bot):
    """
    Capture bot.send_photo calls for assertion.

    Returns list of all send_photo calls with chat_id and photo details.

    Usage:
        async def test_photo_broadcast(worker_context, captured_bot_photos):
            await user_broadcast_job(ctx, broadcast_data)
            assert len(captured_bot_photos) == 10
            assert captured_bot_photos[0]["photo"] == "file_id_123"
    """
    photos = []

    async def capture_photo(chat_id: int, photo: str, **kwargs):
        photos.append({"chat_id": chat_id, "photo": photo, "kwargs": kwargs})
        return True

    mock_bot.send_photo.side_effect = capture_photo

    return photos


@pytest_asyncio.fixture
async def worker_job_runner(worker_ctx_dict):
    """
    Helper fixture for running worker jobs and capturing results.

    Provides a clean interface for executing jobs and verifying outcomes.

    Usage:
        async def test_job(worker_job_runner):
            result = await worker_job_runner.run(morning_notification_job)
            assert result["sent"] == 5
    """

    class JobRunner:
        def __init__(self, ctx_dict: dict):
            self.ctx_dict = ctx_dict
            self.bot = ctx_dict["bot"]
            self.redis = ctx_dict["redis"]
            self.arq = ctx_dict["arq"]

        async def run(self, job_func, *args, **kwargs):
            """Run a worker job and return the result."""
            return await job_func(self.ctx_dict, *args, **kwargs)

        def get_bot_calls(self, method: str = "send_message"):
            """Get all calls to a specific bot method."""
            bot_method = getattr(self.bot, method)
            return bot_method.call_args_list

        def assert_bot_called_with(self, method: str, **kwargs):
            """Assert bot method was called with specific arguments."""
            bot_method = getattr(self.bot, method)
            bot_method.assert_called_with(**kwargs)

        def get_enqueued_jobs(self):
            """Get all jobs enqueued via ARQ."""
            return self.arq.enqueue_job.call_args_list

    return JobRunner(worker_ctx_dict)


@pytest.fixture
def freeze_worker_time(monkeypatch):
    """
    Freeze time for worker jobs that depend on datetime.

    Usage:
        async def test_subscription_expiry(worker_context, freeze_worker_time):
            freeze_worker_time("2025-01-15 12:00:00")
            result = await expire_outdated_subscriptions_job(ctx)
    """
    from freezegun import freeze_time

    def _freeze(time_str: str):
        """Freeze time to specific datetime."""
        return freeze_time(time_str)

    return _freeze


def create_mock_session_pool(session_maker):
    """
    Create a mock session pool for worker context.

    Helper function to create session pool that manages transactions properly.
    Apps should use this in their worker_context fixtures.

    Args:
        session_maker: SQLAlchemy async_sessionmaker instance

    Returns:
        Mock session pool function that returns async context manager
    """

    def mock_session_pool():
        class MockSessionContext:
            async def __aenter__(self):
                session = session_maker()
                self.session = session
                return session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await self.session.rollback()
                await self.session.close()

        return MockSessionContext()

    return mock_session_pool


def create_mock_worker_dependencies():
    """
    Create mock external dependencies for worker context.

    Returns dict with mocked redis, arq, and producer for testing.

    Usage in app fixtures:
        mocks = create_mock_worker_dependencies()
        ctx_dict = {
            **mocks,
            "session_pool": session_pool,
            "bot": mock_bot,
            "repo_class": RequestsRepo,
            "service_factory": service_factory,
        }
    """
    # Create mock redis client
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=True)

    # Create mock arq pool
    mock_arq = AsyncMock()
    mock_arq.enqueue_job = AsyncMock(return_value=True)

    # Create mock producer
    mock_producer = AsyncMock()
    mock_producer.publish = AsyncMock(return_value=True)

    return {
        "redis": mock_redis,
        "arq": mock_arq,
        "producer": mock_producer,
    }


async def create_worker_context(
    db_engine: AsyncEngine,
    mock_bot: MockBot,
    repo_class: type,
    service_factory: Callable[..., Any],
    clean_tables: list[str] | None = None,
) -> WorkerContext:
    """
    Create WorkerContext for testing worker jobs with real database.

    This is a factory function that apps can use in their fixtures to create
    a properly configured WorkerContext with their app-specific dependencies.

    Args:
        db_engine: Database engine from db_engine fixture
        mock_bot: Mock bot instance for capturing messages
        repo_class: App's repository class (e.g., RequestsRepo)
        service_factory: Function that creates service instance from (repo, bot)
        clean_tables: List of table names to clean before each test (optional)

    Returns:
        WorkerContext configured with fresh session pool and app dependencies

    Usage in app's conftest.py:
        @pytest_asyncio.fixture
        async def worker_ctx(db_engine, mock_bot):
            return await create_worker_context(
                db_engine=db_engine,
                mock_bot=mock_bot,
                repo_class=RequestsRepo,
                service_factory=lambda repo, bot: RequestsService(repo=repo, bot=bot),
                clean_tables=["users", "requests"],
            )
    """
    # Create session pool from engine (like production)
    session_pool = create_session_pool(db_engine)

    # Clean up tables for test isolation
    if clean_tables:
        async with session_pool() as session:
            for table in clean_tables:
                await session.execute(text(f"DELETE FROM {table}"))
            await session.commit()

    # Create worker context dict with all dependencies
    ctx_dict = {
        "session_pool": session_pool,
        "bot": mock_bot,
        "repo_class": repo_class,
        "service_factory": service_factory,
        "redis": None,
        "arq": MagicMock(),
        "producer": None,
    }

    return WorkerContext(ctx_dict)

"""Worker test fixtures.

Provides WorkerContext with real database and captured bot messages.
Uses core's worker fixtures for consistency across apps.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService
from core.testing.fixtures.worker import MockBot, create_worker_context


@pytest_asyncio.fixture
async def mock_bot():
    """Mock bot that captures messages for worker tests.

    Returns MockBot instance from core's worker fixtures.
    """
    return MockBot()


@pytest_asyncio.fixture
async def worker_ctx(db_engine: AsyncEngine, mock_bot: MockBot):
    """
    WorkerContext for testing worker jobs with real database.

    Uses db_engine (not db_session) to create fresh sessions for each
    with_transaction() call, matching production behavior.

    Provides:
    - Fresh database sessions via session_pool
    - Mock bot that captures messages (via core's MockBot)
    - Real RequestsService for business logic
    """

    def service_factory(repo, bot):
        return RequestsService(repo=repo, bot=bot)

    return await create_worker_context(
        db_engine=db_engine,
        mock_bot=mock_bot,
        repo_class=RequestsRepo,
        service_factory=service_factory,
        clean_tables=["users"],
    )

"""Pytest configuration for template backend tests."""

import random
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import Balance model FIRST before any core imports
# This ensures it's registered in SQLAlchemy before core's conftest runs
from app.infrastructure.database.models.balance import Balance  # noqa: F401

# Patch RedisClient.__init__ BEFORE any app imports to prevent connection attempts
with patch("core.infrastructure.redis.RedisClient.__init__", lambda self, config: None):
    import app.webhook.auth as auth_module
    from app.infrastructure.database.repo.requests import RequestsRepo

    # App-specific imports
    from app.webhook.app import app
    from app.webhook.dependencies.arq import get_arq_pool
    from app.webhook.dependencies.bot import get_bot
    from app.webhook.dependencies.database import get_repo
    from app.webhook.dependencies.rabbit import get_rabbit_producer
    from app.webhook.dependencies.redis import get_redis_client
    from app.webhook.routers.demo import _counters
    from core.infrastructure.config import settings
    from core.testing.fixtures.auth import generate_telegram_init_data

    # Core fixtures (generic, don't depend on app)
    from core.testing.fixtures.database import db_engine, db_session, postgres_container
    from core.testing.fixtures.mocks import (
        mock_arq_enqueue,
        mock_posthog,
        mock_yookassa,
        mock_yookassa_webhook,
    )
    from core.testing.fixtures.redis import InMemoryRedis, mock_redis


# Re-export core fixtures for pytest discovery
__all__ = [
    "postgres_container",
    "db_engine",
    "db_session",
    "mock_redis",
    "InMemoryRedis",
    "generate_telegram_init_data",
    "mock_yookassa",
    "mock_yookassa_webhook",
    "mock_arq_enqueue",
    "mock_posthog",
    # App-specific
    "test_app",
    "client",
    "authenticated_client",
    "test_user",
]


@pytest_asyncio.fixture
async def test_app(db_session: AsyncSession, mock_redis: InMemoryRedis):
    """Template app with test dependencies injected."""
    original_overrides = app.dependency_overrides.copy()
    original_session_redis = auth_module.session_redis

    # Override dependencies
    async def override_get_repo():
        yield RequestsRepo(db_session)

    async def override_get_redis():
        yield mock_redis

    async def override_get_bot():
        yield MagicMock(id=123456789, username="test_bot")

    async def override_get_arq():
        mock_arq = MagicMock()
        mock_arq.enqueue_job = AsyncMock(return_value=MagicMock())
        yield mock_arq

    async def override_get_rabbit():
        yield MagicMock()

    app.dependency_overrides[get_repo] = override_get_repo
    app.dependency_overrides[get_redis_client] = override_get_redis
    app.dependency_overrides[get_bot] = override_get_bot
    app.dependency_overrides[get_arq_pool] = override_get_arq
    app.dependency_overrides[get_rabbit_producer] = override_get_rabbit
    auth_module.session_redis = mock_redis

    yield app

    # Cleanup
    app.dependency_overrides = original_overrides
    auth_module.session_redis = original_session_redis


@pytest_asyncio.fixture
async def client(test_app) -> AsyncGenerator[AsyncClient]:
    """Unauthenticated HTTP client for testing public endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as c:
        yield c


@pytest_asyncio.fixture
async def authenticated_client(test_app) -> AsyncGenerator[AsyncClient]:
    """HTTP client with valid Telegram auth for testing protected endpoints."""
    telegram_user_id = random.randint(100000, 9999999)
    username = f"test_{uuid4().hex[:8]}"

    init_data = generate_telegram_init_data(
        user_id=telegram_user_id,
        username=username,
        bot_token=settings.bot.token,
    )

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers={"initData": init_data},
    ) as c:
        yield c


@pytest_asyncio.fixture
async def test_user(authenticated_client: AsyncClient):
    """Test user created via authenticated API flow."""
    from core.schemas.users import UserSchema

    response = await authenticated_client.get("/users/me")
    assert response.status_code == 200
    return UserSchema(**response.json())


@pytest_asyncio.fixture(autouse=True)
async def reset_demo_counters():
    """Reset all demo counters before each test to ensure isolation."""
    _counters.clear()
    yield
    _counters.clear()


# =============================================================================
# Architecture Contract Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
def products_module():
    """App's products module for BaseProductProtocolTests."""
    from app.domain import products

    return products


@pytest_asyncio.fixture
async def services(db_session: AsyncSession):
    """App's services instance for BaseCompositionTests."""
    from app.services.requests import RequestsService

    repo = RequestsRepo(db_session)
    return RequestsService(repo=repo)

"""Core test fixtures - available to app tests via import.

Generic fixtures that don't depend on any specific app.
App-specific fixtures (test_app, client, authenticated_client) belong in each app's conftest.py.
"""

# Database
# API client utilities
from core.testing.fixtures.api_client import MockSessionManager

# Auth
from core.testing.fixtures.auth import generate_telegram_init_data

# Bot
from core.testing.fixtures.bot import (
    callback_query_factory,
    message_factory,
    mock_bot,
    update_factory,
)
from core.testing.fixtures.database import db_engine, db_session, postgres_container

# Mocks
from core.testing.fixtures.mocks import (
    mock_arq_enqueue,
    mock_posthog,
    mock_yookassa,
    mock_yookassa_webhook,
)

# Redis
from core.testing.fixtures.redis import InMemoryRedis, mock_redis

# Worker
from core.testing.fixtures.worker import (
    CapturedMessage,
    MockBot,
    captured_bot_messages,
    captured_bot_photos,
    create_mock_session_pool,
    create_mock_worker_dependencies,
    create_worker_context,
    freeze_worker_time,
    worker_job_runner,
    worker_mock_bot,
)

__all__ = [
    # Database
    "postgres_container",
    "db_engine",
    "db_session",
    # Redis
    "mock_redis",
    "InMemoryRedis",
    # Auth
    "generate_telegram_init_data",
    # Mocks
    "mock_yookassa",
    "mock_yookassa_webhook",
    "mock_arq_enqueue",
    "mock_posthog",
    # API client
    "MockSessionManager",
    # Bot
    "mock_bot",
    "message_factory",
    "update_factory",
    "callback_query_factory",
    # Worker
    "MockBot",
    "CapturedMessage",
    "worker_mock_bot",
    "captured_bot_messages",
    "captured_bot_photos",
    "worker_job_runner",
    "freeze_worker_time",
    "create_mock_session_pool",
    "create_mock_worker_dependencies",
    "create_worker_context",
]

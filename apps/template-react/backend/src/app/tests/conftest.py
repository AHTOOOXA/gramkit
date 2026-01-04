"""Root-level pytest configuration for template-react backend tests.

This file provides minimal fixtures for testing endpoints that don't require
full database or authentication setup.
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Import Balance model FIRST before any core imports
# This ensures it's registered in SQLAlchemy before core's conftest runs
from app.infrastructure.database.models.balance import Balance  # noqa: F401
from app.webhook.routers.demo import _counters


@pytest_asyncio.fixture
async def client():
    """Create AsyncClient for testing FastAPI demo endpoints.

    This is a lightweight client that doesn't require database setup.
    Suitable for testing stateless or in-memory endpoints.
    """
    from app.webhook.app import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def reset_demo_counters():
    """Reset all demo counters before each test to ensure isolation."""
    _counters.clear()
    yield
    _counters.clear()

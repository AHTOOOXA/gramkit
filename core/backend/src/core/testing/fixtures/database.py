"""Database fixtures for testing with PostgreSQL testcontainers.

Provides production-parity testing environment using real PostgreSQL in Docker containers.

Fixtures:
- postgres_container: Session-scoped PostgreSQL container (shared across all tests)
- db_engine: Function-scoped database engine connected to testcontainer
- db_session: Function-scoped database session with automatic transaction rollback
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from core.infrastructure.database.models.base import Base


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for the entire test session.

    Container is shared across all tests for performance.
    Started once at session start, stopped at session end.
    """
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest_asyncio.fixture
async def db_engine(postgres_container: PostgresContainer) -> AsyncGenerator[AsyncEngine]:
    """Create async database engine connected to testcontainer.

    Function-scoped: New engine for each test (ensures isolation).
    Creates all database tables from SQLAlchemy models.

    Note: We use function scope (not session) to ensure clean state.
    While session-scoped would be faster, it creates event loop compatibility
    issues with pytest-asyncio. Current performance (~400ms per test) is excellent.
    """
    # Get asyncpg connection URL from testcontainer
    connection_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")

    # Create async engine
    engine = create_async_engine(
        connection_url,
        echo=False,  # Set to True for SQL query debugging
        future=True,
        pool_pre_ping=True,
    )

    # Create all tables (happens EVERY test - slow!)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: dispose engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Create a database session with automatic transaction rollback.

    Function-scoped: New session for each test (isolation).
    Transaction automatically rolls back after test (cleanup).

    This provides perfect test isolation - each test gets a clean database state
    without needing to recreate tables (transaction rollback is instant).

    Usage in tests:
        async def test_example(db_session: AsyncSession):
            # Use db_session for database operations
            # All changes rolled back after test
    """
    # Create session factory
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create session and start transaction
    session = async_session_maker()
    await session.begin()

    try:
        yield session
    finally:
        # Rollback transaction and close session
        await session.rollback()
        await session.close()

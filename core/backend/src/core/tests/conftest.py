"""Pytest configuration for core backend tests.

Markers:
- @pytest.mark.contract: Public interface tests (80%)
- @pytest.mark.business_logic: Algorithm, race condition tests (15%)
- @pytest.mark.regression: Bug fix tests (5%)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.infrastructure.database.models.base import Base, CreatedAtMixin, TableNameMixin, UpdatedAtMixin
from core.infrastructure.database.repo.base import BaseRepo

if TYPE_CHECKING:
    from core.infrastructure.database.models.users import User

# Auth fixtures
from core.testing.fixtures.auth import generate_telegram_init_data

# Database fixtures
from core.testing.fixtures.database import db_engine, db_session, postgres_container

# Re-export for pytest discovery
__all__ = [
    "postgres_container",
    "db_engine",
    "db_session",
    "generate_telegram_init_data",
    "balance_repo",
]


# =============================================================================
# Stub models for core tests
# =============================================================================
# Core's User model has relationships to Balance (app-specific).
# We define a minimal stub here so core tests can run standalone.
# When running with apps, apps provide their own Balance model.

# Only define Balance stub if not already registered by an app
if "Balance" not in Base.registry._class_registry:

    class Balance(Base, CreatedAtMixin, UpdatedAtMixin, TableNameMixin):
        """Stub Balance model for core tests.

        Apps define their own Balance with additional fields.
        This minimal version satisfies User.balance relationship.
        """

        __table_args__ = {"extend_existing": True}

        user_id: Mapped[UUID] = mapped_column(
            PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, autoincrement=False
        )

        user: Mapped[User] = relationship("User", back_populates="balance", uselist=False)


# =============================================================================
# Test models for BaseRepo integration tests
# =============================================================================


class BalanceTestModel(Base, TableNameMixin):
    """Test model for BaseRepo integration tests (separate from Balance stub)."""

    __tablename__ = "test_balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(unique=True)
    credits: Mapped[int] = mapped_column(default=100)
    version: Mapped[int] = mapped_column(default=0)


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "contract: Public interface tests (80%)")
    config.addinivalue_line("markers", "business_logic: Complex logic, race conditions (15%)")
    config.addinivalue_line("markers", "regression: Bug fix tests (5%)")
    config.addinivalue_line("markers", "issue(id): Link test to GitHub issue number")


@pytest.fixture
def anyio_backend():
    """Configure pytest-asyncio backend."""
    return "asyncio"


@pytest_asyncio.fixture
async def balance_repo(db_session: AsyncSession) -> BaseRepo:
    """BaseRepo configured with BalanceTestModel for integration tests."""
    repo = BaseRepo(db_session)
    repo.model_type = BalanceTestModel
    return repo

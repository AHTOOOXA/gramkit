"""Balance repository for user balance/credits management."""

from __future__ import annotations

from app.infrastructure.database.models.balance import Balance
from core.infrastructure.database.repo.base import BaseRepo


class BalanceRepo(BaseRepo[Balance]):
    """Repository for Balance model operations."""

    model = Balance

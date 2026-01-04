"""
═══════════════════════════════════════════════════════════════════════════════
Business Logic Tests
═══════════════════════════════════════════════════════════════════════════════

Tests for complex logic that benefits from direct service/repo testing
rather than going through HTTP endpoints.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHEN TO USE @pytest.mark.business_logic (15% of tests):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. RACE CONDITIONS / CONCURRENCY
   - Concurrent balance withdrawals (two requests, one credit)
   - Inventory decrements (prevent overselling)

2. COMPLEX CALCULATIONS
   - Pricing with discounts, tiers, promotions
   - Scoring algorithms

3. STATE MACHINES
   - Order status transitions (PENDING → PAID → SHIPPED)
   - Subscription lifecycle (ACTIVE → CANCELLED → EXPIRED)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repo.requests import RequestsRepo


@pytest.mark.business_logic
async def test_get_or_create_user_is_idempotent(db_session: AsyncSession):
    """
    Calling get_or_create_user twice with same telegram_id returns same user.

    This proves the idempotency pattern works - duplicate requests
    don't create duplicate users.
    """
    repo = RequestsRepo(db_session)
    telegram_id = 999888777

    # First call - creates user
    user1 = await repo.users.get_or_create_user(
        {
            "telegram_id": telegram_id,
            "username": "idempotent_test",
            "tg_first_name": "Test",
        }
    )

    # Second call - returns same user (not a duplicate)
    user2 = await repo.users.get_or_create_user(
        {
            "telegram_id": telegram_id,
            "username": "idempotent_test",
            "tg_first_name": "Test",
        }
    )

    assert user1.id == user2.id
    assert user1.telegram_id == telegram_id

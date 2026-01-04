"""Generic Balance Service for managing user credits/limits.

Extend this service with app-specific balance logic as needed.
"""

from uuid import UUID

from app.services.base import BaseService


class BalanceService(BaseService):
    """Service for managing user balance/credits.

    This is a minimal implementation. Extend with app-specific methods:
    - Credit deduction/addition
    - Feature limits
    - Usage tracking
    - etc.
    """

    async def get_or_create_balance(self, user_id: UUID):
        """Get user balance or create with defaults if doesn't exist."""
        balance = await self.repo.balance.get_by_id(user_id)
        if balance:
            return balance

        # Create default balance for new user
        return await self.repo.balance.create({"user_id": user_id})

    async def get_balance(self, user_id: UUID):
        """Get user balance."""
        return await self.repo.balance.get_by_id(user_id)

    async def update_balance(self, user_id: UUID, balance_data: dict):
        """Update user balance."""
        return await self.repo.balance.update(user_id, balance_data)

    # Example: Add app-specific methods below
    #
    # async def can_perform_action(self, user_id: int, action_type: str) -> bool:
    #     """Check if user has credits for an action."""
    #     balance = await self.get_or_create_balance(user_id)
    #     has_subscription = await self.services.subscriptions.has_active_subscription(user_id)
    #
    #     if has_subscription:
    #         return True  # Unlimited for subscribers
    #
    #     # Check balance for specific action
    #     return balance.credits > 0
    #
    # async def deduct_credit(self, user_id: int) -> None:
    #     """Deduct one credit from user balance with pessimistic locking."""
    #     balance = await self.repo.balance.get_by_id_with_lock(user_id)
    #     if balance.credits > 0:
    #         await self.update_balance(user_id, {"credits": balance.credits - 1})

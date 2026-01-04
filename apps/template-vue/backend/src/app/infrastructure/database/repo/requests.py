"""Template application repository aggregator using composition pattern."""

from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repo.balance import BalanceRepo
from core.infrastructure.database.repo.groups import GroupMemberRepo, GroupRepo
from core.infrastructure.database.repo.invites import InviteRepo
from core.infrastructure.database.repo.payments import PaymentEventRepo, PaymentRepo
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.infrastructure.database.repo.subscriptions import SubscriptionRepo
from core.infrastructure.database.repo.users import UserRepo


class RequestsRepo:
    """
    Template application repository aggregator.

    Uses composition pattern to delegate all repositories to CoreRequestsRepo.
    Template-specific repositories can be added here as needed.

    Uses lazy loading pattern (@cached_property) to instantiate repositories only when accessed.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._core = CoreRequestsRepo(session)

    # Core repos (delegated to self._core)

    @cached_property
    def users(self) -> UserRepo:
        """User repository (from core)."""
        return self._core.users

    @cached_property
    def balance(self) -> BalanceRepo:
        """Balance repository (template-specific)."""
        return BalanceRepo(self.session)

    @cached_property
    def groups(self) -> GroupRepo:
        """Group repository (from core)."""
        return self._core.groups

    @cached_property
    def members(self) -> GroupMemberRepo:
        """Group member repository (from core)."""
        return self._core.members

    @cached_property
    def invites(self) -> InviteRepo:
        """Invite repository (from core)."""
        return self._core.invites

    @cached_property
    def payments(self) -> PaymentRepo:
        """Payment repository (from core)."""
        return self._core.payments

    @cached_property
    def payment_events(self) -> PaymentEventRepo:
        """Payment event repository (from core)."""
        return self._core.payment_events

    @cached_property
    def subscriptions(self) -> SubscriptionRepo:
        """Subscription repository (from core)."""
        return self._core.subscriptions

"""Core repository aggregator using lazy loading pattern."""

from functools import cached_property
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.repo.admin_users import AdminUsersRepo
from core.infrastructure.database.repo.analytics import AnalyticsRepo
from core.infrastructure.database.repo.audit_log import AuditLogRepo
from core.infrastructure.database.repo.groups import GroupMemberRepo, GroupRepo
from core.infrastructure.database.repo.invites import InviteRepo
from core.infrastructure.database.repo.marketing_links import MarketingLinkRepo
from core.infrastructure.database.repo.notifications import NotificationDeliveryRepo
from core.infrastructure.database.repo.payments import PaymentEventRepo, PaymentRepo
from core.infrastructure.database.repo.promotional_broadcasts import PromotionalBroadcastRepo
from core.infrastructure.database.repo.subscriptions import SubscriptionRepo
from core.infrastructure.database.repo.users import UserRepo


class CoreRequestsRepo:
    """Core repository aggregator using lazy loading pattern.

    Apps should use composition pattern to extend core repositories:

    Example:
        ```python
        from core.infrastructure.database.repo.requests import CoreRequestsRepo

        class AppRequestsRepo:
            def __init__(self, session):
                self.session = session
                self._core = CoreRequestsRepo(session)

            @cached_property
            def users(self):
                '''User repository (from core)'''
                return self._core.users

            @cached_property
            def my_app_entities(self):
                '''App-specific repository'''
                return MyAppEntityRepo(self.session)
        ```

    This pattern provides:
    - Clear separation between core and app repositories
    - Explicit delegation via self._core
    - Easy extension with app-specific repositories
    - No inheritance coupling

    Each property uses @cached_property to instantiate repositories only when first accessed.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @cached_property
    def users(self) -> UserRepo:
        """User repository for managing user accounts and profiles."""
        return UserRepo(self.session)

    @cached_property
    def groups(self) -> GroupRepo:
        """Group repository for managing user groups."""
        return GroupRepo(self.session)

    @cached_property
    def members(self) -> GroupMemberRepo:
        """Group member repository for managing group memberships."""
        return GroupMemberRepo(self.session)

    @cached_property
    def invites(self) -> InviteRepo:
        """Invite repository for managing group invites."""
        return InviteRepo(self.session)

    @cached_property
    def payments(self) -> PaymentRepo:
        """Payment repository for managing payment transactions."""
        return PaymentRepo(self.session)

    @cached_property
    def payment_events(self) -> PaymentEventRepo:
        """Payment event repository for payment event tracking."""
        return PaymentEventRepo(self.session)

    @cached_property
    def subscriptions(self) -> SubscriptionRepo:
        """Subscription repository for managing user subscriptions."""
        return SubscriptionRepo(self.session)

    @cached_property
    def notification_deliveries(self) -> NotificationDeliveryRepo:
        """Log of scheduled notification sends (one row per attempt)."""
        return NotificationDeliveryRepo(self.session)

    @cached_property
    def audit_log(self) -> AuditLogRepo:
        """Admin audit-log repository (mutating admin/owner actions)."""
        return AuditLogRepo(self.session)

    @cached_property
    def admin_users(self) -> AdminUsersRepo:
        """Admin users repository (read-only search + per-user sub-lists)."""
        return AdminUsersRepo(self.session)

    @cached_property
    def analytics(self) -> AnalyticsRepo:
        """Admin money analytics (read-only aggregations: revenue, subscriptions, MRR inputs)."""
        return AnalyticsRepo(self.session)

    @cached_property
    def promotional_broadcasts(self) -> PromotionalBroadcastRepo:
        """Promotional broadcasts (admin composer + scheduled morning/evening sends)."""
        return PromotionalBroadcastRepo(self.session)

    @cached_property
    def marketing_links(self) -> MarketingLinkRepo:
        """Registered acquisition codes (admin marketing links) and per-code results."""
        return MarketingLinkRepo(self.session)

    def get_all_repos(self) -> dict[str, Any]:
        """Get all core repos as dict (useful for debugging/introspection).

        Returns:
            Dictionary mapping repo names to repo instances.
        """
        return {
            "users": self.users,
            "groups": self.groups,
            "members": self.members,
            "invites": self.invites,
            "payments": self.payments,
            "payment_events": self.payment_events,
            "subscriptions": self.subscriptions,
            "notification_deliveries": self.notification_deliveries,
            "audit_log": self.audit_log,
            "admin_users": self.admin_users,
            "analytics": self.analytics,
            "promotional_broadcasts": self.promotional_broadcasts,
            "marketing_links": self.marketing_links,
        }

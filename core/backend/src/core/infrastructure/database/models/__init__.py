"""Core database models for TMA platform."""

from core.infrastructure.database.models.base import Base, CreatedAtMixin, TableNameMixin, UpdatedAtMixin
from core.infrastructure.database.models.enums import (
    AuthMethod,
    NotificationTimeSlot,
    PaymentEventType,
    PaymentProvider,
    PaymentStatus,
    SubscriptionStatus,
    UserType,
)
from core.infrastructure.database.models.friendships import Friendship
from core.infrastructure.database.models.groups import Group, GroupMember
from core.infrastructure.database.models.invites import GroupInvite
from core.infrastructure.database.models.payments import Payment, PaymentEvent
from core.infrastructure.database.models.subscriptions import Subscription
from core.infrastructure.database.models.users import User
from core.infrastructure.database.models.webhooks import FailedWebhook

__all__ = [
    "Base",
    "CreatedAtMixin",
    "TableNameMixin",
    "UpdatedAtMixin",
    "User",
    "UserType",
    "AuthMethod",
    "Payment",
    "PaymentEvent",
    "PaymentProvider",
    "PaymentStatus",
    "PaymentEventType",
    "Subscription",
    "SubscriptionStatus",
    "GroupInvite",
    "Friendship",
    "Group",
    "GroupMember",
    "NotificationTimeSlot",
    "FailedWebhook",
]

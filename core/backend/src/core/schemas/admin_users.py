"""Response + request schemas for the admin Users section.

The list item is a lean projection of the user row; the detail bundles the user
profile, the current subscription, and a couple of cheap rollup counts. Sub-lists
(payments / subscriptions) ride the shared ``AdminListResponse[T]`` envelope.
Request bodies are tiny and explicit.

App-specific per-user data is served by the app's own admin endpoints with their
own typed schemas — never as an untyped field on these.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminUserListItem(BaseModel):
    """One row in the admin users table."""

    id: UUID
    user_type: str
    role: str
    username: str | None = None
    display_name: str | None = None
    telegram_id: int | None = None
    tg_username: str | None = None
    email: str | None = None
    current_streak: int = 0
    best_streak: int = 0
    total_active_days: int = 0
    last_activity_date: date | None = None
    is_onboarded: bool | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserSubscription(BaseModel):
    """A subscription row for the detail page / sub-table."""

    id: UUID
    product_id: str
    provider_id: str
    status: str
    currency: str
    start_date: datetime
    end_date: datetime
    canceled_at: datetime | None = None
    cancellation_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserDetail(BaseModel):
    """Full admin view of a user: profile + current sub + rollups."""

    # Profile
    id: UUID
    user_type: str
    role: str
    username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    language_code: str | None = None
    timezone: str | None = None
    birth_date: date | None = None
    male: bool | None = None

    # Telegram identity
    telegram_id: int | None = None
    tg_username: str | None = None
    tg_first_name: str | None = None
    tg_is_premium: bool | None = None

    # Email
    email: str | None = None
    email_verified: bool = False

    # Engagement
    current_streak: int = 0
    best_streak: int = 0
    total_active_days: int = 0
    last_activity_date: date | None = None
    is_onboarded: bool | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Aggregates
    active_subscription: AdminUserSubscription | None = None
    has_active_subscription: bool = False
    payments_count: int = 0

    # RBAC caveat surface: telegram_id forced to OWNER by config (role changes won't stick).
    is_config_owner: bool = False


class AdminPaymentListItem(BaseModel):
    """One payment row in the per-user payments sub-table."""

    id: UUID
    product_id: str
    provider_id: str
    amount: float
    currency: str
    status: str
    is_recurring: bool = False
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Request bodies ────────────────────────────────────────────────────────────


GiftDuration = Literal["week", "month", "year", "max"]


class GiftSubscriptionRequest(BaseModel):
    """Gift a free subscription for a named duration."""

    duration: GiftDuration


class ChangeRoleRequest(BaseModel):
    """Change a user's RBAC role."""

    new_role: Literal["user", "admin", "owner"]

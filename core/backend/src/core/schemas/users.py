import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, RootModel, field_validator

from core.infrastructure.database.models.enums import UserRole, UserType


class UserSchema(BaseModel):
    """User schema for API responses - NEVER expose password_hash"""

    # Core Identity
    id: UUID | None = None
    user_type: UserType = UserType.REGISTERED
    role: str = UserRole.USER
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # App Profile
    display_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    language_code: str | None = None
    timezone: str | None = None
    birth_date: date | None = None
    male: bool | None = None

    # Auth: Telegram
    telegram_id: int | None = None
    tg_first_name: str | None = None
    tg_last_name: str | None = None
    tg_username: str | None = None
    tg_language_code: str | None = None
    tg_is_premium: bool | None = None
    tg_photo_url: str | None = None
    tg_is_bot: bool | None = None
    tg_added_to_attachment_menu: bool | None = None
    tg_allows_write_to_pm: bool | None = None

    # Auth: Email
    email: str | None = None
    email_verified: bool = False
    email_verified_at: datetime | None = None
    last_login_at: datetime | None = None

    # Engagement
    current_streak: int = 0
    best_streak: int = 0
    total_active_days: int = 0
    last_activity_date: date | None = None

    # Onboarding & Referral
    is_onboarded: bool | None = None
    is_terms_accepted: bool | None = None
    referral_code: str | None = None

    # Notifications: set when the bot got TelegramForbiddenError, cleared on /start or app open
    bot_blocked_at: datetime | None = None

    # Feature-reveal tracking (read path; written via PATCH /users/me/seen-features)
    seen_features: dict = {}

    model_config = ConfigDict(from_attributes=True)

    @property
    def is_new(self) -> bool:
        """User is new if they haven't had their first app session yet.

        Uses state-based check (last_activity_date) instead of time-based check.
        This is reliable regardless of timing, network retries, or race conditions.

        last_activity_date is set by update_user_streak() in every process_start call.
        Works for all users (with or without referal codes).

        Returns:
            True if user has never opened the app (last_activity_date is None)
            False otherwise
        """
        return self.last_activity_date is None

    @property
    def is_guest(self) -> bool:
        """Check if user is a guest user"""
        return self.user_type == UserType.GUEST

    @property
    def is_registered_user(self) -> bool:
        """Check if user is a registered user"""
        return self.user_type == UserType.REGISTERED

    @property
    def is_admin(self) -> bool:
        """Check if user has admin or owner role"""
        return self.role in (UserRole.ADMIN, UserRole.OWNER)

    @property
    def is_owner(self) -> bool:
        """Check if user has owner role"""
        return self.role == UserRole.OWNER


class GroupSchema(BaseModel):
    id: int
    title: str | None = None
    photo_url: str | None = None
    users: list[UserSchema] = []

    model_config = ConfigDict(from_attributes=True)


class UpdateUserRequest(BaseModel):
    """Request schema for updating user profile fields"""

    # App Profile (user-controlled)
    display_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    language_code: str | None = None
    timezone: str | None = None
    birth_date: date | None = None
    male: bool | None = None

    # Onboarding
    is_onboarded: bool | None = None
    is_terms_accepted: bool | None = None

    model_config = ConfigDict(from_attributes=True)


# Feature-seen tracking ------------------------------------------------------

_FEATURE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$")
_MAX_FEATURE_KEYS = 20

# A feature value is either a scalar (one-shot bool, version int) or a shallow
# record (capped-nudge / acknowledged state). Depth is capped at one level by
# construction — values may not nest further.
FeatureScalar = bool | int | float | str
FeatureValue = FeatureScalar | dict[str, FeatureScalar]


class SeenFeaturesPatch(RootModel[dict[str, FeatureValue]]):
    """Body for PATCH /users/me/seen-features.

    A shallow `feature_key -> value` map, merged into `users.seen_features` via
    JSONB `||` (top-level keys only). Hardened because it is user-writable:
    keys must be dotted lowercase identifiers, the map is bounded, and values
    are at most one level deep.
    """

    @field_validator("root")
    @classmethod
    def _validate(cls, value: dict) -> dict:
        if not value:
            raise ValueError("patch must contain at least one feature key")
        if len(value) > _MAX_FEATURE_KEYS:
            raise ValueError(f"too many feature keys (max {_MAX_FEATURE_KEYS})")
        for key in value:
            if not _FEATURE_KEY_RE.match(key):
                raise ValueError(f"invalid feature key: {key!r}")
        return value

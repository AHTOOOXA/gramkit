from datetime import date, datetime
from uuid import UUID, uuid7

from sqlalchemy import BIGINT, Boolean, Date, Enum, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, TableNameMixin, UpdatedAtMixin
from .enums import UserRole, UserType


class User(Base, CreatedAtMixin, UpdatedAtMixin, TableNameMixin):
    # Core Identity
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid7)
    user_type: Mapped[UserType] = mapped_column(Enum(UserType, native_enum=False), default=UserType.REGISTERED)
    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.USER,
        nullable=False,
        index=True,  # For filtering by role
    )

    # App Profile (user-controlled)
    display_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(128), unique=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    language_code: Mapped[str | None] = mapped_column(String(10))
    timezone: Mapped[str | None] = mapped_column(String(50), default="Europe/Moscow")
    birth_date: Mapped[date | None] = mapped_column(Date)
    male: Mapped[bool | None] = mapped_column(Boolean)

    # Auth: Telegram (read-only from TG API)
    telegram_id: Mapped[int | None] = mapped_column(BIGINT, unique=True, nullable=True)
    tg_first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tg_last_name: Mapped[str | None] = mapped_column(String(64))
    tg_username: Mapped[str | None] = mapped_column(String(32))
    tg_language_code: Mapped[str | None] = mapped_column(String(8))
    tg_is_premium: Mapped[bool | None] = mapped_column(Boolean)
    tg_photo_url: Mapped[str | None] = mapped_column(String(500))
    tg_is_bot: Mapped[bool | None] = mapped_column(Boolean)
    tg_added_to_attachment_menu: Mapped[bool | None] = mapped_column(Boolean)
    tg_allows_write_to_pm: Mapped[bool | None] = mapped_column(Boolean)

    # Auth: Email
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    email_verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Engagement
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_active_days: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Onboarding & Referral
    is_onboarded: Mapped[bool | None] = mapped_column(Boolean, default=False)
    is_terms_accepted: Mapped[bool | None] = mapped_column(Boolean, default=False)
    referral_code: Mapped[str | None] = mapped_column(String(40), unique=True)

    # Relationships
    friendships: Mapped[list[Friendship]] = relationship(
        "Friendship",
        primaryjoin="or_(User.id==Friendship.user_id1, User.id==Friendship.user_id2)",
        viewonly=True,
    )

    balance: Mapped[Balance] = relationship("Balance", back_populates="user", uselist=False)
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="user")
    subscriptions: Mapped[list[Subscription]] = relationship("Subscription", back_populates="user")

    def __repr__(self):
        return f"<User {self.id} {self.username} ({self.user_type.value})>"

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

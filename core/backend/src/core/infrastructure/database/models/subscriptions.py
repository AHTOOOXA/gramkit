from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, TIMESTAMP, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, TableNameMixin, UpdatedAtMixin
from .enums import PaymentProvider, SubscriptionStatus


class Subscription(Base, CreatedAtMixin, UpdatedAtMixin, TableNameMixin):
    id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_id: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider, native_enum=False), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus, native_enum=False), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    start_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(String(50))
    cancellation_feedback: Mapped[str | None] = mapped_column(Text)
    recurring_details: Mapped[dict] = mapped_column(JSON, default=dict)

    # Dunning state: how many consecutive renewal attempts have failed, and when the last
    # attempt ran (used to space retries so a daily cron doesn't hammer a declining card).
    failed_renewal_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"), default=0)
    last_renewal_attempt_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # The saved card token used for recurring charges. Promoted out of recurring_details (JSON)
    # so it is typed, queryable, and not a silent KeyError away from breaking renewals. The JSON
    # is kept as a fallback for rows written before this column existed.
    payment_method_id: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        # At most one live subscription row per user. Excludes EXPIRED/CANCELED so historical
        # rows are kept; the reuse-first top_up logic means this only bites a concurrent insert.
        Index(
            "uq_subscription_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('ACTIVE', 'PAST_DUE', 'PENDING')"),
        ),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="subscriptions")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="subscription", cascade="all, delete")

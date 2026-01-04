from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, TIMESTAMP, Enum, ForeignKey, String, Text
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

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="subscriptions")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="subscription", cascade="all, delete")

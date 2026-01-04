from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, TIMESTAMP, Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, TableNameMixin, UpdatedAtMixin
from .enums import PaymentEventType, PaymentProvider, PaymentStatus


class Payment(Base, CreatedAtMixin, UpdatedAtMixin, TableNameMixin):
    id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_id: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider, native_enum=False), nullable=False)
    amount: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, native_enum=False), nullable=False)
    subscription_id: Mapped[UUID] = mapped_column(
        PgUUID, ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # false only for first payments
    was_rewarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Data received from provider
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="payments")
    events: Mapped[list[PaymentEvent]] = relationship("PaymentEvent", back_populates="payment")
    subscription: Mapped[Subscription] = relationship("Subscription", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id} user={self.user_id} amount={self.amount}{self.currency} status={self.status}>"


class PaymentEvent(Base, CreatedAtMixin, TableNameMixin):
    id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(
        PgUUID, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider, native_enum=False), nullable=False)
    event_type: Mapped[PaymentEventType] = mapped_column(Enum(PaymentEventType, native_enum=False), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # false only for first payments

    # Relationships
    payment: Mapped[Payment] = relationship("Payment", back_populates="events")

    def __repr__(self):
        return f"<PaymentEvent {self.id} payment={self.payment_id} type={self.event_type}>"

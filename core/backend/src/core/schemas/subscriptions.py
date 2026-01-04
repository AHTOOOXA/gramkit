from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field

from core.infrastructure.database.models.enums import PaymentProvider, SubscriptionStatus


class SubscriptionSchema(BaseModel):
    id: UUID
    user_id: UUID
    product_id: str
    status: SubscriptionStatus
    start_date: datetime
    end_date: datetime
    canceled_at: datetime | None = None
    cancellation_reason: str | None = None
    cancellation_feedback: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def has_access(self) -> bool:
        """Determines if the subscription gives premium access."""
        return self.end_date is not None and datetime.now(UTC) < self.end_date

    @classmethod
    def get_mock_subscription(cls, user_id: UUID) -> SubscriptionSchema:
        mock_time = datetime.now(UTC) - timedelta(days=1)
        return cls(
            id=uuid4(),
            user_id=user_id,
            product_id="MOCK",
            status=SubscriptionStatus.NONE,
            start_date=mock_time,
            end_date=mock_time,
            canceled_at=mock_time,
            cancellation_reason=None,
            cancellation_feedback=None,
        )


class SubscriptionWithDetailsSchema(SubscriptionSchema):
    provider_id: PaymentProvider
    product_price: float
    currency: str


class CancelSubscriptionRequest(BaseModel):
    reason: str | None = Field(None, max_length=50, description="Cancellation reason code")
    feedback: str | None = Field(None, description="Optional user feedback")

from uuid import UUID

from pydantic import BaseModel, field_serializer

from core.infrastructure.database.models.enums import PaymentStatus


class ProductPriceSchema(BaseModel):
    currency: str
    amount: float


class ProductSchema(BaseModel):
    id: str
    name: str
    price: float
    currency: str
    duration_days: int
    is_recurring: bool
    # Every currency this product can be bought in (RUB/USD for card, XTR for Telegram Stars).
    # `price`/`currency` stay as the primary (RUB) display price for back-compat; the frontend reads
    # `prices` to surface the Stars (XTR) amount on the secondary CTA.
    prices: list[ProductPriceSchema] = []


class StartPurchaseRequest(BaseModel):
    product_id: str
    currency: str = "RUB"
    provider_id: str = "YOOKASSA"
    return_url: str | None = None
    locale: str | None = None


class StartPurchaseResponse(BaseModel):
    payment_id: str
    confirmation_token: str | None = None  # YooKassa embedded widget
    confirmation_url: str | None = None  # Telegram Stars invoice link (legacy/other providers)
    amount: float
    currency: str

    @field_serializer("payment_id")
    def serialize_payment_id(self, value: str | UUID) -> str:
        return str(value)


class PaymentStatusResponse(BaseModel):
    payment_id: str
    status: PaymentStatus

    @field_serializer("payment_id")
    def serialize_payment_id(self, value: str | UUID) -> str:
        return str(value)

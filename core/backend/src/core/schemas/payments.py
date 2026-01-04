from uuid import UUID

from pydantic import BaseModel, field_serializer


class ProductSchema(BaseModel):
    id: str
    name: str
    price: float
    currency: str
    duration_days: int
    is_recurring: bool


class StartPurchaseRequest(BaseModel):
    product_id: str
    currency: str = "RUB"
    provider_id: str = "YOOKASSA"
    return_url: str


class StartPurchaseResponse(BaseModel):
    payment_id: str
    confirmation_url: str
    amount: float
    currency: str

    @field_serializer("payment_id")
    def serialize_payment_id(self, value: str | UUID) -> str:
        return str(value)

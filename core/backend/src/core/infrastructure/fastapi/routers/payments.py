"""Core payment routes.

These routes provide payment endpoints that can be used by apps.
Apps must provide service layer implementation via get_services dependency.

The routes are generic and can work with any payment provider configured
in the app's payment service.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from core.infrastructure.fastapi.dependencies import get_services, get_user
from core.infrastructure.fastapi.rate_limiter import HARD_LIMIT, SOFT_LIMIT, limiter
from core.infrastructure.logging import get_logger
from core.schemas.payments import ProductSchema, StartPurchaseRequest, StartPurchaseResponse
from core.schemas.users import UserSchema
from core.services.requests import CoreRequestsService

router = APIRouter(prefix="/payments", tags=["payments"])

logger = get_logger(__name__)


@router.get("/products", response_model=list[ProductSchema])
@limiter.limit(SOFT_LIMIT)
async def get_products(
    request: Request,
    user: UserSchema = Depends(get_user),
    services: CoreRequestsService = Depends(get_services),
) -> list[ProductSchema]:
    """
    Get available products for purchase.

    Returns products excluding test products, suitable for profile/shop pages.
    """
    # Get products for profile page (excludes test products)
    products_data = await services.payments.get_profile_products_async(currency="RUB")

    # Convert to schema
    products = []
    for product_data in products_data:
        products.append(
            ProductSchema(
                id=product_data["id"],
                name=product_data["name"],
                price=product_data["price"],
                currency=product_data["currency"],
                duration_days=product_data["duration_days"],
                is_recurring=product_data["recurring"],
            )
        )
    return products


@router.post("/start_purchase", response_model=StartPurchaseResponse)
@limiter.limit(HARD_LIMIT)
async def start_purchase(
    request: Request,
    purchase_request: StartPurchaseRequest,
    user: UserSchema = Depends(get_user),
    services: CoreRequestsService = Depends(get_services),
) -> StartPurchaseResponse:
    """
    Start a payment for a product.

    Creates a payment and returns a confirmation URL for the user to complete payment.
    Supports multiple payment providers (YooKassa, Telegram Stars, etc).
    """
    try:
        return_data = await services.payments.start_payment(
            user_id=user.id,
            product_id=purchase_request.product_id,
            currency=purchase_request.currency,
            provider_id=purchase_request.provider_id,
            return_url=purchase_request.return_url,
        )
        return StartPurchaseResponse(**return_data)
    except ValueError as e:
        logger.warning(f"Invalid payment request from user {user.id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

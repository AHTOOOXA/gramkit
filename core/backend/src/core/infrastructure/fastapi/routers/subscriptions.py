"""Core Subscription Management Routes.

Generic subscription management endpoints for:
- Getting subscription status with details
- Cancelling subscription with feedback

Apps must override get_user and get_services dependencies.
"""

from fastapi import APIRouter, Depends, Request

from core.infrastructure.fastapi.dependencies import get_services, get_user
from core.infrastructure.fastapi.rate_limiter import HARD_LIMIT, SOFT_LIMIT, limiter
from core.infrastructure.logging import get_logger
from core.schemas.subscriptions import CancelSubscriptionRequest, SubscriptionSchema, SubscriptionWithDetailsSchema
from core.schemas.users import UserSchema
from core.services.requests import CoreRequestsService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

logger = get_logger(__name__)


@router.get("/", response_model=SubscriptionWithDetailsSchema)
@limiter.limit(SOFT_LIMIT)
async def get_subscription(
    request: Request,
    services: CoreRequestsService = Depends(get_services),
    user: UserSchema = Depends(get_user),
) -> SubscriptionWithDetailsSchema:
    """Get current subscription with details for authenticated user."""
    return await services.subscriptions.get_subscription_with_details_for_user(user.id)


@router.post("/cancel", response_model=SubscriptionSchema)
@limiter.limit(HARD_LIMIT)
async def cancel_subscription(
    request: Request,
    cancel_data: CancelSubscriptionRequest,
    services: CoreRequestsService = Depends(get_services),
    user: UserSchema = Depends(get_user),
) -> SubscriptionSchema:
    """Cancel current subscription with optional reason and feedback."""
    return await services.subscriptions.cancel_subscription(user.id, cancel_data.reason, cancel_data.feedback)

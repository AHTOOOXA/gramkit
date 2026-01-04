"""Core User Management Routes.

Generic user management endpoints for:
- Getting user profile
- Updating user profile

Apps can override authentication via get_user dependency.
"""

from fastapi import APIRouter, Depends, Request, Response

from core.infrastructure.fastapi.dependencies import get_services, get_user
from core.infrastructure.fastapi.rate_limiter import HARD_LIMIT, SOFT_LIMIT, limiter
from core.infrastructure.logging import get_logger
from core.schemas.users import UpdateUserRequest, UserSchema
from core.services.requests import CoreRequestsService

router = APIRouter(prefix="/users", tags=["users"])

logger = get_logger(__name__)


@router.get("/me", response_model=UserSchema)
@limiter.limit(SOFT_LIMIT)
async def get_current_user(
    request: Request,
    user: UserSchema = Depends(get_user),
) -> UserSchema:
    """Get current authenticated user profile."""
    return user


@router.patch("/me", response_model=UserSchema)
@limiter.limit(HARD_LIMIT)
async def update_current_user(
    request: Request,
    response: Response,
    user_data: UpdateUserRequest,
    services: CoreRequestsService = Depends(get_services),
    user: UserSchema = Depends(get_user),
) -> UserSchema:
    """Update current authenticated user profile."""
    updated_user = await services.users.update_user(user.id, user_data)

    if user_data.is_onboarded is True:
        response.set_cookie(
            key="user_onboarded",
            value="true",
            path="/",
            max_age=31536000,
            httponly=False,
            samesite="lax",
        )

    return updated_user

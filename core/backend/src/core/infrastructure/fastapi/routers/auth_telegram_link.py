"""Telegram account linking router.

Provides endpoints for web users to link their Telegram accounts.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from core.infrastructure.fastapi.dependencies import get_current_user_id, get_services
from core.infrastructure.logging import get_logger
from core.schemas.auth import (
    ErrorResponse,
    TelegramLinkStartResponse,
    TelegramLinkStatusResponse,
)
from core.services.requests import CoreRequestsService

logger = get_logger(__name__)


# Error code to HTTP status mapping
ERROR_STATUS_MAP = {
    "rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
    "already_linked": status.HTTP_409_CONFLICT,
    "token_invalid": status.HTTP_400_BAD_REQUEST,
    "token_expired": status.HTTP_410_GONE,
    "telegram_already_used": status.HTTP_409_CONFLICT,
    "user_not_found": status.HTTP_404_NOT_FOUND,
}

# Error code to user message mapping
ERROR_MESSAGE_MAP = {
    "rate_limited": "Too many requests. Please try again later.",
    "already_linked": "Telegram account already linked to this account.",
    "token_invalid": "Invalid or expired link token.",
    "token_expired": "Link token expired. Please start again.",
    "telegram_already_used": "This Telegram account is already linked to another user.",
    "user_not_found": "User not found.",
}


def _handle_link_error(error: ValueError) -> HTTPException:
    """Convert link service error to HTTP exception."""
    error_code = str(error)
    status_code = ERROR_STATUS_MAP.get(error_code, status.HTTP_400_BAD_REQUEST)
    message = ERROR_MESSAGE_MAP.get(error_code, "An error occurred.")

    return HTTPException(
        status_code=status_code,
        detail={"error": error_code, "message": message},
    )


router = APIRouter(prefix="/auth/link/telegram", tags=["account-linking"])


@router.post(
    "/start",
    response_model=TelegramLinkStartResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        409: {"model": ErrorResponse, "description": "Already linked"},
        429: {"model": ErrorResponse, "description": "Rate limited"},
    },
)
async def start_link(
    services: CoreRequestsService = Depends(get_services),
    user_id: UUID | None = Depends(get_current_user_id),
) -> TelegramLinkStartResponse:
    """Start Telegram account linking flow.

    Generates a link token and returns bot URL with deep link.
    User should open the bot URL to complete linking.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "not_authenticated", "message": "Login required"},
        )

    try:
        result = await services.telegram_link.start_link(user_id)
        return TelegramLinkStartResponse(
            link_token=result["link_token"],
            bot_url=result["bot_url"],
            expires_in=result["expires_in"],
        )
    except ValueError as e:
        raise _handle_link_error(e)


@router.get(
    "/poll",
    response_model=TelegramLinkStatusResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Token not found"},
    },
)
async def poll_link_status(
    token: str,
    services: CoreRequestsService = Depends(get_services),
    user_id: UUID | None = Depends(get_current_user_id),
) -> TelegramLinkStatusResponse:
    """Poll link token status.

    Frontend polls this endpoint to detect when linking completes.
    Returns status: "pending" | "completed" | "expired"
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "not_authenticated", "message": "Login required"},
        )

    result = await services.telegram_link.get_status(token)

    if result is None:
        return TelegramLinkStatusResponse(status="expired")

    return TelegramLinkStatusResponse(
        status=result["status"],
        telegram_id=result.get("telegram_id"),
        telegram_username=result.get("telegram_username"),
        error=result.get("error"),
    )

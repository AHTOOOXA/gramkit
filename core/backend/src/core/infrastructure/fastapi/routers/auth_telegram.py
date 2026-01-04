"""Telegram authentication routes.

This router consolidates all Telegram authentication methods:
1. Code-based auth: User receives 6-digit code in Telegram DM
2. Deep link auth: User clicks bot link to authenticate

URL structure:
- POST /auth/login/telegram/code/send       - Send verification code
- POST /auth/login/telegram/code/verify     - Verify code, create session
- POST /auth/login/telegram/deeplink/start  - Start deep link flow
- GET  /auth/login/telegram/deeplink/poll   - Check deep link status
- POST /auth/logout                         - Logout (destroy session)

# TODO: Email auth endpoints (future)
# - POST /auth/email/send   - Send email verification code
# - POST /auth/email/verify - Verify email code, create session
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from core.infrastructure.config import settings
from core.infrastructure.fastapi.dependencies import get_services
from core.infrastructure.logging import get_logger
from core.infrastructure.session import clear_session_cookie, get_session_from_request, set_session_cookie
from core.schemas.users import UserSchema
from core.services.requests import CoreRequestsService

router = APIRouter(prefix="/auth", tags=["authentication"])

logger = get_logger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================


class LogoutResponse(BaseModel):
    message: str


# Code-based auth models
class SendCodeRequest(BaseModel):
    username: str


class SendCodeResponse(BaseModel):
    message: str
    expires_in: int


class VerifyCodeRequest(BaseModel):
    username: str
    code: str


class VerifyCodeResponse(BaseModel):
    user: UserSchema
    message: str


# Deep link auth models
class DeeplinkLoginStartResponse(BaseModel):
    """Response for starting deep link login."""

    token: str
    bot_url: str
    expires_in: int = 300


class DeeplinkLoginPollResponse(BaseModel):
    """Response for checking deep link login status."""

    status: Literal["pending", "verified", "expired"]
    user_id: UUID | None = None


# =============================================================================
# Logout Endpoint
# =============================================================================


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    services: CoreRequestsService = Depends(get_services),
):
    """
    Logout endpoint that destroys the user's session.

    Uses SessionService for session destruction (business logic) and
    session cookie functions for cookie clearing (HTTP concern).
    """
    try:
        session_id = get_session_from_request(request)

        if session_id:
            destroyed = await services.sessions.destroy_session(session_id)
            if destroyed:
                logger.info(f"Session {session_id} destroyed during logout")
            else:
                logger.warning(f"Session {session_id} not found during logout")

        clear_session_cookie(response)

        return LogoutResponse(message="Successfully logged out")

    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        try:
            clear_session_cookie(response)
        except Exception as clear_error:
            logger.error(f"Failed to clear cookie: {clear_error}")

        raise HTTPException(status_code=500, detail="Logout failed. Please try again.")


# =============================================================================
# Code-based Auth Endpoints
# =============================================================================


@router.post("/login/telegram/code/send", response_model=SendCodeResponse)
async def send_verification_code(request: SendCodeRequest, services: CoreRequestsService = Depends(get_services)):
    """
    Send 6-digit verification code to user's Telegram DM.
    """
    try:
        result = await services.auth.send_verification_code(request.username)

        if not result["success"]:
            error_code = result.get("error_code", "UNKNOWN_ERROR")
            if error_code == "RATE_LIMIT_EXCEEDED":
                raise HTTPException(status_code=429, detail=result["error"])
            elif error_code == "USER_NOT_FOUND":
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

        code = result["code"]
        telegram_id = result["telegram_id"]

        verification_message = (
            f"🔐 <b>Verification Code</b>\n\n"
            f"Your login code: <code>{code}</code>\n\n"
            f"Enter this code on the website to complete your login.\n"
            f"Code expires in 5 minutes."
        )

        message_sent = await services.messages.send_message(
            telegram_id=telegram_id, text=verification_message, parse_mode="HTML"
        )

        if not message_sent:
            logger.warning(f"Failed to send verification code to telegram_id {telegram_id}")

        return SendCodeResponse(message=result["message"], expires_in=result["expires_in"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send code error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification code")


@router.post("/login/telegram/code/verify", response_model=VerifyCodeResponse)
async def verify_code_and_login(
    request: VerifyCodeRequest,
    response: Response,
    services: CoreRequestsService = Depends(get_services),
):
    """
    Verify 6-digit code and create authenticated session.

    Uses SessionService for session creation (business logic) and
    session cookie functions for cookie setting (HTTP concern).
    """
    try:
        result = await services.auth.verify_code(request.username, request.code)

        if not result["success"]:
            error_code = result.get("error_code", "UNKNOWN_ERROR")
            if error_code == "RATE_LIMIT_EXCEEDED":
                raise HTTPException(status_code=429, detail=result["error"])
            elif error_code in ["CODE_EXPIRED", "CODE_MISMATCH", "INVALID_CODE_FORMAT"]:
                raise HTTPException(status_code=400, detail=result["error"])
            elif error_code == "USER_NOT_FOUND":
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

        user = result["user"]
        session_id = result["session_id"]

        set_session_cookie(response, session_id)

        logger.info(f"User {user.id} logged in via Telegram verification")

        return VerifyCodeResponse(user=user, message="Successfully logged in")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify code error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Verification failed")


# =============================================================================
# Deep Link Auth Endpoints
# =============================================================================


@router.post("/login/telegram/deeplink/start", response_model=DeeplinkLoginStartResponse)
async def start_deeplink_login(
    request: Request,
    services: CoreRequestsService = Depends(get_services),
):
    """
    Start Telegram deep link login flow.

    Returns a token and bot URL. User should be redirected to bot URL.
    Frontend should then poll /poll endpoint.
    """
    ip = request.client.host if request.client else None
    token = await services.auth.create_link_token(ip)

    bot_url_config = settings.bot.url
    bot_username = _extract_bot_username(bot_url_config)
    bot_url = f"https://t.me/{bot_username}?start=auth_{token}"

    logger.info(f"Deeplink login started: token={token[:8]}...")

    return DeeplinkLoginStartResponse(token=token, bot_url=bot_url, expires_in=300)


@router.get("/login/telegram/deeplink/poll", response_model=DeeplinkLoginPollResponse)
async def poll_deeplink_login(
    token: str,
    response: Response,
    services: CoreRequestsService = Depends(get_services),
):
    """
    Check status of deep link login token.

    Frontend should poll this endpoint after redirecting user to Telegram.
    When status is "verified", session cookie is set and user is logged in.
    """
    token_data = await services.auth.get_link_status(token)

    if not token_data:
        raise HTTPException(status_code=410, detail="Token expired or invalid")

    status = token_data.get("status", "pending")

    if status == "pending":
        return DeeplinkLoginPollResponse(status="pending")

    if status == "verified":
        session_id = token_data.get("session_id")
        user_id = token_data.get("user_id")

        if not session_id or not user_id:
            logger.error(f"Token verified but missing session/user: {token[:8]}...")
            raise HTTPException(status_code=500, detail="Auth state corrupted")

        await services.auth.consume_link_token(token)

        set_session_cookie(response, session_id)

        logger.info(f"Deeplink login completed: user_id={user_id}, token={token[:8]}...")

        return DeeplinkLoginPollResponse(status="verified", user_id=user_id)

    raise HTTPException(status_code=500, detail=f"Unknown token status: {status}")


# =============================================================================
# Helpers
# =============================================================================


def _extract_bot_username(bot_url: str) -> str:
    """Extract bot username from bot URL like https://t.me/BotName."""
    if "t.me/" in bot_url:
        return bot_url.split("t.me/")[-1].split("?")[0].split("/")[0]
    return bot_url

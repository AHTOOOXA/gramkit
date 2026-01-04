"""Email authentication router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr

from core.infrastructure.fastapi.dependencies import get_current_user_id, get_services
from core.infrastructure.logging import get_logger
from core.infrastructure.session import set_session_cookie
from core.schemas.auth import (
    EmailLinkCompleteRequest,
    EmailLinkCompleteResponse,
    EmailLinkRequest,
    EmailLinkResponse,
    EmailLoginRequest,
    EmailLoginResponse,
    EmailResendRequest,
    EmailResendResponse,
    EmailSignupCompleteRequest,
    EmailSignupCompleteResponse,
    EmailSignupRequest,
    EmailSignupResponse,
    ErrorResponse,
)
from core.services.requests import CoreRequestsService

logger = get_logger(__name__)


# Request/Response models for password reset
class PasswordResetStartRequest(BaseModel):
    email: EmailStr


class PasswordResetStartResponse(BaseModel):
    reset_token: str
    expires_in: int


class PasswordResetCompleteRequest(BaseModel):
    reset_token: str
    code: str
    new_password: str


class PasswordResetCompleteResponse(BaseModel):
    success: bool = True


# Error code to HTTP status mapping
ERROR_STATUS_MAP = {
    "rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
    "email_already_in_use": status.HTTP_409_CONFLICT,
    "email_already_verified": status.HTTP_409_CONFLICT,
    "signup_token_invalid": status.HTTP_400_BAD_REQUEST,
    "signup_token_expired": status.HTTP_410_GONE,
    "code_invalid": status.HTTP_400_BAD_REQUEST,
    "code_expired": status.HTTP_410_GONE,
    "password_too_weak": status.HTTP_400_BAD_REQUEST,
    "invalid_credentials": status.HTTP_401_UNAUTHORIZED,
    "account_locked": status.HTTP_423_LOCKED,
    "email_send_failed": status.HTTP_503_SERVICE_UNAVAILABLE,
    "user_not_found": status.HTTP_404_NOT_FOUND,
    "reset_token_invalid": status.HTTP_400_BAD_REQUEST,
}

# Error code to user message mapping
ERROR_MESSAGE_MAP = {
    "rate_limited": "Too many requests. Please try again later.",
    "email_already_in_use": "Email already in use by another account.",
    "email_already_verified": "Email already linked to this account.",
    "signup_token_invalid": "Invalid or expired signup token.",
    "signup_token_expired": "Signup session expired. Please start again.",
    "code_invalid": "Invalid verification code.",
    "code_expired": "Verification code expired. Please request a new one.",
    "password_too_weak": "Password does not meet complexity requirements.",
    "invalid_credentials": "Invalid credentials.",
    "account_locked": "Account temporarily locked. Please try again in 15 minutes.",
    "email_send_failed": "Unable to send verification email. Please try again.",
    "user_not_found": "User not found.",
    "reset_token_invalid": "Invalid or expired reset token.",
}


def _handle_auth_error(error: ValueError) -> HTTPException:
    """Convert auth service error to HTTP exception."""
    error_code = str(error)
    status_code = ERROR_STATUS_MAP.get(error_code, status.HTTP_400_BAD_REQUEST)
    message = ERROR_MESSAGE_MAP.get(error_code, "An error occurred.")

    return HTTPException(
        status_code=status_code,
        detail={"error": error_code, "message": message},
    )


router = APIRouter(prefix="/auth", tags=["email-auth"])


# =============================================================================
# Email Check Endpoint
# =============================================================================


class EmailCheckRequest(BaseModel):
    email: EmailStr


class EmailCheckResponse(BaseModel):
    exists: bool


@router.post(
    "/email/check",
    response_model=EmailCheckResponse,
)
async def check_email(
    request: EmailCheckRequest,
    services: CoreRequestsService = Depends(get_services),
) -> EmailCheckResponse:
    """
    Check if email is already registered.

    Returns whether the email exists in the system.
    """
    exists = await services.auth.email_check_exists(request.email)
    return EmailCheckResponse(exists=exists)


# =============================================================================
# Signup Endpoints
# =============================================================================


@router.post(
    "/signup/email/start",
    response_model=EmailSignupResponse,
    responses={
        409: {"model": ErrorResponse, "description": "Email already in use"},
        429: {"model": ErrorResponse, "description": "Rate limited"},
    },
)
async def start_signup(
    request: EmailSignupRequest,
    services: CoreRequestsService = Depends(get_services),
) -> EmailSignupResponse:
    """
    Start email signup flow.

    Sends verification code to provided email address.
    Returns signup token for subsequent requests.
    """
    try:
        result = await services.auth.email_start_signup(request.email)
        return EmailSignupResponse(
            message="Verification code sent",
            signup_token=result["signup_token"],
            expires_in=result["expires_in"],
        )
    except ValueError as e:
        raise _handle_auth_error(e)


@router.post(
    "/signup/email/complete",
    response_model=EmailSignupCompleteResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid code or password"},
        409: {"model": ErrorResponse, "description": "Email already in use"},
        410: {"model": ErrorResponse, "description": "Token expired"},
    },
)
async def complete_signup(
    request: EmailSignupCompleteRequest,
    response: Response,
    services: CoreRequestsService = Depends(get_services),
) -> EmailSignupCompleteResponse:
    """
    Complete email signup.

    Verifies code, validates password, creates user account.
    Sets session cookie on success.
    """
    try:
        result = await services.auth.email_complete_signup(
            signup_token=request.signup_token,
            code=request.code,
            password=request.password,
            username=request.username,
            language_code=request.language_code,
        )

        user = result["user"]
        session_id = result["session_id"]

        set_session_cookie(response, session_id)

        return EmailSignupCompleteResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
        )
    except ValueError as e:
        raise _handle_auth_error(e)


# =============================================================================
# Login Endpoint
# =============================================================================


@router.post(
    "/login/email",
    response_model=EmailLoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        423: {"model": ErrorResponse, "description": "Account locked"},
    },
)
async def login(
    request: EmailLoginRequest,
    response: Response,
    services: CoreRequestsService = Depends(get_services),
) -> EmailLoginResponse:
    """
    Login with email or username and password.

    Sets session cookie on success.
    """
    try:
        result = await services.auth.email_login(
            email_or_username=request.email_or_username,
            password=request.password,
        )

        user = result["user"]
        session_id = result["session_id"]

        set_session_cookie(response, session_id)

        return EmailLoginResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
        )
    except ValueError as e:
        raise _handle_auth_error(e)


# =============================================================================
# Link Endpoints (Requires Authentication)
# =============================================================================


@router.post(
    "/link/email/start",
    response_model=EmailLinkResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        409: {"model": ErrorResponse, "description": "Email already in use"},
        429: {"model": ErrorResponse, "description": "Rate limited"},
    },
)
async def start_link(
    request: EmailLinkRequest,
    services: CoreRequestsService = Depends(get_services),
    user_id: UUID | None = Depends(get_current_user_id),
) -> EmailLinkResponse:
    """
    Start email linking flow for authenticated Telegram users.

    Sends verification code to provided email address.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "not_authenticated", "message": "Login required"},
        )

    try:
        result = await services.auth.email_start_link(
            user_id=user_id,
            email=request.email,
        )
        return EmailLinkResponse(expires_in=result["expires_in"])
    except ValueError as e:
        raise _handle_auth_error(e)


@router.post(
    "/link/email/complete",
    response_model=EmailLinkCompleteResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid code or password"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        409: {"model": ErrorResponse, "description": "Email already in use"},
        410: {"model": ErrorResponse, "description": "Code expired"},
    },
)
async def complete_link(
    request: EmailLinkCompleteRequest,
    services: CoreRequestsService = Depends(get_services),
    user_id: UUID | None = Depends(get_current_user_id),
) -> EmailLinkCompleteResponse:
    """
    Complete email linking flow.

    Verifies code and sets password for email login.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "not_authenticated", "message": "Login required"},
        )

    try:
        await services.auth.email_complete_link(
            user_id=user_id,
            code=request.code,
            password=request.password,
        )
        return EmailLinkCompleteResponse()
    except ValueError as e:
        raise _handle_auth_error(e)


# =============================================================================
# Password Reset Endpoints
# =============================================================================


@router.post(
    "/password/reset/start",
    response_model=PasswordResetStartResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Email not found"},
        429: {"model": ErrorResponse, "description": "Rate limited"},
    },
)
async def start_reset(
    request: PasswordResetStartRequest,
    services: CoreRequestsService = Depends(get_services),
) -> PasswordResetStartResponse:
    """
    Start password reset flow.

    Sends verification code to provided email address.
    Returns reset token for subsequent requests.
    """
    try:
        result = await services.auth.email_start_reset(request.email)
        return PasswordResetStartResponse(
            reset_token=result["reset_token"],
            expires_in=result["expires_in"],
        )
    except ValueError as e:
        raise _handle_auth_error(e)


@router.post(
    "/password/reset/complete",
    response_model=PasswordResetCompleteResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid code or password"},
        410: {"model": ErrorResponse, "description": "Token expired"},
    },
)
async def complete_reset(
    request: PasswordResetCompleteRequest,
    services: CoreRequestsService = Depends(get_services),
) -> PasswordResetCompleteResponse:
    """
    Complete password reset.

    Verifies code and sets new password.
    """
    try:
        await services.auth.email_complete_reset(
            reset_token=request.reset_token,
            code=request.code,
            new_password=request.new_password,
        )
        return PasswordResetCompleteResponse()
    except ValueError as e:
        raise _handle_auth_error(e)


# =============================================================================
# Resend Endpoint
# =============================================================================


@router.post(
    "/signup/email/resend",
    response_model=EmailResendResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid token"},
        410: {"model": ErrorResponse, "description": "Token expired"},
        429: {"model": ErrorResponse, "description": "Rate limited"},
    },
)
async def resend_code(
    request: EmailResendRequest,
    services: CoreRequestsService = Depends(get_services),
    user_id: UUID | None = Depends(get_current_user_id),
) -> EmailResendResponse:
    """
    Resend verification code.

    For signup flow: provide signup_token.
    For link flow: requires authentication (uses current user_id).
    """
    try:
        # Determine which flow to resend for
        if request.signup_token:
            result = await services.auth.email_resend_code(signup_token=request.signup_token)
        elif user_id:
            result = await services.auth.email_resend_code(user_id=user_id)
        else:
            raise ValueError("signup_token_invalid")

        return EmailResendResponse(expires_in=result["expires_in"])
    except ValueError as e:
        raise _handle_auth_error(e)

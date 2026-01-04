"""Email authentication schemas and error codes."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class EmailAuthError(StrEnum):
    """Error codes for email authentication."""

    # Validation errors
    INVALID_EMAIL = "invalid_email"
    PASSWORD_TOO_WEAK = "password_too_weak"

    # Availability errors
    EMAIL_ALREADY_VERIFIED = "email_already_verified"  # On this account
    EMAIL_ALREADY_IN_USE = "email_already_in_use"  # On another account

    # Verification errors
    CODE_EXPIRED = "code_expired"
    CODE_INVALID = "code_invalid"
    SIGNUP_TOKEN_INVALID = "signup_token_invalid"
    SIGNUP_TOKEN_EXPIRED = "signup_token_expired"

    # Auth errors
    INVALID_CREDENTIALS = "invalid_credentials"  # Generic for security
    ACCOUNT_LOCKED = "account_locked"

    # Rate limiting
    RATE_LIMITED = "rate_limited"


# Request/Response schemas (basic structure, will be completed in Phase 04)


class EmailSignupRequest(BaseModel):
    """Request to start email signup flow."""

    email: EmailStr


class EmailSignupResponse(BaseModel):
    """Response for signup initiation."""

    message: str
    signup_token: str
    expires_in: int = 600  # 10 minutes


class EmailSignupCompleteRequest(BaseModel):
    """Request to complete email signup."""

    signup_token: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    language_code: str | None = Field(default=None, max_length=10)


class EmailLoginRequest(BaseModel):
    """Request to login with email or username."""

    email_or_username: str = Field(min_length=3, max_length=255)
    password: str


class EmailLinkRequest(BaseModel):
    """Request to start email linking for Telegram users."""

    email: EmailStr


class EmailLinkCompleteRequest(BaseModel):
    """Request to complete email linking."""

    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    password: str = Field(min_length=8, max_length=128)


class EmailResendRequest(BaseModel):
    """Request to resend verification code."""

    signup_token: str | None = None  # For signup flow; if None, uses auth session for link flow


# Response schemas


class EmailSignupCompleteResponse(BaseModel):
    """Response for successful signup completion."""

    user_id: UUID
    username: str
    email: str
    message: str = "Account created successfully"


class EmailLoginResponse(BaseModel):
    """Response for successful login."""

    user_id: UUID
    username: str | None
    email: str | None
    message: str = "Login successful"


class EmailLinkResponse(BaseModel):
    """Response for starting email link flow."""

    message: str = "Verification code sent"
    expires_in: int


class EmailLinkCompleteResponse(BaseModel):
    """Response for successful email linking."""

    message: str = "Email linked successfully"
    success: bool = True


class EmailResendResponse(BaseModel):
    """Response for code resend."""

    message: str = "Verification code sent"
    expires_in: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str


# =========================================================================
# Telegram Link Schemas (for linking Telegram to existing email accounts)
# =========================================================================


class TelegramLinkError(StrEnum):
    """Error codes for Telegram account linking."""

    ALREADY_LINKED = "already_linked"
    TOKEN_INVALID = "token_invalid"
    TOKEN_EXPIRED = "token_expired"
    RATE_LIMITED = "rate_limited"
    TELEGRAM_ALREADY_USED = "telegram_already_used"


class TelegramLinkStartResponse(BaseModel):
    """Response for starting Telegram link flow."""

    link_token: str
    bot_url: str
    expires_in: int = 300


class TelegramLinkStatusResponse(BaseModel):
    """Response for checking Telegram link status."""

    status: str
    telegram_id: int | None = None
    telegram_username: str | None = None
    error: str | None = None  # Error code when status is "error"

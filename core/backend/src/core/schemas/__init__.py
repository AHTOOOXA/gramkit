"""Core schemas for TMA platform."""

from core.schemas.auth import (
    EmailAuthError,
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

__all__ = [
    "EmailAuthError",
    "EmailLinkCompleteRequest",
    "EmailLinkCompleteResponse",
    "EmailLinkRequest",
    "EmailLinkResponse",
    "EmailLoginRequest",
    "EmailLoginResponse",
    "EmailResendRequest",
    "EmailResendResponse",
    "EmailSignupCompleteRequest",
    "EmailSignupCompleteResponse",
    "EmailSignupRequest",
    "EmailSignupResponse",
    "ErrorResponse",
]

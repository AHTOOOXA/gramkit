"""Telegram Mini App authentication infrastructure.

This module provides authentication components for Telegram Mini Apps (TMAs),
including initData validation and user verification.
"""

from core.infrastructure.auth.telegram import (
    InvalidInitDataError,
    NoInitDataError,
    TelegramAuthenticator,
    TelegramUser,
    generate_secret_key,
)

__all__ = [
    "TelegramAuthenticator",
    "TelegramUser",
    "generate_secret_key",
    "NoInitDataError",
    "InvalidInitDataError",
]

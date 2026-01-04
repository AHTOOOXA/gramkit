"""Telegram webhook secret token validator."""

import hmac

from fastapi import HTTPException


class TelegramWebhookValidator:
    """Validate Telegram webhook secret tokens."""

    def __init__(self, secret_token: str):
        self.secret_token = secret_token

    def validate_secret(self, header_value: str | None) -> bool:
        """
        Validate Telegram webhook secret token.

        Telegram sends the secret token in X-Telegram-Bot-Api-Secret-Token header.
        This secret is set when registering the webhook with Telegram.

        Args:
            header_value: The X-Telegram-Bot-Api-Secret-Token header value

        Returns:
            True if secret token is valid

        Raises:
            HTTPException: If secret token is missing or invalid
        """
        if not header_value:
            raise HTTPException(status_code=401, detail="Missing X-Telegram-Bot-Api-Secret-Token header")

        # Constant-time comparison (prevent timing attacks)
        is_valid = hmac.compare_digest(header_value, self.secret_token)

        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid webhook secret token")

        return True

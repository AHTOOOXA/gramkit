"""Telegram Mini App (TMA) authentication infrastructure.

This module provides authentication components for Telegram Mini Apps:
- TelegramUser: Dataclass representing Telegram user from initData
- TelegramAuthenticator: HMAC-based validation of initData
- Helper functions and exceptions

Links:
    - https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    - https://core.telegram.org/bots/webapps#webappinitdata
"""

import dataclasses
import hashlib
import hmac
import json
from json import JSONDecodeError
from urllib.parse import parse_qsl, unquote


@dataclasses.dataclass
class TelegramUser:
    """Represents a Telegram user from WebAppInitData.

    Links:
        https://core.telegram.org/bots/webapps#webappuser
    """

    id: int
    first_name: str
    is_bot: bool | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None
    added_to_attachment_menu: bool | None = None
    allows_write_to_pm: bool | None = None
    photo_url: str | None = None


def generate_secret_key(token: str) -> bytes:
    """Generates a secret key from a Telegram Bot Token.

    This is part of the Telegram Mini App authentication flow.
    The secret key is used to validate initData received from the web app.

    Links:
        https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Args:
        token: Telegram Bot Token

    Returns:
        bytes: Secret key for HMAC validation
    """
    base = b"WebAppData"
    token_enc = token.encode("utf-8")
    return hmac.digest(base, token_enc, hashlib.sha256)


class TelegramAuthenticator:
    """Validates Telegram Mini App initData using HMAC.

    This authenticator verifies that initData received from a Telegram Mini App
    was actually sent by Telegram and hasn't been tampered with.

    Links:
        https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Example:
        >>> secret = generate_secret_key(bot_token)
        >>> authenticator = TelegramAuthenticator(secret)
        >>> user = authenticator.verify_token(init_data)
        >>> print(f"Authenticated user: {user.id}")
    """

    def __init__(self, secret: bytes):
        """Initialize authenticator with secret key.

        Args:
            secret: Secret key generated from bot token via generate_secret_key()
        """
        self._secret = secret

    @staticmethod
    def _parse_init_data(data: str) -> dict:
        """Convert init_data string into dictionary.

        Args:
            data: The query string passed by the webapp

        Returns:
            dict: Parsed init_data

        Raises:
            InvalidInitDataError: If data is empty or invalid
        """
        if not data:
            raise InvalidInitDataError("Init Data cannot be empty")
        return dict(parse_qsl(data))

    @staticmethod
    def _parse_user_data(data: str) -> dict:
        """Convert user value from WebAppInitData to Python dictionary.

        Links:
            https://core.telegram.org/bots/webapps#webappinitdata

        Args:
            data: URL-encoded JSON string with user data

        Returns:
            dict: Parsed user data

        Raises:
            InvalidInitDataError: If data cannot be decoded
        """
        try:
            return json.loads(unquote(data))
        except JSONDecodeError:
            raise InvalidInitDataError("Cannot decode init data")

    def _validate(self, hash_: str, token: str) -> bool:
        """Validates the data received from the Telegram web app.

        Uses the validation method from Telegram documentation.

        Links:
            https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

        Args:
            hash_: Hash from init data
            token: Init data from webapp (without hash field)

        Returns:
            bool: Validation result
        """
        token_bytes = token.encode("utf-8")
        client_hash = hmac.new(self._secret, token_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(client_hash, hash_)

    def verify_token(self, token: str) -> TelegramUser:
        """Verifies initData and returns Telegram user if valid.

        Links:
            https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

        Args:
            token: Init data from webapp (complete query string)

        Returns:
            TelegramUser: Telegram user if token is valid

        Raises:
            InvalidInitDataError: If the token is invalid or missing required fields
        """
        init_data = self._parse_init_data(token)
        token = "\n".join(
            f"{key}={val}" for key, val in sorted(init_data.items(), key=lambda item: item[0]) if key != "hash"
        )
        token = unquote(token)
        hash_ = init_data.get("hash")
        if not hash_:
            raise InvalidInitDataError("Init data does not contain hash")

        hash_ = hash_.strip()

        if not self._validate(hash_, token):
            raise InvalidInitDataError("Invalid token")

        user_data = init_data.get("user")
        if not user_data:
            raise InvalidInitDataError("Init data does not contain user")

        user_data = unquote(user_data)
        user_data = self._parse_user_data(user_data)
        return TelegramUser(**user_data)


class NoInitDataError(Exception):
    """Raised when initData is missing from request."""

    pass


class InvalidInitDataError(Exception):
    """Raised when initData validation fails."""

    pass

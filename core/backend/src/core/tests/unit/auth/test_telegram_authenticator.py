"""Unit tests for TelegramAuthenticator.

Tests the HMAC-based validation of Telegram Mini App initData.
Covers valid flows, tampering detection, edge cases, and error handling.

Links:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import json
from urllib.parse import parse_qsl, urlencode

import pytest

from core.infrastructure.auth.telegram import (
    InvalidInitDataError,
    TelegramAuthenticator,
    generate_secret_key,
)
from core.testing.fixtures.auth import generate_telegram_init_data


class TestTelegramAuthenticatorVerification:
    """Test TelegramAuthenticator.verify_token() validation logic."""

    @pytest.mark.contract
    def test_verify_valid_init_data(self):
        """Valid init_data should authenticate successfully."""
        # Arrange
        bot_token = "test_token_123"
        user_id = 123456
        username = "test_user"
        init_data = generate_telegram_init_data(user_id=user_id, username=username, bot_token=bot_token)
        secret = generate_secret_key(bot_token)
        authenticator = TelegramAuthenticator(secret)

        # Act
        user = authenticator.verify_token(init_data)

        # Assert
        assert user.id == user_id
        assert user.username == username
        assert user.first_name == "Test"

    @pytest.mark.contract
    def test_verify_extracts_all_user_fields(self):
        """All optional user fields should be extracted correctly."""
        # Arrange
        bot_token = "test_token_456"
        init_data = generate_telegram_init_data(
            user_id=789,
            username="full_user",
            first_name="John",
            last_name="Doe",
            language_code="uk",
            is_premium=True,
            bot_token=bot_token,
        )
        secret = generate_secret_key(bot_token)
        authenticator = TelegramAuthenticator(secret)

        # Act
        user = authenticator.verify_token(init_data)

        # Assert
        assert user.id == 789
        assert user.username == "full_user"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.language_code == "uk"
        assert user.is_premium is True

    @pytest.mark.contract
    def test_verify_rejects_tampered_user_id(self):
        """Tampering with user_id should fail HMAC validation."""
        # Arrange
        bot_token = "test_token_789"
        init_data = generate_telegram_init_data(user_id=123456, username="test_user", bot_token=bot_token)
        secret = generate_secret_key(bot_token)
        authenticator = TelegramAuthenticator(secret)

        # Tamper with user_id in the init_data
        parsed = dict(parse_qsl(init_data))
        user_data = json.loads(parsed["user"])
        user_data["id"] = 999999  # Change user ID
        parsed["user"] = json.dumps(user_data, separators=(",", ":"))
        tampered_init_data = urlencode(parsed)

        # Act & Assert
        with pytest.raises(InvalidInitDataError, match="Invalid token"):
            authenticator.verify_token(tampered_init_data)

    @pytest.mark.contract
    def test_verify_rejects_tampered_username(self):
        """Tampering with username should fail HMAC validation."""
        # Arrange
        bot_token = "test_token_abc"
        init_data = generate_telegram_init_data(user_id=123456, username="test_user", bot_token=bot_token)
        secret = generate_secret_key(bot_token)
        authenticator = TelegramAuthenticator(secret)

        # Tamper with username
        parsed = dict(parse_qsl(init_data))
        user_data = json.loads(parsed["user"])
        user_data["username"] = "attacker"
        parsed["user"] = json.dumps(user_data, separators=(",", ":"))
        tampered_init_data = urlencode(parsed)

        # Act & Assert
        with pytest.raises(InvalidInitDataError, match="Invalid token"):
            authenticator.verify_token(tampered_init_data)

    @pytest.mark.contract
    def test_verify_rejects_wrong_bot_token(self):
        """Using wrong bot token for secret generation should fail validation."""
        # Arrange
        correct_token = "correct_token"
        wrong_token = "wrong_token"
        init_data = generate_telegram_init_data(user_id=123456, username="test_user", bot_token=correct_token)
        wrong_secret = generate_secret_key(wrong_token)
        authenticator = TelegramAuthenticator(wrong_secret)

        # Act & Assert
        with pytest.raises(InvalidInitDataError, match="Invalid token"):
            authenticator.verify_token(init_data)

    @pytest.mark.contract
    def test_verify_rejects_empty_data(self):
        """Empty init_data should raise InvalidInitDataError."""
        # Arrange
        secret = generate_secret_key("test_token")
        authenticator = TelegramAuthenticator(secret)

        # Act & Assert
        with pytest.raises(InvalidInitDataError, match="cannot be empty"):
            authenticator.verify_token("")

    @pytest.mark.contract
    def test_verify_rejects_missing_hash(self):
        """Init_data without hash field should raise InvalidInitDataError."""
        # Arrange
        bot_token = "test_token_def"
        init_data = generate_telegram_init_data(user_id=123456, username="test_user", bot_token=bot_token)
        secret = generate_secret_key(bot_token)
        authenticator = TelegramAuthenticator(secret)

        # Remove hash from init_data
        parsed = dict(parse_qsl(init_data))
        del parsed["hash"]
        init_data_no_hash = urlencode(parsed)

        # Act & Assert
        with pytest.raises(InvalidInitDataError, match="hash"):
            authenticator.verify_token(init_data_no_hash)

    @pytest.mark.contract
    def test_verify_rejects_missing_user(self):
        """Init_data without user field should raise InvalidInitDataError."""
        # Arrange
        bot_token = "test_token_ghi"
        init_data = generate_telegram_init_data(user_id=123456, username="test_user", bot_token=bot_token)
        secret = generate_secret_key(bot_token)
        authenticator = TelegramAuthenticator(secret)

        # Remove user field
        parsed = dict(parse_qsl(init_data))
        del parsed["user"]
        init_data_no_user = urlencode(parsed)

        # Act & Assert
        # Note: Removing user field invalidates the hash, so "Invalid token" is raised first
        with pytest.raises(InvalidInitDataError):
            authenticator.verify_token(init_data_no_user)

    @pytest.mark.contract
    def test_verify_rejects_malformed_user_json(self):
        """Malformed user JSON should raise InvalidInitDataError."""
        # Arrange
        bot_token = "test_token_jkl"
        init_data = generate_telegram_init_data(user_id=123456, username="test_user", bot_token=bot_token)
        secret = generate_secret_key(bot_token)
        authenticator = TelegramAuthenticator(secret)

        # Corrupt user JSON (invalid JSON syntax)
        parsed = dict(parse_qsl(init_data))
        parsed["user"] = "{id:123}"  # Invalid JSON (missing quotes)
        corrupted_init_data = urlencode(parsed)

        # Act & Assert
        # Note: Corrupting user JSON invalidates the hash, so "Invalid token" is raised first
        with pytest.raises(InvalidInitDataError):
            authenticator.verify_token(corrupted_init_data)

    @pytest.mark.contract
    def test_generate_secret_key_deterministic(self):
        """Secret key generation should be deterministic for same token."""
        # Arrange
        token1 = "same_token"
        token2 = "same_token"
        different_token = "different_token"

        # Act
        secret1 = generate_secret_key(token1)
        secret2 = generate_secret_key(token2)
        secret_different = generate_secret_key(different_token)

        # Assert
        assert secret1 == secret2, "Same token should produce same secret"
        assert secret1 != secret_different, "Different tokens should produce different secrets"

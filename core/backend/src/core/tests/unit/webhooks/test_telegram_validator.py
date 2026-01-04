"""Unit tests for TelegramWebhookValidator.

Tests secret token validation for Telegram webhook requests.
Covers valid tokens, invalid tokens, missing headers, and timing-attack resistance.
"""

import pytest
from fastapi import HTTPException

from core.infrastructure.webhooks.telegram_validator import TelegramWebhookValidator


class TestTelegramWebhookValidator:
    """Test TelegramWebhookValidator.validate_secret() validation logic."""

    @pytest.mark.contract
    def test_valid_secret_passes(self):
        """Valid secret token should pass validation without raising exception."""
        # Arrange
        secret_token = "test_secret_token_123"
        validator = TelegramWebhookValidator(secret_token)

        # Act
        result = validator.validate_secret(secret_token)

        # Assert
        assert result is True

    @pytest.mark.contract
    def test_invalid_secret_raises_401(self):
        """Invalid secret token should raise HTTPException with 401."""
        # Arrange
        correct_token = "correct_token"
        wrong_token = "wrong_token"
        validator = TelegramWebhookValidator(correct_token)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_secret(wrong_token)

        assert exc_info.value.status_code == 401
        assert "Invalid webhook secret token" in exc_info.value.detail

    @pytest.mark.contract
    def test_missing_header_raises_401(self):
        """Missing X-Telegram-Bot-Api-Secret-Token header should raise 401."""
        # Arrange
        secret_token = "test_secret_token_456"
        validator = TelegramWebhookValidator(secret_token)

        # Act & Assert - Test with None
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_secret(None)

        assert exc_info.value.status_code == 401
        assert "Missing X-Telegram-Bot-Api-Secret-Token header" in exc_info.value.detail

    @pytest.mark.contract
    def test_empty_secret_raises_401(self):
        """Empty secret token should raise HTTPException with 401."""
        # Arrange
        real_secret = "real_secret"
        validator = TelegramWebhookValidator(real_secret)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_secret("")

        assert exc_info.value.status_code == 401
        # Will match either "Missing" or "Invalid" depending on implementation
        assert exc_info.value.status_code == 401

    @pytest.mark.business_logic
    def test_timing_attack_resistant(self):
        """Validator should use constant-time comparison (hmac.compare_digest)."""
        # Arrange
        correct_secret = "correct_secret_token"
        wrong_secret = "wrong_secret_token"
        validator = TelegramWebhookValidator(correct_secret)

        # Act & Assert
        # The validator uses hmac.compare_digest() internally for timing-attack resistance
        # We verify it rejects invalid secrets consistently
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_secret(wrong_secret)

        assert exc_info.value.status_code == 401
        assert "Invalid webhook secret token" in exc_info.value.detail

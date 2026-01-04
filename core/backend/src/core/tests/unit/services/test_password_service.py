"""Unit tests for PasswordService.

Tests password hashing, verification, validation, and code generation.
"""

import pytest

from core.services.password import PasswordService


@pytest.mark.business_logic
class TestPasswordHashAndVerify:
    """Tests for password hashing and verification."""

    @pytest.fixture
    def service(self):
        return PasswordService()

    def test_hash_password_creates_argon2_hash(self, service: PasswordService):
        """hash_password returns argon2 hash with correct prefix."""
        password = "MyPassword123"
        hash_result = service.hash_password(password)

        # argon2id hashes start with $argon2id$
        assert hash_result.startswith("$argon2id$")

    def test_hash_password_different_each_time(self, service: PasswordService):
        """hash_password produces different hashes for same password (due to salt)."""
        password = "SamePassword123"
        hash1 = service.hash_password(password)
        hash2 = service.hash_password(password)

        # Different salts mean different hashes
        assert hash1 != hash2

    def test_verify_password_correct(self, service: PasswordService):
        """verify_password returns True for correct password."""
        password = "MySecurePass123!"
        hash_result = service.hash_password(password)

        assert service.verify_password(password, hash_result) is True

    def test_verify_password_incorrect(self, service: PasswordService):
        """verify_password returns False for wrong password."""
        hash_result = service.hash_password("CorrectPassword123")

        assert service.verify_password("WrongPassword123", hash_result) is False

    def test_verify_password_invalid_hash_format(self, service: PasswordService):
        """verify_password returns False for invalid hash format."""
        assert service.verify_password("password", "invalid_hash") is False

    def test_verify_password_empty_hash(self, service: PasswordService):
        """verify_password returns False for empty hash."""
        assert service.verify_password("password", "") is False

    def test_verify_password_empty_password(self, service: PasswordService):
        """verify_password works with empty password (hashed)."""
        hash_result = service.hash_password("")
        assert service.verify_password("", hash_result) is True
        assert service.verify_password("notempty", hash_result) is False


@pytest.mark.business_logic
class TestPasswordValidation:
    """Tests for password strength validation."""

    @pytest.fixture
    def service(self):
        return PasswordService()

    @pytest.mark.parametrize(
        "password,expected_valid,reason",
        [
            # Length checks
            ("short", False, "too short (less than 8 chars)"),
            ("" + "a" * 129, False, "too long (over 128 chars)"),
            # Complexity requirement: must have at least one of uppercase, digit, or special
            # All lowercase, no digit/special = FAIL
            ("alllowercase", False, "lowercase only - no complexity"),
            ("a" * 128, False, "max length lowercase only - no complexity"),
            # Has uppercase = PASS
            ("ALLUPPERCASE", True, "has uppercase"),
            ("A" * 128, True, "max length with uppercase"),
            ("Password", True, "has uppercase"),
            # Has digit = PASS
            ("12345678", True, "has digits"),
            ("password1", True, "has digit"),
            ("pass word1", True, "has digit with space"),
            # Has special char = PASS
            ("password!", True, "has special character"),
            # Multiple complexity factors = PASS
            ("Password1", True, "has uppercase and digit"),
            ("PASSWORD1", True, "has uppercase and digit"),
        ],
    )
    def test_validate_strength(self, service: PasswordService, password: str, expected_valid: bool, reason: str):
        """validate_strength checks length and complexity requirements."""
        is_valid, error_msg = service.validate_strength(password)
        assert is_valid == expected_valid, f"Failed for: {reason}"

    def test_validate_strength_returns_error_message_on_invalid(self, service: PasswordService):
        """validate_strength returns descriptive error message."""
        is_valid, error_msg = service.validate_strength("short")
        assert is_valid is False
        assert error_msg is not None
        assert "8 characters" in error_msg

    def test_validate_strength_returns_none_on_valid(self, service: PasswordService):
        """validate_strength returns None error_msg for valid password."""
        is_valid, error_msg = service.validate_strength("ValidPass123!")
        assert is_valid is True
        assert error_msg is None


@pytest.mark.business_logic
class TestVerificationCodeGeneration:
    """Tests for verification code generation."""

    @pytest.fixture
    def service(self):
        return PasswordService()

    def test_generate_verification_code_is_6_digits(self, service: PasswordService):
        """generate_verification_code returns 6-digit string."""
        code = service.generate_verification_code()

        assert len(code) == 6
        assert code.isdigit()

    def test_generate_verification_code_pads_with_zeros(self, service: PasswordService):
        """generate_verification_code pads with leading zeros."""
        # Generate many codes - some should have leading zeros
        codes = [service.generate_verification_code() for _ in range(1000)]

        # All codes should be exactly 6 chars
        assert all(len(c) == 6 for c in codes)
        # All codes should be numeric
        assert all(c.isdigit() for c in codes)

    def test_generate_verification_code_randomness(self, service: PasswordService):
        """generate_verification_code produces sufficiently random codes."""
        # Generate 100 codes - with 1M possibilities, all should be unique
        codes = {service.generate_verification_code() for _ in range(100)}

        # All codes should be unique (extremely unlikely to have collisions)
        assert len(codes) == 100

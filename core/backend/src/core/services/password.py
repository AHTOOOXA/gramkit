"""Password hashing and validation service."""

import secrets

from passlib.hash import argon2

from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


class PasswordService:
    """Service for password hashing and validation."""

    # Password requirements
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    def __init__(self):
        self._hasher = argon2.using(memory_cost=65536, time_cost=3, parallelism=4)

    def hash_password(self, password: str) -> str:
        """
        Hash a password using Argon2.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return self._hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against a hash.

        Uses constant-time comparison to prevent timing attacks.

        Args:
            password: Plain text password to verify
            password_hash: Stored Argon2 hash

        Returns:
            True if password matches, False otherwise
        """
        try:
            return self._hasher.verify(password, password_hash)
        except (ValueError, TypeError) as e:
            logger.warning(f"Password verification failed: {e}")
            return False

    def validate_strength(self, password: str) -> tuple[bool, str | None]:
        """
        Validate password meets complexity requirements.

        Requirements:
        - 8-128 characters
        - Contains at least one of: uppercase, digit, or special character

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if len(password) < self.MIN_LENGTH:
            return False, f"Password must be at least {self.MIN_LENGTH} characters"

        if len(password) > self.MAX_LENGTH:
            return False, f"Password must be at most {self.MAX_LENGTH} characters"

        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in self.SPECIAL_CHARS for c in password)

        if not (has_upper or has_digit or has_special):
            return False, "Password must contain at least one uppercase letter, number, or special character"

        return True, None

    def generate_verification_code(self) -> str:
        """
        Generate a 6-digit verification code.

        Uses cryptographically secure random number generation.

        Returns:
            6-digit string code (e.g., "123456")
        """
        # Generate random number 0-999999, format with leading zeros
        code = secrets.randbelow(1000000)
        return f"{code:06d}"


# Singleton instance for convenience
password_service = PasswordService()

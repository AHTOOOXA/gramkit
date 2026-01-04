"""Core exceptions for TMA platform."""


class UserNotFoundException(Exception):
    """Raised when a user is not found in the database."""

    pass


class PaymentException(Exception):
    """Base exception for payment-related errors."""

    pass


class SubscriptionException(Exception):
    """Base exception for subscription-related errors."""

    pass

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


class PaymentNotFoundException(PaymentException):
    """Raised when a payment is not found in the database."""

    pass


class RefundNotAllowedException(PaymentException):
    """Raised when a payment can't be refunded here (wrong status or provider)."""

    pass


class AdminTaskNotFoundException(Exception):
    """Raised when no admin task is registered under the requested name."""

    pass


class BroadcastException(Exception):
    """Base exception for admin broadcast errors."""

    pass


class BroadcastNotFoundException(BroadcastException):
    """Raised when a promotional broadcast row doesn't exist."""

    pass


class InvalidBroadcastException(BroadcastException):
    """Raised when broadcast content or a request about it is invalid (the message is user-facing)."""

    pass


class MarketingLinkException(Exception):
    """Base exception for admin marketing-link errors."""

    pass


class MarketingLinkNotFoundException(MarketingLinkException):
    """Raised when a marketing link row doesn't exist."""

    pass


class MarketingCodeNotAllowedException(MarketingLinkException):
    """Raised when a code can't be registered: already registered, or one of the app's own codes."""

    pass

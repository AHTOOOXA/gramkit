from enum import StrEnum


class AuthMethod(StrEnum):
    """Authentication method used for login."""

    TELEGRAM = "telegram"
    EMAIL = "email"


class PaymentProvider(StrEnum):
    YOOKASSA = "YOOKASSA"
    TELEGRAM_STARS = "TELEGRAM_STARS"
    GIFT = "GIFT"
    # add other providers as needed


class PaymentStatus(StrEnum):
    CREATED = "CREATED"
    WAITING_FOR_ACTION = "WAITING_FOR_ACTION"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"

    @property
    def is_final(self) -> bool:
        """Check if this is a final payment state that should not be overwritten."""
        return self in {self.SUCCEEDED, self.FAILED, self.CANCELED}


class PaymentEventType(StrEnum):
    PAYMENT_CREATED = "PAYMENT_CREATED"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PROVIDER_RESPONSE = "PROVIDER_RESPONSE"
    PAYMENT_SUCCEEDED = "PAYMENT_SUCCEEDED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_CANCELED = "PAYMENT_CANCELED"


class SubscriptionStatus(StrEnum):
    NONE = "NONE"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class NotificationTimeSlot(StrEnum):
    MORNING = "MORNING"
    EVENING = "EVENING"


class UserType(StrEnum):
    GUEST = "GUEST"
    REGISTERED = "REGISTERED"


class UserRole(StrEnum):
    """User role for authorization (what they can do)."""

    USER = "user"
    ADMIN = "admin"
    OWNER = "owner"


class SpreadType(StrEnum):
    DAILY = "DAILY"
    SINGLE_CARD = "SINGLE_CARD"
    THREE_CARD = "THREE_CARD"
    YES_NO = "YES_NO"
    LOVE = "LOVE"
    A_OR_B = "A_OR_B"
    FINANCIAL = "FINANCIAL"
    DESTINY = "DESTINY"

    # New spread types
    EDUCATION = "EDUCATION"
    EX_PARTNER = "EX_PARTNER"
    DISAPPEARANCE = "DISAPPEARANCE"
    WAIT_OR_RELEASE = "WAIT_OR_RELEASE"
    SITUATION = "SITUATION"
    CAREER_CROSSROADS = "CAREER_CROSSROADS"
    TALENT = "TALENT"
    SELF_DISCOVERY = "SELF_DISCOVERY"

    OB_DAILY = "OB_DAILY"
    OB_THREE_CARD = "OB_THREE_CARD"

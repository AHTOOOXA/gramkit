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
    REFUNDED = "REFUNDED"  # fully refunded after SUCCEEDED (the only transition out of a final state)

    @property
    def is_final(self) -> bool:
        """Check if this is a final payment state that should not be overwritten."""
        return self in {self.SUCCEEDED, self.FAILED, self.CANCELED, self.REFUNDED}


class PaymentEventType(StrEnum):
    PAYMENT_CREATED = "PAYMENT_CREATED"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PROVIDER_RESPONSE = "PROVIDER_RESPONSE"
    PAYMENT_SUCCEEDED = "PAYMENT_SUCCEEDED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_CANCELED = "PAYMENT_CANCELED"
    PAYMENT_REFUNDED = "PAYMENT_REFUNDED"


class SubscriptionStatus(StrEnum):
    NONE = "NONE"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"  # renewal failing, in grace — still entitled, retried daily by dunning
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class NotificationTimeSlot(StrEnum):
    MORNING = "MORNING"
    EVENING = "EVENING"


class NotificationSlot(StrEnum):
    """When a logged notification went out (`notification_deliveries.slot`)."""

    MORNING = "morning"
    EVENING = "evening"
    OTHER = "other"


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

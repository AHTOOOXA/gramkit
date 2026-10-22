from abc import ABC, abstractmethod
from typing import Any

from core.infrastructure.database.models.enums import PaymentEventType, PaymentStatus
from core.infrastructure.database.models.payments import Payment


class PurchaseLimitError(Exception):
    """The user has already bought the product's daily limit (``daily_purchase_limit``) in 24 h."""


class ProviderRefundError(Exception):
    """The payment provider refused or failed the refund call (nothing was refunded)."""


class PaymentProviderInterface(ABC):
    @abstractmethod
    async def create_payment(
        self, payment: Payment, return_url: str | None = None, locale: str | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Create a payment with the provider

        Args:
            payment: The payment record from the database
            return_url: Optional URL to redirect to after payment
            locale: Optional app i18n locale ('ru'/'en') for provider UI language

        Returns:
            Tuple containing (payment_updates, return_data)
        """
        pass

    @abstractmethod
    async def process_callback(
        self, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], PaymentEventType, Payment, dict[str, Any]]:
        """
        Process a callback from the payment provider

        Args:
            payload: The callback payload from the provider

        Returns:
            Tuple containing (update_data, event_type, payment, recurring_details)
        """
        pass

    @abstractmethod
    async def charge_recurring(
        self, payment: Payment, recurring_details: dict
    ) -> tuple[dict[str, Any], PaymentEventType, Payment, dict[str, Any]]:
        """
        Charge a recurring payment

        Args:
            payment: The payment record from the database
            recurring_details: Details needed for recurring payments

        Returns:
            Tuple containing (update_data, event_type, payment, recurring_details)
        """
        pass

    async def get_payment_status(self, payment: Payment) -> tuple[PaymentStatus, dict[str, Any]]:
        """Default: return the stored status + no recurring details (no live reconcile).

        YooKassa overrides this to reconcile live and surface recurring details so the
        reconcile path can grant entitlement just like the webhook.
        """
        return payment.status, {}

    async def cancel(self, subscription: Any) -> None:
        """Stop future provider-driven renewals for ``subscription``.

        Default: no-op. YooKassa renewals are driven by OUR own dunning cron (which only selects
        ACTIVE/PAST_DUE subs), so marking the subscription CANCELED in our DB already stops them —
        there is nothing to tell YooKassa. Telegram Stars overrides this: Telegram auto-debits on
        its own schedule, so we must call editUserStarSubscription(is_canceled=True) or it keeps
        charging a "canceled" user.
        """
        return None

    # Whether refund() is implemented (PaymentsService.refund_payment checks before writing anything).
    supports_refund: bool = False

    async def refund(self, payment: Payment) -> None:
        """Return a succeeded payment's money to the user. Raises on failure.

        Default: not supported. YooKassa refunds are made by hand in its dashboard and arrive as
        refund.* webhooks. Telegram Stars overrides this with refundStarPayment.
        """
        raise NotImplementedError(f"Refunds are not supported for provider {payment.provider_id}")

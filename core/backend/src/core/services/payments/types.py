from abc import ABC, abstractmethod
from typing import Any

from core.infrastructure.database.models.enums import PaymentEventType
from core.infrastructure.database.models.payments import Payment


class PaymentProviderInterface(ABC):
    @abstractmethod
    async def create_payment(
        self, payment: Payment, return_url: str | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Create a payment with the provider

        Args:
            payment: The payment record from the database
            return_url: Optional URL to redirect to after payment

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

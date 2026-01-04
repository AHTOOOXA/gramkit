from typing import Any

from yookassa import Configuration
from yookassa import Payment as YooKassaPayment
from yookassa.domain.common.confirmation_type import ConfirmationType
from yookassa.domain.models.receipt import Receipt, ReceiptItem
from yookassa.domain.notification import WebhookNotificationFactory
from yookassa.domain.request.payment_request_builder import PaymentRequestBuilder

from core.domain.products import ProductCatalog
from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import PaymentEventType, PaymentStatus
from core.infrastructure.database.models.payments import Payment
from core.infrastructure.logging import get_logger
from core.services.payments.types import PaymentProviderInterface

logger = get_logger(__name__)


class YooKassaProvider(PaymentProviderInterface):
    def __init__(self, repo, services, products: ProductCatalog):
        """Initialize YooKassa provider.

        Uses settings.payment for configuration.
        """
        self.repo = repo
        self.services = services
        self.products = products
        Configuration.account_id = settings.payment.shop_id
        Configuration.secret_key = settings.payment.secret_key

    def _build_receipt(self, payment: Payment) -> tuple[float, str, Receipt]:
        """
        Build a receipt for YooKassa payment

        Args:
            payment: The payment record

        Returns:
            Tuple of amount, currency, and receipt
        """
        product = self.products.get_product(payment.product_id)
        if not product:
            raise ValueError(f"Product {payment.product_id} not found")

        price_info = product.get_price_for(payment.currency)
        receipt = Receipt()
        receipt.customer = {"email": settings.payment.receipt_email}
        receipt.items = [
            ReceiptItem(
                {
                    "description": product.name,
                    "quantity": 1,
                    "amount": {"value": str(price_info.amount), "currency": payment.currency},
                    "vat_code": 1,
                }
            )
        ]
        return price_info.amount, price_info.currency, receipt

    def _build_payment_request(
        self,
        payment: Payment,
        *,
        return_url: str | None = None,
        description_prefix: str = "",
        payment_method_id: str | None = None,
    ) -> PaymentRequestBuilder:
        """
        Build a payment request for YooKassa

        Args:
            payment: The payment record
            return_url: URL to redirect after payment
            description_prefix: Prefix for payment description
            payment_method_id: ID of saved payment method for recurring payments

        Returns:
            Built payment request
        """
        # Get product info
        product = self.products.get_product(payment.product_id)
        if not product:
            raise ValueError(f"Product {payment.product_id} not found")

        # Build price info and receipt internally
        amount, currency, receipt = self._build_receipt(payment)

        builder = PaymentRequestBuilder()
        builder.set_amount({"value": str(amount), "currency": currency})
        builder.set_capture(True)
        builder.set_receipt(receipt)
        is_recurring = product.recurring
        builder.set_metadata({"app_payment_id": str(payment.id), "is_recurring": is_recurring})
        builder.set_description(f"{description_prefix}{product.name} for user_id: {payment.user_id}")
        if payment_method_id:
            builder.set_payment_method_id(payment_method_id)
        else:
            if return_url:
                builder.set_confirmation({"type": ConfirmationType.REDIRECT, "return_url": return_url})
            if is_recurring:
                builder.set_save_payment_method(True)
        return builder.build()

    async def create_payment(
        self, payment: Payment, return_url: str | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Create a payment with YooKassa

        Args:
            payment: The payment record
            return_url: URL to redirect after payment

        Returns:
            Tuple of payment updates and return data
        """
        product = self.products.get_product(payment.product_id)
        if not product:
            raise ValueError(f"Product {payment.product_id} not found")

        request = self._build_payment_request(payment, return_url=return_url)
        logger.info(f"Creating payment for product {product.product_id} for user {payment.user_id}")
        response = YooKassaPayment.create(request)
        logger.info(f"Provider payment created with id: {response.id}")

        payment_updates = {
            "status": PaymentStatus.WAITING_FOR_ACTION,
            "provider_payment_id": response.id,
            "provider_metadata": response.metadata,
        }

        price_info = product.get_price_for(payment.currency)

        return_data = {
            "payment_id": response.id,
            "confirmation_url": response.confirmation.confirmation_url,
            "amount": price_info.amount,
            "currency": price_info.currency,
        }

        return payment_updates, return_data

    async def process_callback(
        self, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], PaymentEventType, Payment, dict[str, Any]]:
        """
        Process a callback from YooKassa

        Args:
            payload: The callback payload

        Returns:
            Tuple of update data, event type, payment, and recurring details
        """
        try:
            notification = WebhookNotificationFactory().create(payload)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {}, None, None, None

        if not notification:
            logger.error("Invalid notification received")
            return {}, None, None, None

        app_payment_id = notification.object.metadata.get("app_payment_id")
        is_recurring = notification.object.metadata.get("is_recurring", False) == "true"
        if not app_payment_id:
            logger.error("Missing app_payment_id in notification metadata")
            return {}, None, None, None

        payment = await self.repo.payments.get_by_id(app_payment_id)
        if not payment:
            logger.error(f"Payment not found for app_payment_id: {app_payment_id}")
            return {}, None, None, None

        if notification.event == "payment.succeeded":
            new_status = PaymentStatus.SUCCEEDED
            event_type = PaymentEventType.PAYMENT_SUCCEEDED
            recurring_details = {}
            if notification.object.payment_method and notification.object.payment_method.id:
                recurring_details["payment_method_id"] = notification.object.payment_method.id
        elif notification.event == "payment.waiting_for_capture":
            new_status = PaymentStatus.WAITING_FOR_ACTION
            event_type = PaymentEventType.PROVIDER_RESPONSE
            recurring_details = {}
        elif notification.event == "payment.canceled":
            new_status = PaymentStatus.CANCELED
            event_type = PaymentEventType.PAYMENT_CANCELED
            recurring_details = {}
        else:
            new_status = payment.status
            event_type = PaymentEventType.PROVIDER_RESPONSE
            recurring_details = {}

        logger.info(f"Processed callback event for payment {payment.id}")
        update_data = {
            "status": new_status,
            "provider_metadata": getattr(notification, "to_dict", lambda: payload)(),
            "is_recurring": is_recurring,
        }
        return update_data, event_type, payment, recurring_details

    async def charge_recurring(
        self, payment: Payment, recurring_details: dict
    ) -> tuple[dict[str, Any], PaymentEventType, Payment, dict[str, Any]]:
        """
        Charge a recurring payment with YooKassa

        Args:
            payment: The payment record
            recurring_details: Details needed for recurring payment

        Returns:
            Tuple of update data, event type, payment, and recurring details
        """
        if not recurring_details.get("payment_method_id"):
            logger.error(f"No payment method id for payment {payment.id}")
            return None, None, None, None

        product = self.products.get_product(payment.product_id)
        if not product:
            raise ValueError(f"Product {payment.product_id} not found")

        logger.info(f"Initiating recurring charge for payment {payment.id}")
        request = self._build_payment_request(
            payment,
            return_url=None,
            description_prefix="Auto-renewal: ",
            payment_method_id=recurring_details["payment_method_id"],
        )
        response = YooKassaPayment.create(request)
        logger.info(
            f"Recurring charge response for payment {payment.id}: status {response.status}, provider id {response.id}"
        )

        if response.status == "succeeded":
            new_status = PaymentStatus.SUCCEEDED
            event_type = PaymentEventType.PAYMENT_SUCCEEDED
        else:
            new_status = PaymentStatus.FAILED
            event_type = PaymentEventType.PAYMENT_FAILED

        update_data = {
            "status": new_status,
            "provider_payment_id": response.id,
            "provider_metadata": response.metadata,
            "is_recurring": True,
        }
        recurring_details = {}

        return update_data, event_type, payment, recurring_details

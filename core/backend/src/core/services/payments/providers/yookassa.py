import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from yookassa import Configuration
from yookassa import Payment as YooKassaPayment
from yookassa import Refund as YooKassaRefund
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

_YOOKASSA_LOCALES = {"ru": "ru_RU", "en": "en_US"}


def _payment_details(remote: Any) -> dict[str, str]:
    """How the payment was made or why it was canceled, for analytics: payment_method_type
    (bank_card, sbp, ...), cancellation_reason (insufficient_funds, 3d_secure_failed, ...) and
    cancellation_party (payment_network, yoo_money, merchant)."""
    method = getattr(remote, "payment_method", None)
    cancellation = getattr(remote, "cancellation_details", None)
    details = {
        "payment_method_type": getattr(method, "type", None),
        "cancellation_reason": getattr(cancellation, "reason", None),
        "cancellation_party": getattr(cancellation, "party", None),
    }
    return {key: str(value) for key, value in details.items() if value}


def _to_yookassa_locale(locale: str | None) -> str | None:
    """Map an app i18n locale ('ru'/'en', maybe 'ru-RU') to a YooKassa widget locale, or None to auto-detect."""
    if not locale:
        return None
    return _YOOKASSA_LOCALES.get(locale.lower().split("-")[0])


def renewal_idempotency_key(subscription_id: UUID, end_date: datetime) -> str:
    """Deterministic idempotency key for a renewal charge, stable for one billing period.

    A re-fired renewal for the same (subscription, period) reuses this key, so YooKassa
    dedups the create() call. NOTE: YooKassa's Idempotence-Key window only holds ~24h, so
    this is a best-effort backstop — the primary double-charge guards are the SUCCEEDED-only
    dedup query, the uq_payment_idempotency_key index, and was_rewarded gating. ``end_date``
    must be tz-aware (the column is TIMESTAMP(timezone=True)) so the isoformat is stable.
    """
    raw = f"renewal:{subscription_id}:{end_date.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


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
        locale: str | None = None,
    ) -> PaymentRequestBuilder:
        """
        Build a payment request for YooKassa

        Args:
            payment: The payment record
            return_url: URL to redirect after payment
            description_prefix: Prefix for payment description
            payment_method_id: ID of saved payment method for recurring payments
            locale: App i18n locale ('ru'/'en') for the embedded widget language

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
            confirmation = {"type": ConfirmationType.EMBEDDED}
            yk_locale = _to_yookassa_locale(locale)
            if yk_locale:
                confirmation["locale"] = yk_locale
            builder.set_confirmation(confirmation)
            if is_recurring:
                builder.set_save_payment_method(True)
        return builder.build()

    async def create_payment(
        self, payment: Payment, return_url: str | None = None, locale: str | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Create a payment with YooKassa

        Args:
            payment: The payment record
            return_url: URL to redirect after payment
            locale: App i18n locale ('ru'/'en') for the embedded widget language

        Returns:
            Tuple of payment updates and return data
        """
        product = self.products.get_product(payment.product_id)
        if not product:
            raise ValueError(f"Product {payment.product_id} not found")

        request = self._build_payment_request(payment, return_url=return_url, locale=locale)
        logger.info(f"Creating payment for product {product.product_id} for user {payment.user_id}")
        response = YooKassaPayment.create(request, payment.idempotency_key)
        logger.info(f"Provider payment created with id: {response.id}")

        payment_updates = {
            "status": PaymentStatus.WAITING_FOR_ACTION,
            "provider_payment_id": response.id,
            "provider_metadata": response.metadata,
        }

        price_info = product.get_price_for(payment.currency)

        return_data = {
            "payment_id": str(payment.id),
            "confirmation_token": response.confirmation.confirmation_token,
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

        # A refund.* body carries a refund object (id, payment_id, amount), not a payment.
        if str(payload.get("event", "")).startswith("refund."):
            return await self._process_refund_callback(notification)

        # SECURITY: never trust the webhook body. YooKassa does not sign notifications, so a
        # forged "payment.succeeded" body must not be able to grant a subscription. Re-fetch the
        # authoritative payment object and drive every decision off its real status, not the body.
        try:
            remote = YooKassaPayment.find_one(notification.object.id)
        except Exception as e:
            # Transient YooKassa failure during webhook delivery: do NOT act on the (untrusted)
            # body. The locked payment stays non-final; a later webhook / reconciliation resolves it.
            logger.error(f"Failed to re-fetch payment {notification.object.id} from YooKassa: {e}")
            return {}, None, None, None

        if not remote:
            logger.error(f"Re-fetch returned no payment for {notification.object.id}")
            return {}, None, None, None

        remote_metadata = remote.metadata or {}
        app_payment_id = remote_metadata.get("app_payment_id")
        if not app_payment_id:
            logger.error("Missing app_payment_id in re-fetched payment metadata")
            return {}, None, None, None

        payment = await self.repo.payments.get_by_id(app_payment_id)
        if not payment:
            logger.error(f"Payment not found for app_payment_id: {app_payment_id}")
            return {}, None, None, None

        recurring_details = {}
        if remote.status == "succeeded":
            new_status = PaymentStatus.SUCCEEDED
            event_type = PaymentEventType.PAYMENT_SUCCEEDED
            # Prefer the re-fetched payment_method; fall back to the notification body so a
            # first-time saved card still yields a recurring token. Warn only if both are empty
            # on a recurring product (its renewals would otherwise silently fail).
            pm = getattr(remote, "payment_method", None) or getattr(notification.object, "payment_method", None)
            if pm and getattr(pm, "id", None):
                recurring_details["payment_method_id"] = pm.id
            else:
                product = self.products.get_product(payment.product_id)
                if product and product.recurring:
                    logger.warning(
                        f"Succeeded payment {remote.id} has no payment_method id; recurring renewal will fail"
                    )
            recurring_details.update(_payment_details(remote))
        elif remote.status == "canceled":
            new_status = PaymentStatus.CANCELED
            event_type = PaymentEventType.PAYMENT_CANCELED
            recurring_details = _payment_details(remote)  # why it was canceled, for analytics
        elif remote.status == "waiting_for_capture":
            new_status = PaymentStatus.WAITING_FOR_ACTION
            event_type = PaymentEventType.PROVIDER_RESPONSE
        else:
            # pending / unknown — leave the payment as-is; a later event resolves it.
            new_status = payment.status
            event_type = PaymentEventType.PROVIDER_RESPONSE

        logger.info(f"Processed callback for payment {payment.id}: authoritative remote status {remote.status}")
        update_data = {
            "status": new_status,
            "provider_metadata": {
                "webhook": payload,
                "remote_status": remote.status,
                "provider_payment_id": remote.id,
            },
            # No is_recurring here: it's set when the payment row is created (a renewal by the
            # renewal job, a purchase by the user). The metadata "is_recurring" is "save the card
            # for renewals", true on first purchases too — it used to overwrite the flag.
        }
        return update_data, event_type, payment, recurring_details

    async def _process_refund_callback(
        self, notification: Any
    ) -> tuple[dict[str, Any], PaymentEventType | None, Payment | None, dict[str, Any]]:
        """A refund of one of our payments. Refunds are made by hand in the YooKassa dashboard.

        Same rule as payments: the body isn't signed, so the refund is re-fetched and only the
        authoritative object is acted on. A succeeded refund of the full amount marks the payment
        REFUNDED (out of revenue); a partial one is recorded but keeps it SUCCEEDED. Subscriptions
        are not touched — whoever refunded decides about access.
        """
        try:
            refund = YooKassaRefund.find_one(notification.object.id)
        except Exception as e:
            logger.error(f"Failed to re-fetch refund {notification.object.id} from YooKassa: {e}")
            return {}, None, None, None
        if not refund:
            logger.error(f"Re-fetch returned no refund for {notification.object.id}")
            return {}, None, None, None

        payment = await self.repo.payments.get_by_provider_payment_id(refund.payment_id)
        if not payment:
            logger.error(f"Refund {refund.id} is for unknown payment {refund.payment_id}")
            return {}, None, None, None

        refunded = float(refund.amount.value)
        refund_info = {
            "id": refund.id,
            "status": refund.status,
            "amount": refunded,
            "currency": refund.amount.currency,
            "description": getattr(refund, "description", None),
        }
        provider_metadata = {**(payment.provider_metadata or {}), "refund": refund_info}
        if refund.status != "succeeded":
            return {"provider_metadata": provider_metadata}, PaymentEventType.PROVIDER_RESPONSE, payment, {}
        if refunded < payment.amount:
            logger.warning(f"Partial refund {refund.id} of payment {payment.id}: {refunded} of {payment.amount}")
            return {"provider_metadata": provider_metadata}, PaymentEventType.PROVIDER_RESPONSE, payment, {}
        return (
            {"status": PaymentStatus.REFUNDED, "provider_metadata": provider_metadata},
            PaymentEventType.PAYMENT_REFUNDED,
            payment,
            {},
        )

    async def get_payment_status(self, payment: Payment) -> tuple[PaymentStatus, dict[str, Any]]:
        """Reconcile live status from YooKassa via find_one. Falls back to stored status.

        On a SUCCEEDED reconcile, also surface ``recurring_details`` (the saved
        payment_method_id) the SAME way ``process_callback`` does, so the reconcile path can
        grant entitlement — including a future-renewable subscription — exactly like the webhook.
        """
        if not payment.provider_payment_id:
            return payment.status, {}
        try:
            remote = YooKassaPayment.find_one(payment.provider_payment_id)
        except Exception as e:
            logger.error(f"Error fetching payment status from YooKassa for {payment.id}: {e}")
            return payment.status, {}
        if not remote:
            return payment.status, {}
        status_map = {
            "succeeded": PaymentStatus.SUCCEEDED,
            "canceled": PaymentStatus.CANCELED,
            "waiting_for_capture": PaymentStatus.WAITING_FOR_ACTION,
            "pending": PaymentStatus.WAITING_FOR_ACTION,
        }
        mapped = status_map.get(remote.status)
        if mapped is None:
            logger.warning(f"Unknown YooKassa status '{remote.status}' for payment {payment.id}")
            return payment.status, {}
        if mapped == PaymentStatus.CANCELED:
            return mapped, _payment_details(remote)  # why it was canceled, for analytics
        if mapped != PaymentStatus.SUCCEEDED:
            return mapped, {}
        recurring_details: dict[str, Any] = _payment_details(remote)
        pm = getattr(remote, "payment_method", None)
        if pm and getattr(pm, "id", None):
            recurring_details["payment_method_id"] = pm.id
        else:
            product = self.products.get_product(payment.product_id)
            if product and product.recurring:
                logger.warning(
                    f"Succeeded payment {remote.id} (reconcile) has no payment_method id; recurring renewal will fail"
                )
        return mapped, recurring_details

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
        response = YooKassaPayment.create(request, recurring_details.get("idempotency_key"))
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

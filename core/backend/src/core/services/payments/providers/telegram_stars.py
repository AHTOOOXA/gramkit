from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from aiogram.types import LabeledPrice

from core.domain.products import ProductCatalog
from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import PaymentEventType, PaymentStatus
from core.infrastructure.database.models.payments import Payment
from core.infrastructure.logging import get_logger
from core.services.payments.types import PaymentProviderInterface

logger = get_logger(__name__)


class TelegramStarsProvider(PaymentProviderInterface):
    def __init__(self, repo, services, products: ProductCatalog):
        """Initialize Telegram Stars provider.

        Uses settings.bot for configuration.
        """
        self.repo = repo
        self.services = services
        self.products = products
        self.bot = Bot(token=settings.bot.token)

    async def create_payment(self, payment: Payment, return_url: str = None) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Create a Telegram Stars payment invoice

        Args:
            payment: The payment record from the database
            return_url: Optional URL to redirect to after payment (used for Web App)

        Returns:
            Tuple containing (payment_updates, return_data)
        """
        try:
            # Create invoice for Telegram Stars
            # For Telegram Stars, the amount should be in stars (integer)
            stars_amount = int(payment.amount)

            # Get product details for description
            product = self.products.get_product(payment.product_id)

            title = f"{product.name}" if product else f"Product {payment.product_id}"
            description = f"Purchase of {title}"
            if product and product.recurring:
                description += f" - Auto-renewing every {product.duration_days} days"

            # Create invoice with subscription support
            invoice_params = {
                "title": title,
                "description": description,
                "payload": f"payment_{payment.id}",  # Custom payload to identify the payment
                "currency": "XTR",  # Telegram Stars currency
                "prices": [LabeledPrice(label=title, amount=stars_amount)],
                "is_flexible": False,
                "need_name": False,
                "need_phone_number": False,
                "need_email": False,
                "need_shipping_address": False,
                "send_phone_number_to_provider": False,
                "send_email_to_provider": False,
                "provider_token": "",  # Empty for Telegram Stars
            }

            # Add recurring subscription parameters if this is a subscription
            if product and product.recurring:
                # Telegram Stars subscriptions are always monthly (30 days = 2592000 seconds)
                invoice_params.update(
                    {
                        "subscription_period": 2592000,  # 30 days in seconds (Telegram Stars constraint)
                    }
                )
                logger.info(f"Creating Telegram Stars subscription invoice for payment {payment.id} with 30-day period")

            invoice_link = await self.bot.create_invoice_link(**invoice_params)

            logger.info(f"Created Telegram Stars invoice for payment {payment.id}: {invoice_link}")

            # Update payment record
            payment_updates = {
                "status": PaymentStatus.WAITING_FOR_ACTION,
                "provider_payment_id": f"tg_stars_{payment.id}",
                "provider_metadata": {
                    "invoice_link": invoice_link,
                    "stars_amount": stars_amount,
                    "title": title,
                    "description": description,
                },
            }

            # Return data for the frontend
            return_data = {
                "payment_id": str(payment.id),  # Convert UUID to string for JSON serialization
                "confirmation_url": invoice_link,
                "status": "pending",
                "provider": "TELEGRAM_STARS",
                "amount": stars_amount,
                "currency": "XTR",
            }

            return payment_updates, return_data

        except Exception as e:
            logger.error(f"Failed to create Telegram Stars payment for payment {payment.id}: {e}")
            payment_updates = {
                "status": PaymentStatus.FAILED,
                "provider_metadata": {"error": str(e)},
            }
            return_data = {
                "payment_id": str(payment.id),  # Convert UUID to string for JSON serialization
                "confirmation_url": "",  # Empty URL for failed payment
                "status": "failed",
                "provider": "TELEGRAM_STARS",
                "amount": float(payment.amount),  # Use payment amount from database
                "currency": payment.currency,  # Use payment currency from database
                "error": str(e),
            }
            return payment_updates, return_data

    async def process_callback(
        self, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], PaymentEventType, Payment, dict[str, Any]]:
        """
        Process a callback from Telegram Stars (pre_checkout or successful_payment)

        Args:
            payload: The callback payload from Telegram

        Returns:
            Tuple containing (update_data, event_type, payment, recurring_details)
        """
        try:
            # Extract payment ID from the payload
            # This will be handled by webhook when Telegram sends pre_checkout_query or successful_payment
            payment_id = None

            if "payload" in payload:
                # Extract payment ID from custom payload
                custom_payload = payload["payload"]
                if custom_payload.startswith("payment_"):
                    payment_id = custom_payload.replace("payment_", "")  # Keep as string (UUID)

            if not payment_id:
                logger.error(f"Could not extract payment ID from payload: {payload}")
                return {}, None, None, {}

            payment = await self.repo.payments.get_by_id(payment_id)
            if not payment:
                logger.error(f"Payment {payment_id} not found")
                return {}, None, None, {}

            # Determine event type based on the payload
            if payload.get("successful_payment"):
                # Payment succeeded - could be initial payment or renewal
                successful_payment = payload["successful_payment"]

                # Check if this is a renewal payment
                is_renewal = False
                if "recurring_used" in payload:
                    is_renewal = payload.get("recurring_used", False)
                elif successful_payment.get("recurring_used"):
                    is_renewal = True
                # Also check if this payment already has subscription data (indicates renewal)
                elif payment.subscription_id:
                    is_renewal = True

                event_type = PaymentEventType.PAYMENT_SUCCEEDED
                update_data = {
                    "status": PaymentStatus.SUCCEEDED,
                    "provider_metadata": {
                        **payment.provider_metadata,
                        "telegram_payment_charge_id": successful_payment.get("telegram_payment_charge_id"),
                        "provider_payment_charge_id": successful_payment.get("provider_payment_charge_id"),
                        "is_renewal": is_renewal,
                        "payment_processed_at": datetime.now(UTC).isoformat(),
                    },
                }

                # Handle recurring details for subscriptions
                recurring_details = {}
                if payment.product_id.endswith("_SUB") or "SUBSCRIPTION" in payment.product_id:
                    recurring_details = {
                        "telegram_payment_charge_id": successful_payment.get("telegram_payment_charge_id"),
                        "provider_payment_charge_id": successful_payment.get("provider_payment_charge_id"),
                        "is_renewal": is_renewal,
                        "telegram_subscription_managed": True,
                    }

                renewal_status = "renewal" if is_renewal else "initial payment"
                logger.info(f"Telegram Stars {renewal_status} {payment_id} succeeded")
                return update_data, event_type, payment, recurring_details

            elif payload.get("pre_checkout_query"):
                # Pre-checkout query - validate and approve
                event_type = PaymentEventType.PROVIDER_RESPONSE
                update_data = {
                    "provider_metadata": {
                        **payment.provider_metadata,
                        "pre_checkout_query_id": payload["pre_checkout_query"]["id"],
                    },
                }
                logger.info(f"Telegram Stars pre-checkout query for payment {payment_id}")
                return update_data, event_type, payment, {}

            else:
                logger.warning(f"Unknown Telegram Stars callback type: {payload}")
                return {}, None, payment, {}

        except Exception as e:
            logger.error(f"Error processing Telegram Stars callback: {e}")
            return {}, None, None, {}

    async def charge_recurring(
        self, payment: Payment, recurring_details: dict
    ) -> tuple[dict[str, Any], PaymentEventType, Payment, dict[str, Any]]:
        """
        Handle Telegram Stars recurring payment

        Note: Telegram Stars manages automatic recurring payments internally.
        This method doesn't perform actual charging - Telegram handles that automatically.
        Instead, we process the renewal notification when Telegram sends it via bot handlers.

        Args:
            payment: The payment record from the database
            recurring_details: Details needed for recurring payments

        Returns:
            Tuple containing (update_data, event_type, payment, recurring_details)
        """
        logger.info(
            f"Telegram Stars subscription renewal expected for payment {payment.id} - Telegram manages charging automatically"
        )

        # For Telegram Stars, we don't charge manually - Telegram handles renewals automatically
        # This method is called by the subscription service, but for Telegram Stars we just
        # acknowledge that renewal is expected and Telegram will handle it
        update_data = {
            "status": PaymentStatus.WAITING_FOR_ACTION,
            "provider_metadata": {
                **payment.provider_metadata,
                "renewal_expected": True,
                "telegram_managed": True,
                "note": "Telegram Stars subscription renewal is managed automatically by Telegram",
                "last_renewal_check": payment.created_at.isoformat() if payment.created_at else None,
            },
        }

        # Return SUCCESS event since Telegram will handle the actual renewal
        # The bot handlers will process the actual renewal notification when it comes
        logger.info(f"Telegram Stars subscription {payment.id} marked as awaiting automatic renewal by Telegram")

        return update_data, PaymentEventType.PROVIDER_RESPONSE, payment, recurring_details

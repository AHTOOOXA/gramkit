from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from core.domain.products import ProductCatalog
from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import (
    PaymentEventType,
    PaymentProvider,
    PaymentStatus,
)
from core.infrastructure.database.models.subscriptions import Subscription
from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.services.base import BaseService
from core.services.payments.providers import get_provider

logger = get_logger(__name__)


class PaymentsService(BaseService):
    def __init__(self, repo, producer, services, bot, products: ProductCatalog):
        """
        Initialize PaymentsService with app-specific product definitions.

        Uses settings.payment and settings.bot for configuration.

        Args:
            repo: Repository aggregator
            producer: Message queue producer
            services: Service aggregator
            bot: Telegram bot instance
            products: App-specific products catalog (must satisfy ProductCatalog protocol)
        """
        super().__init__(repo, producer, services, bot)

        # Inject app-specific product catalog (type-safe via Protocol)
        self.products = products

        self.providers = {
            PaymentProvider.YOOKASSA.value: get_provider(PaymentProvider.YOOKASSA, repo, services, products),
            PaymentProvider.TELEGRAM_STARS.value: get_provider(
                PaymentProvider.TELEGRAM_STARS, repo, services, products
            ),
            # Add more providers here as needed
        }

    async def _handle_success(self, payment: Any, recurring_details: Any, update_data: dict[str, Any]) -> None:
        """
        Handle a successful payment by rewarding the user

        Args:
            payment: The payment record
            recurring_details: Details for recurring payments
            update_data: Data to update the payment record with
        """
        product = self.products.get_product(payment.product_id)
        if product and not payment.was_rewarded:
            await product.reward(payment.user_id, payment, recurring_details, self.services.subscriptions)

            posthog.capture(
                distinct_id=str(payment.user_id),
                event="payment_succeeded",
                properties={
                    "user_id": str(payment.user_id),
                    "product_id": payment.product_id,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "is_recurring": payment.is_recurring,
                    "payment_id": str(payment.id),
                },
            )

            update_data["was_rewarded"] = True

    async def start_payment(
        self, user_id: UUID, product_id: str, currency: str, provider_id: PaymentProvider, return_url: str = None
    ) -> dict[str, Any]:
        """
        Start a payment process

        Args:
            user_id: The user making the payment
            product_id: The product being purchased
            currency: The currency for the payment
            provider_id: The payment provider to use
            return_url: URL to redirect to after payment

        Returns:
            Dict with payment details and confirmation URL
        """
        logger.info(
            f"Starting payment for user {user_id} product {product_id} currency {currency} provider {provider_id} return url {return_url}"
        )

        # Get product (includes test products in debug mode)
        product = self.products.get_product(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found or not available")

        payment = await self.repo.payments.create(
            {
                "user_id": user_id,
                "product_id": product_id,
                "provider_id": provider_id,
                "amount": product.get_price_for(currency).amount,
                "currency": currency,
                "status": PaymentStatus.CREATED,
                "provider_payment_id": None,
                "provider_metadata": {},
            }
        )
        logger.info(f"Payment record created with id: {payment.id}")

        posthog.capture(
            distinct_id=str(user_id),
            event="payment_record_created",
            properties={
                "user_id": str(user_id),
                "product_id": product_id,
                "currency": currency,
                "amount": product.get_price_for(currency).amount,
                "provider_id": provider_id,
                "payment_id": str(payment.id),
            },
        )

        await self.repo.payment_events.create(
            {
                "payment_id": payment.id,
                "provider_id": provider_id,
                "event_type": PaymentEventType.PAYMENT_CREATED,
                "timestamp": datetime.now(UTC),
                "raw_data": {
                    "user_id": str(user_id),
                    "provider_id": provider_id,
                    "product_id": product_id,
                    "currency": currency,
                    "amount": product.get_price_for(currency).amount,
                    "return_url": return_url,
                },
            }
        )

        provider = self.providers.get(provider_id)
        payment_updates, return_data = await provider.create_payment(payment, return_url=return_url)
        logger.info(f"Payment initiated with provider id: {return_data.get('payment_id')}")

        posthog.capture(
            distinct_id=str(user_id),
            event="payment_initiated",
            properties={
                "user_id": str(user_id),
                "product_id": product_id,
                "provider_id": provider_id,
                "return_data": return_data,
            },
        )

        await self.repo.payments.update(payment.id, payment_updates)
        await self.repo.payment_events.create(
            {
                "payment_id": payment.id,
                "provider_id": provider_id,
                "event_type": PaymentEventType.PAYMENT_INITIATED,
                "timestamp": datetime.now(UTC),
                "raw_data": {
                    "user_id": str(user_id),
                    "provider_id": provider_id,
                    "product_id": product_id,
                    "return_data": return_data,
                },
            }
        )

        return return_data

    async def process_callback(self, payload: dict[str, Any], provider_id: PaymentProvider) -> None:
        """
        Process a callback from a payment provider

        Args:
            payload: The callback payload
            provider_id: The payment provider that sent the callback
        """
        provider = self.providers.get(provider_id)
        if not provider:
            logger.error(f"Received callback for unknown provider: {provider_id}")
            return

        update_data, event_type, payment, recurring_details = await provider.process_callback(payload)

        if not payment or not event_type:
            logger.error("Provider callback processing failed, missing critical data")
            return

        logger.info(f"Processing callback for payment {payment.id} with event {event_type}")

        # Re-fetch payment with pessimistic lock to prevent race conditions
        # This ensures we check the CURRENT state and prevent concurrent webhooks
        # from overwriting final states
        locked_payment = await self.repo.payments.get_by_id_with_lock(payment.id)

        # State machine protection: Check if payment is already in a final state
        if locked_payment.status.is_final:
            logger.warning(
                f"Ignoring webhook for payment {payment.id} - "
                f"already in final state {locked_payment.status}. "
                f"Attempted transition from provider: {update_data.get('status', 'unknown')}"
            )
            # Still log the event for monitoring and debugging
            await self.repo.payment_events.create(
                {
                    "payment_id": payment.id,
                    "provider_id": provider_id,
                    "event_type": event_type,
                    "timestamp": datetime.now(UTC),
                    "raw_data": payload,
                }
            )
            return

        # Payment is not in final state and is locked - safe to update
        if event_type == PaymentEventType.PAYMENT_SUCCEEDED:
            await self._handle_success(locked_payment, recurring_details, update_data)

        await self.repo.payments.update(payment.id, update_data)
        await self.repo.payment_events.create(
            {
                "payment_id": payment.id,
                "provider_id": provider_id,
                "event_type": event_type,
                "timestamp": datetime.now(UTC),
                "raw_data": payload,
            }
        )

    async def charge_subscription(self, subscription: Subscription) -> None:
        """
        Charge a recurring subscription

        Args:
            subscription: The subscription to charge
        """
        provider = self.providers.get(subscription.provider_id.value)
        if not provider:
            logger.error(f"Provider {subscription.provider_id.value} not found")
            return

        logger.info(f"Charging subscription for subscription id {subscription.id} and user {subscription.user_id}")

        # Keep using existing product_id for recurring subscriptions
        product = self.products.get_product(subscription.product_id)

        payment = await self.repo.payments.create(
            {
                "user_id": subscription.user_id,
                "product_id": subscription.product_id,
                "provider_id": subscription.provider_id,
                "amount": product.get_price_for(subscription.currency).amount,
                "currency": subscription.currency,
                "status": PaymentStatus.CREATED,
                "is_recurring": True,
                "provider_payment_id": None,
                "provider_metadata": {},
            }
        )
        logger.info(f"Subscription payment record created with id: {payment.id}")
        await self.repo.payment_events.create(
            {
                "payment_id": payment.id,
                "provider_id": subscription.provider_id,
                "event_type": PaymentEventType.PAYMENT_CREATED,
                "timestamp": datetime.now(UTC),
                "raw_data": {"subscription_id": str(subscription.id)},
                "is_recurring": True,
            }
        )

        update_data, event_type, payment, recurring_details = await provider.charge_recurring(
            payment, subscription.recurring_details
        )
        logger.info(f"Recurring charge {event_type} for subscription payment {payment.id}")

        if not payment or not event_type:
            logger.error(f"Charge subscription failed, missing critical data {payment.id}")
            return

        if event_type == PaymentEventType.PAYMENT_SUCCEEDED:
            await self._handle_success(payment, recurring_details, update_data)

        await self.repo.payments.update(payment.id, update_data)
        await self.repo.payment_events.create(
            {
                "payment_id": payment.id,
                "provider_id": subscription.provider_id,
                "event_type": event_type,
                "timestamp": datetime.now(UTC),
                "raw_data": {"subscription_id": str(subscription.id)},
                "is_recurring": True,
            }
        )
        logger.info(f"Subscription payment update processed for subscription id {subscription.id}")

    def get_available_products(self, currency: str = "RUB") -> list[dict[str, Any]]:
        """
        Get a list of available products formatted for API responses

        Returns currently available products, and test products when in debug mode

        Args:
            currency: The currency to display prices in

        Returns:
            List of product dictionaries
        """
        products = self.products.AVAILABLE_PRODUCTS.copy()

        # Include test products in debug mode
        if settings.debug:
            products.update(self.products.TEST_PRODUCTS)

        return [
            {
                "id": p.product_id,
                "name": p.name,
                "price": p.get_price_for(currency).amount,
                "currency": p.get_price_for(currency).currency,
                "duration_days": p.duration_days,
                "recurring": p.recurring,
            }
            for p in products.values()
        ]

    async def get_available_products_async(self, user_id: UUID = None, currency: str = "RUB") -> list[dict[str, Any]]:
        """
        Async version of get_available_products

        Returns currently available products, and test products when in debug mode

        Args:
            user_id: The user ID requesting products (unused, but kept for API compatibility)
            currency: The currency to display prices in

        Returns:
            List of product dictionaries
        """
        return self.get_available_products(currency)

    async def get_profile_products_async(self, user_id: UUID = None, currency: str = "RUB") -> list[dict[str, Any]]:
        """
        Get products for profile page (excludes test products)

        Args:
            user_id: The user ID requesting products (unused, but kept for API compatibility)
            currency: The currency to display prices in

        Returns:
            List of profile product dictionaries
        """
        return [
            {
                "id": p.product_id,
                "name": p.name,
                "price": p.get_price_for(currency).amount,
                "currency": p.get_price_for(currency).currency,
                "duration_days": p.duration_days,
                "recurring": p.recurring,
            }
            for p in self.products.CURRENT_OFFERS.values()
        ]

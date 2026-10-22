from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from core.domain.products import ProductCatalog, product_daily_purchase_limit, product_take_back
from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import (
    PaymentEventType,
    PaymentProvider,
    PaymentStatus,
    SubscriptionStatus,
)
from core.infrastructure.database.models.payments import Payment
from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.infrastructure.telegram.admin_messages import esc, fmt_money, tags, user_ref, user_tag
from core.services.base import BaseService
from core.services.payments.providers import get_provider
from core.services.payments.providers.telegram_stars import is_native_stars_subscription
from core.services.payments.types import ProviderRefundError, PurchaseLimitError

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
                    "provider_id": payment.provider_id,
                    "payment_method_type": _payment_method_type(payment, recurring_details),
                },
            )

            update_data["was_rewarded"] = True

    async def _handle_refund(self, payment: Any, access_note: str | None = None, user: Any = None) -> None:
        """Report a refunded payment. What was taken back is in ``access_note``; without one, nothing
        was (a YooKassa dashboard refund: whoever refunds decides about access / credits)."""
        posthog.capture(
            distinct_id=str(payment.user_id),
            event="payment_refunded",
            properties={
                "user_id": str(payment.user_id),
                "product_id": payment.product_id,
                "amount": payment.amount,
                "currency": payment.currency,
                "payment_id": str(payment.id),
            },
        )
        if user is None:
            user = await self.services.users.get_user_by_id(payment.user_id)
        who = user_ref(user) if user else f"<code>{payment.user_id}</code>"
        default_note = "Nothing was taken back: revoke the access or readings by hand if needed."
        await self.services.messages.queue_admin_broadcast(
            f"↩️ <b>Refund</b> · {who} — {fmt_money(payment.amount, payment.currency)} for {esc(payment.product_id)}\n"
            f"<i>Payment marked REFUNDED. {esc(access_note) if access_note else default_note}</i>\n"
            + tags("refund", *([user_tag(user)] if user else []))
        )

    async def refund_payment(self, payment_id: UUID) -> Payment:
        """Refund a succeeded payment at its provider (an admin action) and take back what it paid for.

        The subscription loses the payment's period (end_date moves back by the product's duration;
        with nothing left it ends now), and a provider-managed subscription is canceled so it doesn't
        charge again. Raises ValueError when the payment can't be refunded here (not SUCCEEDED, or a
        provider without a refund API: YooKassa refunds are made in its dashboard).

        The DB work (writes and the reads the report needs) comes first and the provider call last: if
        the provider refuses (``ProviderRefundError``), the request's transaction rolls back and
        nothing changed. After the money is back, nothing may fail the request. If the provider did
        refund but the call still failed (a timeout), its refund notice finishes the job: see
        ``process_callback``.
        """
        payment = await self.repo.payments.get_by_id_with_lock(payment_id)
        if payment is None:
            raise ValueError("Payment not found")
        if payment.status != PaymentStatus.SUCCEEDED:
            raise ValueError(f"Only a succeeded payment can be refunded (this one is {payment.status})")
        provider = self.providers.get(payment.provider_id)
        if provider is None or not provider.supports_refund:
            raise ValueError(f"{payment.provider_id} payments can't be refunded from here")

        now = datetime.now(UTC)
        refunded = await self.repo.payments.update(
            payment.id,
            {
                "status": PaymentStatus.REFUNDED,
                "provider_metadata": {**(payment.provider_metadata or {}), "refunded_at": now.isoformat()},
            },
        )
        await self.repo.payment_events.create(
            {
                "payment_id": payment.id,
                "provider_id": payment.provider_id,
                "event_type": PaymentEventType.PAYMENT_REFUNDED,
                "timestamp": now,
                "raw_data": {"source": "admin_refund"},
            }
        )
        subscription, access_note = await self._take_back_period(payment, now)
        user = await self.services.users.get_user_by_id(
            payment.user_id
        )  # for the report, before the point of no return

        try:
            await provider.refund(payment)
        except Exception as e:
            raise ProviderRefundError(str(e)) from e

        access_note = await self._stop_renewals_after_refund(payment, subscription, access_note)
        try:
            await self._handle_refund(payment, access_note=access_note, user=user)
        except Exception as e:
            # The money is back: a reporting failure must not roll the REFUNDED row back.
            logger.error(f"Refund {payment.id}: reporting failed: {e}", exc_info=True)
        return refunded or payment

    async def _stop_renewals_after_refund(self, payment: Any, subscription: Any, access_note: str) -> str:
        """Cancel the refunded subscription at its provider. The money is back already, so a failure
        is only noted: it risks a future renewal, which the resurrection guard in
        top_up_subscription refuses for a canceled sub."""
        if subscription is None:
            return access_note
        try:
            await self.cancel_provider_subscription(subscription)
        except Exception as e:
            logger.error(f"Refund {payment.id}: canceling subscription {subscription.id} at the provider failed: {e}")
            access_note += f" Cancel at {subscription.provider_id} failed: {e}"
        return access_note

    async def _take_back_period(self, payment: Any, now: datetime) -> tuple[Any, str]:
        """Take back what the refunded payment gave: the product's own take-back (e.g. a credit pack's
        unspent credits), else the period from its subscription. Returns (subscription, note)."""
        product = self.products.get_product(payment.product_id)
        note = await product_take_back(product, payment, self.services.subscriptions)
        if note is not None:
            return None, note
        if not payment.subscription_id:
            return None, "No subscription was linked to this payment."
        subscription = await self.repo.subscriptions.get_by_id_with_lock(payment.subscription_id)
        if subscription is None:
            return None, "No subscription was linked to this payment."
        days = product.duration_days if product else 0
        end_date = subscription.end_date - timedelta(days=days)
        if end_date <= now:
            await self.repo.subscriptions.update(
                subscription.id,
                {
                    "status": SubscriptionStatus.EXPIRED,
                    "end_date": now,
                    "canceled_at": subscription.canceled_at or now,
                    "cancellation_reason": "refunded",
                },
            )
            return subscription, "Access ended now."
        await self.repo.subscriptions.update(
            subscription.id,
            {
                "status": SubscriptionStatus.CANCELED,
                "end_date": end_date,
                "canceled_at": subscription.canceled_at or now,
                "cancellation_reason": "refunded",
            },
        )
        return subscription, f"Access shortened by {days} days, to {end_date:%Y-%m-%d}; renewals stopped."

    async def start_payment(
        self,
        user_id: UUID,
        product_id: str,
        currency: str,
        provider_id: PaymentProvider,
        return_url: str | None = None,
        locale: str | None = None,
    ) -> dict[str, Any]:
        """
        Start a payment process

        Args:
            user_id: The user making the payment
            product_id: The product being purchased
            currency: The currency for the payment
            provider_id: The payment provider to use
            return_url: URL to redirect to after payment
            locale: App i18n locale ('ru'/'en') for provider UI language (embedded widget)

        Returns:
            Dict with payment details and confirmation URL
        """
        logger.info(
            f"Starting payment for user {user_id} product {product_id} currency {currency} provider {provider_id} return url {return_url}"
        )

        # Only what's on sale (plus test products in debug mode): a legacy plan keeps renewing, refunding
        # and canceling by its own product, but can't be bought again from an old link.
        on_sale = {**self.products.AVAILABLE_PRODUCTS, **(self.products.TEST_PRODUCTS if settings.debug else {})}
        product = on_sale.get(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found or not available")
        await self._check_daily_purchase_limit(user_id, product)

        payment = await self.repo.payments.create(
            {
                "user_id": user_id,
                "product_id": product_id,
                "provider_id": provider_id,
                "amount": product.get_price_for(currency).amount,
                "currency": currency,
                "status": PaymentStatus.CREATED,
                # Persisted before the provider call so a retry reuses the same key (no double-charge).
                "idempotency_key": uuid4().hex,
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
        payment_updates, return_data = await provider.create_payment(payment, return_url=return_url, locale=locale)
        logger.info(f"Payment initiated with provider id: {return_data.get('payment_id')}")

        posthog.capture(
            distinct_id=str(user_id),
            event="payment_provider_created",
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

    async def check_purchase_allowed(self, user_id: UUID, product_id: str) -> None:
        """Raise PurchaseLimitError if this purchase would go over the daily cap. Checked when the
        payment starts and again right before Telegram charges (pre-checkout), so invoices opened
        ahead and paid later can't get past it."""
        product = self.products.get_product(product_id)
        if product is not None:
            await self._check_daily_purchase_limit(user_id, product)

    async def _check_daily_purchase_limit(self, user_id: UUID, product: Any) -> None:
        """Products with a ``daily_purchase_limit`` share it: at most that many succeeded purchases of
        any of them per user in 24 h. A guardrail against buying compulsively (one-off packs)."""
        limit = product_daily_purchase_limit(product)
        if not limit:
            return
        limited_ids = [pid for pid, p in self.products.AVAILABLE_PRODUCTS.items() if product_daily_purchase_limit(p)]
        since = datetime.now(UTC) - timedelta(hours=24)
        bought = await self.repo.payments.count_succeeded_since(user_id, limited_ids, since)
        if bought >= limit:
            posthog.capture(
                distinct_id=str(user_id),
                event="purchase_daily_limit_reached",
                properties={"user_id": str(user_id), "product_id": product.product_id, "limit": limit},
            )
            raise PurchaseLimitError(f"Daily purchase limit reached ({limit} in 24 h)")

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

        # State machine protection: Check if payment is already in a final state. The one exit
        # from a final state is a refund of a succeeded payment.
        is_refund = event_type == PaymentEventType.PAYMENT_REFUNDED and locked_payment.status == PaymentStatus.SUCCEEDED
        # Only a SUCCEEDED payment can be refunded: a refund for anything else (already refunded, or a
        # row whose successful_payment never arrived) is logged and changes nothing.
        not_refundable = event_type == PaymentEventType.PAYMENT_REFUNDED and not is_refund
        if (locked_payment.status.is_final and not is_refund) or not_refundable:
            logger.warning(
                f"Ignoring {event_type} for payment {payment.id} in state {locked_payment.status}. "
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
        elif is_refund:
            access_note = None
            if provider.supports_refund:
                # A refund through the provider's API (Telegram Stars) we haven't recorded: our own
                # refund_payment whose request failed after the provider had refunded (a timeout), or
                # one the provider made itself. The money is back either way, so take back what the
                # payment gave, as refund_payment does.
                subscription, access_note = await self._take_back_period(locked_payment, datetime.now(UTC))
                access_note = await self._stop_renewals_after_refund(locked_payment, subscription, access_note)
            await self._handle_refund(locked_payment, access_note=access_note)
        elif event_type in (PaymentEventType.PAYMENT_FAILED, PaymentEventType.PAYMENT_CANCELED):
            _capture_failure(payment, update_data.get("status"), recurring_details)

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

    async def cancel_provider_subscription(self, subscription: Any) -> None:
        """Tell the payment provider to stop future renewals for ``subscription``.

        Routes to the provider that owns the subscription. For Telegram Stars this calls
        editUserStarSubscription(is_canceled=True) so Telegram stops auto-debiting; for YooKassa
        it is a no-op (our own dunning cron drives those renewals, so the CANCELED status already
        stops them). A native Star subscription still live on the row is canceled at Telegram even
        when a later purchase (e.g. a plan by card) made the row another provider's. Best-effort by
        contract — callers should not let a provider-side failure block the user's cancel; the
        top_up_subscription resurrection guard is the safety net.
        """
        provider_ids = [subscription.provider_id]
        if subscription.provider_id != PaymentProvider.TELEGRAM_STARS and is_native_stars_subscription(
            subscription, self.products
        ):
            provider_ids.append(PaymentProvider.TELEGRAM_STARS.value)
        for provider_id in provider_ids:
            provider = self.providers.get(provider_id)
            if not provider:
                logger.warning(
                    f"No provider for subscription {subscription.id} ({provider_id}); cannot cancel remotely"
                )
                continue
            await provider.cancel(subscription)

    async def get_payment_status(self, user_id: UUID, payment_id: UUID) -> Payment | None:
        """Return the payment if owned by user, reconciling live status when non-final.

        Returns None when not found or not owned (router -> 404).
        """
        payment = await self.repo.payments.get_by_id(payment_id)
        if not payment or payment.user_id != user_id:
            return None
        if payment.status.is_final:
            return payment
        provider = self.providers.get(payment.provider_id)
        if not provider:
            return payment
        live_status, recurring_details = await provider.get_payment_status(payment)
        if live_status == payment.status:
            return payment
        # Re-fetch under lock so a webhook-set final state is never clobbered (same guard as process_callback).
        locked = await self.repo.payments.get_by_id_with_lock(payment.id)
        if locked is None:
            return payment
        if locked.status.is_final:
            return locked
        update_data: dict[str, Any] = {"status": live_status}
        if live_status in (PaymentStatus.FAILED, PaymentStatus.CANCELED):
            _capture_failure(locked, live_status, recurring_details)
        if live_status == PaymentStatus.SUCCEEDED:
            # Grant entitlement here too — otherwise the reconcile leaves a SUCCEEDED-but-unrewarded
            # row, and the webhook's finality guard would then refuse to reward it (the user pays but
            # never gets the subscription). Idempotent via was_rewarded + the row lock above, so the
            # webhook and the poll can't double-grant: whichever finalizes first grants, the other
            # no-ops. The reconcile already did the authoritative find_one, so granting here is as
            # secure as the webhook.
            await self._handle_success(locked, recurring_details, update_data)
            await self.repo.payment_events.create(
                {
                    "payment_id": locked.id,
                    "provider_id": locked.provider_id,
                    "event_type": PaymentEventType.PAYMENT_SUCCEEDED,
                    "timestamp": datetime.now(UTC),
                    "raw_data": {"source": "status_reconcile", "remote_status": live_status.value},
                }
            )
        updated = await self.repo.payments.update(payment.id, update_data)
        return updated or locked

    @staticmethod
    def _currency_prices(product: Any, fallback_currency: str) -> list[dict[str, Any]]:
        """All currencies a product can be bought in, as ``[{currency, amount}]``.

        App products carry a ``prices`` dict (RUB/USD/XTR); the core ProductCatalog protocol does
        not require it, so read defensively and fall back to the single requested-currency price.
        Lets the frontend surface the Telegram Stars (XTR) amount without a second API round-trip.
        """
        prices = getattr(product, "prices", None)
        if isinstance(prices, dict) and prices:
            return [{"currency": cp.currency, "amount": cp.amount} for cp in prices.values()]
        price = product.get_price_for(fallback_currency)
        return [{"currency": price.currency, "amount": price.amount}]

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
                "prices": self._currency_prices(p, currency),
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
                "prices": self._currency_prices(p, currency),
            }
            for p in self.products.CURRENT_OFFERS.values()
        ]


def _payment_method_type(payment: Any, details: dict[str, Any] | None) -> str | None:
    """bank_card / sbp / ... from YooKassa; telegram_stars for Stars."""
    if payment.provider_id == PaymentProvider.TELEGRAM_STARS:
        return "telegram_stars"
    return (details or {}).get("payment_method_type")


def _capture_failure(payment: Any, status: Any, details: dict[str, Any] | None) -> None:
    """`payment_failed` for a payment that ended FAILED or CANCELED, with the provider's reason
    when it gives one. Sent once: from the webhook or from the status poll, whichever sees the
    final status first (the other finds the row already final)."""
    details = details or {}
    posthog.capture(
        distinct_id=str(payment.user_id),
        event="payment_failed",
        properties={
            "user_id": str(payment.user_id),
            "product_id": payment.product_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "provider_id": payment.provider_id,
            "is_recurring": payment.is_recurring,
            "payment_id": str(payment.id),
            "status": str(status) if status else None,
            "payment_method_type": _payment_method_type(payment, details),
            # Same names as the renewal job's payment_failed.
            "reason": details.get("cancellation_reason"),
            "party": details.get("cancellation_party"),
        },
    )

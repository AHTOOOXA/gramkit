from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from aiogram.types import LabeledPrice

from core.domain.products import ProductCatalog, product_invoice_text
from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import PaymentEventType, PaymentProvider, PaymentStatus
from core.infrastructure.database.models.payments import Payment
from core.infrastructure.logging import get_logger
from core.infrastructure.telegram.admin_messages import esc, tags
from core.services.payments.types import PaymentProviderInterface

logger = get_logger(__name__)


def is_native_stars_subscription(subscription: Any, products: ProductCatalog) -> bool:
    """Whether Telegram still renews this subscription row itself (a native monthly Star subscription
    not yet canceled at Telegram).

    Read from the row's own record, not from its current product or provider: another purchase merged
    into the row (the weekly plan in Stars, any plan by card) replaces product_id and provider_id,
    while the native subscription keeps renewing at Telegram. The initial native charge stores
    ``telegram_subscription_charge_id``; a cancel at Telegram sets ``telegram_subscription_canceled``.
    Monthly Stars subs from before the first-charge id was stored count as native too.
    """
    details = subscription.recurring_details or {}
    if details.get("telegram_subscription_canceled"):
        return False
    if details.get("telegram_subscription_charge_id"):
        return True
    product = products.get_product(subscription.product_id)
    return bool(
        subscription.provider_id == PaymentProvider.TELEGRAM_STARS
        and product
        and product.recurring
        and product.duration_days == 30
        and details.get("telegram_subscription_managed", True)
    )


class TelegramStarsProvider(PaymentProviderInterface):
    supports_refund = True

    def __init__(self, repo, services, products: ProductCatalog):
        """Initialize Telegram Stars provider.

        Uses settings.bot for configuration.
        """
        self.repo = repo
        self.services = services
        self.products = products
        self.bot = Bot(token=settings.bot.token)

    async def create_payment(
        self, payment: Payment, return_url: str = None, locale: str | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Create a Telegram Stars payment invoice

        Args:
            payment: The payment record from the database
            return_url: Optional URL to redirect to after payment (used for Web App)
            locale: Ignored (Telegram Stars uses an invoice, no embedded widget)

        Returns:
            Tuple containing (payment_updates, return_data)
        """
        try:
            # Create invoice for Telegram Stars
            # For Telegram Stars, the amount should be in stars (integer)
            stars_amount = int(payment.amount)

            # Get product details for description
            product = self.products.get_product(payment.product_id)

            # Native Telegram Star subscriptions are 30-day-only, so only the monthly plan can
            # auto-renew via Stars; any other recurring plan (e.g. yearly) is sold as a ONE-TIME
            # Star payment with self-managed expiry.
            is_native_sub = bool(product and product.recurring and product.duration_days == 30)

            title = f"{product.name}" if product else f"Product {payment.product_id}"
            description = f"Purchase of {title}"
            if is_native_sub:
                description += " - Auto-renewing every 30 days"
            elif product and product.recurring:
                description += f" - {product.duration_days} days access"
            # The app can word the invoice in the user's language (Telegram shows it in the payment sheet).
            localized = product_invoice_text(product, locale)
            if localized:
                title, description = localized

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

            # Add the native auto-renew period only for the 30-day plan. Omitting it makes this a
            # one-time Star charge (used for the yearly plan, which we expire ourselves).
            if is_native_sub:
                invoice_params["subscription_period"] = 2592000  # 30 days in seconds (Telegram constraint)
                logger.info(f"Creating Telegram Stars subscription invoice for payment {payment.id} with 30-day period")
            else:
                logger.info(f"Creating one-time Telegram Stars invoice for payment {payment.id}")

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

            payment = None
            refunded_charge_id = (payload.get("refunded_payment") or {}).get("telegram_payment_charge_id")
            if refunded_charge_id:
                # A refund names the exact charge. A renewal has its own row keyed by the charge id,
                # while the invoice payload always points at the subscription's first row.
                payment = await self.repo.payments.get_by_provider_payment_id(refunded_charge_id)
            if not payment:
                payment = await self.repo.payments.get_by_id(payment_id)
                stored_charge_id = (
                    (payment.provider_metadata or {}).get("telegram_payment_charge_id") if payment else None
                )
                if refunded_charge_id and stored_charge_id and stored_charge_id != refunded_charge_id:
                    # A charge we have no row for (a renewal whose successful_payment was lost). The
                    # payload's row is another charge: marking it REFUNDED would be wrong.
                    await self._alert_unknown_refund(payment, refunded_charge_id)
                    return {}, None, None, {}
            if not payment:
                logger.error(f"Payment {payment_id} not found")
                return {}, None, None, {}

            # Determine event type based on the payload
            if payload.get("successful_payment"):
                # Payment succeeded - could be the initial charge or an auto-renewal
                successful_payment = payload["successful_payment"]
                charge_id = successful_payment.get("telegram_payment_charge_id")
                provider_charge_id = successful_payment.get("provider_payment_charge_id")

                # Telegram's authoritative subscription flags: is_recurring is True on EVERY
                # subscription charge, is_first_recurring is True only on the first one — so a
                # renewal (auto-debit) is precisely "recurring but not the first".
                is_recurring = bool(successful_payment.get("is_recurring") or payload.get("is_recurring"))
                is_first_recurring = bool(
                    successful_payment.get("is_first_recurring") or payload.get("is_first_recurring")
                )
                is_renewal = is_recurring and not is_first_recurring

                product = self.products.get_product(payment.product_id)
                is_subscription = bool(product and product.recurring)
                # Only the 30-day plan is a native Telegram-managed subscription (auto-renews +
                # cancellable at Telegram). Any other recurring plan (yearly) is a one-time Star
                # charge we expire ourselves — Telegram never auto-renews it, so there is nothing to
                # cancel there.
                is_native_sub = bool(is_subscription and product and product.duration_days == 30)

                # recurring_details carries the Telegram charge id down to top_up_subscription so it
                # is stored on the subscription row (cancel()/refunds read it later). Gate on
                # product.recurring — the old endswith("_SUB") test never matched the real *_V3
                # product ids, so the charge id was silently dropped.
                recurring_details = {}
                if is_subscription:
                    recurring_details = {
                        # The latest charge — overwritten each renewal by the top_up merge; used for
                        # refunds (refundStarPayment is per-charge) and renewal dedup.
                        "telegram_payment_charge_id": charge_id,
                        "provider_payment_charge_id": provider_charge_id,
                        "is_renewal": is_renewal,
                        # True only for the native monthly sub; the yearly one-time purchase is not
                        # Telegram-managed (cancel() no-ops for it).
                        "telegram_subscription_managed": is_native_sub,
                    }
                    if is_native_sub and not is_renewal:
                        # The FIRST charge id is the subscription's canonical identifier for
                        # editUserStarSubscription — Telegram's botCancelStarsSubscription wants the
                        # charge id "from the first subscription payment". Set it ONCE on the initial
                        # charge under a stable key the top_up merge never overwrites, so cancel()
                        # sends the right id even after many renewals (the latest id would be rejected
                        # and Telegram would keep debiting a "canceled" user).
                        recurring_details["telegram_subscription_charge_id"] = charge_id
                        # A new native subscription; an earlier one on this row may have been canceled.
                        recurring_details["telegram_subscription_canceled"] = False

                event_type = PaymentEventType.PAYMENT_SUCCEEDED

                if is_renewal:
                    # RENEWAL. Telegram auto-debited the user and re-sent the ORIGINAL invoice
                    # payload, so `payment` is the first charge's row — already SUCCEEDED. Reusing it
                    # would hit the finality guard in PaymentsService.process_callback and silently
                    # no-op (the historical "sub lapses after month 1 while Telegram keeps charging"
                    # bug). Mint a fresh, non-final Payment row keyed on this renewal's unique
                    # telegram charge id and hand THAT to the service, so _handle_success →
                    # top_up_subscription extends end_date. Idempotent: a redelivered renewal finds
                    # the row by charge id and lets the finality guard no-op it. NOTE this
                    # get-then-create dedup is not atomic (provider_payment_id is indexed, not
                    # unique, and this runs before the service's row lock) — safe today because the
                    # only delivery path is the aiogram bot, which processes updates sequentially, so
                    # the same renewal is never minted concurrently. If a concurrent path is ever
                    # added (e.g. the dormant web webhook), add a partial-unique index on
                    # provider_payment_id as the structural backstop.
                    existing = await self.repo.payments.get_by_provider_payment_id(charge_id) if charge_id else None
                    if existing:
                        logger.info(
                            f"Telegram Stars renewal for charge {charge_id} already recorded "
                            f"(payment {existing.id}); deferring to finality guard"
                        )
                        return {}, event_type, existing, recurring_details

                    renewal_payment = await self.repo.payments.create(
                        {
                            "user_id": payment.user_id,
                            "product_id": payment.product_id,
                            "provider_id": payment.provider_id,
                            "amount": payment.amount,
                            "currency": payment.currency,
                            "status": PaymentStatus.CREATED,
                            "is_recurring": True,
                            "subscription_id": payment.subscription_id,
                            "provider_payment_id": charge_id,
                            "provider_metadata": {
                                "telegram_payment_charge_id": charge_id,
                                "provider_payment_charge_id": provider_charge_id,
                                "is_renewal": True,
                                "renewed_from_payment_id": str(payment.id),
                                "payment_processed_at": datetime.now(UTC).isoformat(),
                            },
                        }
                    )
                    logger.info(
                        f"Telegram Stars renewal recorded as fresh payment {renewal_payment.id} "
                        f"(charge {charge_id}, renewed from {payment.id})"
                    )
                    return {"status": PaymentStatus.SUCCEEDED}, event_type, renewal_payment, recurring_details

                # INITIAL charge (or a one-time purchase). The original WAITING_FOR_ACTION row is the
                # right one to finalize; a redelivery finds it already SUCCEEDED and the finality
                # guard no-ops it.
                update_data = {
                    "status": PaymentStatus.SUCCEEDED,
                    "provider_metadata": {
                        **payment.provider_metadata,
                        "telegram_payment_charge_id": charge_id,
                        "provider_payment_charge_id": provider_charge_id,
                        "is_renewal": False,
                        "payment_processed_at": datetime.now(UTC).isoformat(),
                    },
                }
                logger.info(f"Telegram Stars initial payment {payment_id} succeeded")
                return update_data, event_type, payment, recurring_details

            elif payload.get("refunded_payment"):
                # Telegram refunded a Star charge (our refundStarPayment, or a refund made on
                # Telegram's side). The service lets only a SUCCEEDED payment become REFUNDED, so a
                # refund already recorded by refund_payment() is a logged no-op here.
                update_data = {
                    "status": PaymentStatus.REFUNDED,
                    "provider_metadata": {
                        **payment.provider_metadata,
                        "refunded_at": datetime.now(UTC).isoformat(),
                    },
                }
                logger.info(f"Telegram Stars refund for payment {payment.id} (charge {refunded_charge_id})")
                return update_data, PaymentEventType.PAYMENT_REFUNDED, payment, {}

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

    async def refund(self, payment: Payment) -> None:
        """Give one charge's Stars back to the user (refundStarPayment). Raises on failure.

        refundStarPayment works per charge: a renewal row carries its own charge id, the first row
        the initial one. It doesn't stop a native subscription; PaymentsService.refund_payment
        cancels that separately.
        """
        charge_id = (payment.provider_metadata or {}).get("telegram_payment_charge_id")
        if not charge_id:
            raise RuntimeError(f"Telegram Stars payment {payment.id} has no stored charge id; cannot refund")

        user = await self.services.users.get_user_by_id(payment.user_id)
        if not user or not user.telegram_id:
            raise RuntimeError(f"Telegram Stars payment {payment.id}: user/telegram_id unavailable; cannot refund")

        await self.bot.refund_star_payment(user_id=user.telegram_id, telegram_payment_charge_id=charge_id)
        logger.info(f"Refunded Telegram Stars payment {payment.id} (charge {charge_id})")

    async def cancel(self, subscription) -> None:
        """Cancel the Telegram-managed Star subscription so Telegram stops auto-debiting.

        Telegram drives native Star-subscription renewals itself (unlike YooKassa, which our cron
        drives), so for the monthly plan a DB-only cancel is not enough — without this call Telegram
        keeps charging and the renewal would re-activate a "canceled" sub. We call
        editUserStarSubscription(is_canceled=True) with the subscription's FIRST charge id (Telegram
        identifies the subscription by its inception charge — botCancelStarsSubscription wants the id
        "from the first subscription payment"; the latest renewal's id is rejected).

        One-time Star purchases (the weekly and yearly plans) are NOT Telegram-managed — Telegram
        never auto-renews them, so there is nothing to cancel there and this is a no-op (the DB
        CANCELED is sufficient; the sub self-expires at end_date). Neither is a native sub already
        canceled at Telegram. Raises on any failure for a managed sub (missing id, unknown user, API
        error) so cancel_subscription turns it into an admin alert rather than a silent money leak.
        """
        if not is_native_stars_subscription(subscription, self.products):
            logger.info(
                f"Subscription {subscription.id} has no live Telegram Star subscription "
                f"(one-time or already canceled there); cancel is a no-op"
            )
            return

        details = subscription.recurring_details or {}
        # Prefer the stable first-charge id; fall back to the (possibly-latest) legacy key only for
        # subs written before it was persisted separately.
        charge_id = details.get("telegram_subscription_charge_id") or details.get("telegram_payment_charge_id")
        if not charge_id:
            # Legacy sub written before any charge id was stored (the old endswith("_SUB") gate
            # dropped it). We cannot tell Telegram to stop, so raise instead of returning silently —
            # otherwise the DB reads CANCELED while Telegram keeps debiting and nobody is alerted.
            # (Self-heals once the sub renews under the fixed code, which backfills the charge id.)
            raise RuntimeError(
                f"Telegram Stars subscription {subscription.id} has no stored charge id; "
                f"cannot cancel auto-renewal at Telegram"
            )

        user = await self.services.users.get_user_by_id(subscription.user_id)
        if not user or not user.telegram_id:
            raise RuntimeError(
                f"Telegram Stars subscription {subscription.id}: user/telegram_id unavailable; "
                f"cannot cancel auto-renewal at Telegram"
            )

        await self.bot.edit_user_star_subscription(
            user_id=user.telegram_id,
            telegram_payment_charge_id=charge_id,
            is_canceled=True,
        )
        # Remembered on the row: a later cancel or refund of it (e.g. after a card purchase merged in)
        # doesn't ask Telegram again.
        await self.repo.subscriptions.update(
            subscription.id, {"recurring_details": {**details, "telegram_subscription_canceled": True}}
        )
        logger.info(f"Canceled Telegram Stars subscription {subscription.id} at Telegram (charge {charge_id})")

    async def _alert_unknown_refund(self, payment: Payment, refunded_charge_id: str) -> None:
        logger.error(
            f"Telegram refunded charge {refunded_charge_id}, which matches no payment "
            f"(the invoice's payment {payment.id} is charge {payment.provider_metadata.get('telegram_payment_charge_id')})"
        )
        await self.services.messages.queue_admin_broadcast(
            f"🚨 <b>Stars refund for an unknown charge</b>\n"
            f"Telegram refunded charge <code>{esc(refunded_charge_id)}</code> of the subscription bought with "
            f"payment <code>{payment.id}</code>, but no payment row has that charge. Nothing was marked "
            f"refunded or taken back: check the user's access by hand.\n" + tags("critical", "refund")
        )

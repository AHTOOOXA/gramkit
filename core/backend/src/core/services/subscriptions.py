from datetime import UTC, datetime, timedelta
from uuid import UUID

from core.domain.products import ProductCatalog
from core.infrastructure.database.models.enums import PaymentProvider, SubscriptionStatus
from core.infrastructure.database.models.payments import Payment, PaymentStatus
from core.infrastructure.logging import get_logger
from core.infrastructure.telegram.admin_messages import (
    esc,
    fmt_ago,
    fmt_date,
    fmt_money,
    fmt_money_map,
    tags,
    user_ref,
    user_tag,
)
from core.schemas.subscriptions import SubscriptionSchema, SubscriptionWithDetailsSchema
from core.schemas.users import UpdateUserRequest
from core.services.base import BaseService

logger = get_logger(__name__)


class SubscriptionsService(BaseService):
    def __init__(self, repo, producer, services, bot, products: ProductCatalog):
        super().__init__(repo, producer, services, bot)
        self.products = products

    def _format_days(self, time_delta: timedelta) -> str:
        total_seconds = time_delta.total_seconds()
        days = int(total_seconds // 86400)  # 86400 seconds in a day
        return f"{days} days"

    def _product_label(self, product_id: str) -> str:
        product = self.products.get_product(product_id)
        return esc(product.name if product else product_id)

    async def _admin_user_context(self, user) -> str:
        """'joined 3d ago · 2 payments · LTV 798 ₽' — who this customer is, at a glance."""
        payments = [p for p in await self.repo.payments.get_by_user_id(user.id) if p.status == PaymentStatus.SUCCEEDED]
        ltv: dict[str, float] = {}
        for p in payments:
            ltv[p.currency] = ltv.get(p.currency, 0) + p.amount
        count = len(payments)
        return (
            f"joined {fmt_ago(user.created_at)} · {count} payment{'s' if count != 1 else ''} · LTV {fmt_money_map(ltv)}"
        )

    # TO FRONTEND
    async def get_subscription_for_user(self, user_id: UUID) -> SubscriptionSchema:
        subscription = await self.repo.subscriptions.get_active_by_user_id(user_id)
        if subscription:
            return SubscriptionSchema.model_validate(subscription)
        return SubscriptionSchema.get_mock_subscription(user_id)

    async def get_subscription_with_details_for_user(self, user_id: UUID) -> SubscriptionWithDetailsSchema:
        subscription = await self.repo.subscriptions.get_active_by_user_id(user_id)
        if subscription:
            if subscription.product_id == "GIFT_SUB":
                product_price = 0
            else:
                product = self.products.get_product(subscription.product_id)
                if not product:
                    logger.error(f"Product {subscription.product_id} not found")
                    product_price = 0
                else:
                    product_price = product.get_price_for(subscription.currency).amount

            subscription_dict = {
                "id": subscription.id,
                "user_id": subscription.user_id,
                "product_id": subscription.product_id,
                "status": subscription.status,
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "product_price": product_price,
                "provider_id": subscription.provider_id,
                "currency": subscription.currency,
            }
            subscription_with_details = SubscriptionWithDetailsSchema.model_validate(subscription_dict)
            return subscription_with_details
        else:
            subscription = SubscriptionSchema.get_mock_subscription(user_id)
            weekly_product = self.products.get_product("WEEK_SUB_V2")  # Use newer product price for mock
            product_price = weekly_product.get_price_for("USD").amount if weekly_product else 1.99

            subscription_dict = {
                "id": subscription.id,
                "user_id": subscription.user_id,
                "product_id": subscription.product_id,
                "status": subscription.status,
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "product_price": product_price,
                "provider_id": PaymentProvider.GIFT,
                "currency": "USD",
            }
            subscription_with_details = SubscriptionWithDetailsSchema.model_validate(subscription_dict)
            return subscription_with_details

    async def has_active_subscription(self, user_id: UUID) -> bool:
        subscription = await self.repo.subscriptions.get_active_by_user_id(user_id)
        return subscription is not None and subscription.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.CANCELED,
        )

    # INSIDE PAYMENT SERVICE
    async def top_up_subscription(self, user_id, product_id, duration_days, payment: Payment, recurring_details: dict):
        logger.info(
            f"Topping up subscription for user {user_id} with product {payment.product_id} after payment {payment.id}"
        )
        now = datetime.now(UTC)
        subscription = await self.repo.subscriptions.get_active_by_user_id(user_id)
        if not subscription:
            # Fallback: find expired-but-still-ACTIVE subs (e.g., after downtime)
            # Prevents creating duplicate subs and leaving old ones to be re-charged
            subscription = await self.repo.subscriptions.get_renewable_by_user_id(user_id)

        # Resurrection backstop for the no-sub-found case: a late auto-renewal can land just after a
        # canceled sub's end_date, when neither lookup above sees it (get_active filters end_date >
        # now; get_renewable excludes CANCELED). Without this, the renewal would create a brand-new
        # ACTIVE sub — resurrecting what the user canceled. Refuse if a recently-canceled sub exists.
        # (Only auto-renewals carry recurring_details.is_renewal; a deliberate re-purchase is
        # is_first_recurring and falls through to reactivate normally.)
        if not subscription and recurring_details.get("is_renewal"):
            recently_canceled = await self.repo.subscriptions.get_recently_canceled_by_user_id(
                user_id, now - timedelta(days=45)
            )
            if recently_canceled:
                logger.warning(
                    f"Ignoring auto-renewal for recently-canceled subscription {recently_canceled.id} "
                    f"(payment {payment.id}); not resurrecting past end_date"
                )
                await self.repo.payments.update(payment.id, {"subscription_id": recently_canceled.id})
                return recently_canceled

        is_renewal = False

        # Always use the product_id from the payment record
        actual_product_id = payment.product_id

        if subscription:
            # Resurrection guard: a user-CANCELED subscription that is still inside its paid window
            # must NOT be flipped back to ACTIVE by a late/in-flight provider auto-renewal (e.g. a
            # Telegram Star debit that fired before our editUserStarSubscription cancel propagated).
            # Only block genuine auto-renewals (recurring_details.is_renewal) — a user actively
            # re-purchasing reuses this same row and SHOULD reactivate it, so it must fall through.
            # Honoring-vs-refunding the extra charge is a Phase 2 decision; Phase 1 just refuses to
            # resurrect.
            if subscription.status == SubscriptionStatus.CANCELED and recurring_details.get("is_renewal"):
                logger.warning(
                    f"Ignoring auto-renewal for canceled subscription {subscription.id} "
                    f"(payment {payment.id}); not resurrecting"
                )
                await self.repo.payments.update(payment.id, {"subscription_id": subscription.id})
                return subscription

            is_renewal = True
            current_end_date = max(subscription.end_date, now)
            new_end_date = current_end_date + timedelta(days=duration_days)
            merged_details = {
                **subscription.recurring_details,
                **recurring_details,
            }  # new values override existing keys
            subscription = await self.repo.subscriptions.update(
                subscription.id,
                {
                    "product_id": actual_product_id,
                    "provider_id": payment.provider_id,
                    "currency": payment.currency,
                    "status": SubscriptionStatus.ACTIVE,
                    "end_date": new_end_date,
                    "recurring_details": merged_details,
                    "payment_method_id": merged_details.get("payment_method_id") or subscription.payment_method_id,
                },
            )
        else:
            subscription = await self.repo.subscriptions.create(
                {
                    "user_id": user_id,
                    "product_id": actual_product_id,
                    "provider_id": payment.provider_id,
                    "currency": payment.currency,
                    "status": SubscriptionStatus.ACTIVE,
                    "start_date": now,
                    "end_date": now + timedelta(days=duration_days),
                    "recurring_details": recurring_details,
                    "payment_method_id": recurring_details.get("payment_method_id"),
                },
            )
        await self.repo.payments.update(payment.id, {"subscription_id": subscription.id})
        user = await self.services.users.update_user(
            user_id,
            UpdateUserRequest(
                is_onboarded=True,
            ),
        )  # FOR HANDLING IF PURCHASED BEFORE ONBOARDING FINISHED

        amount = esc(fmt_money(payment.amount, payment.currency))
        context = await self._admin_user_context(user)
        if is_renewal:
            await self.services.messages.queue_admin_broadcast(
                f"🔁 <b>Renewal · {amount}</b>\n"
                f"{self._product_label(actual_product_id)} · {user_ref(user)}\n"
                f"<i>{context} · until {fmt_date(subscription.end_date)}</i>\n"
                f"{tags('renewal', user_tag(user))}"
            )
        else:
            await self.services.messages.queue_admin_broadcast(
                f"💰 <b>Purchase · {amount}</b>\n"
                f"{self._product_label(actual_product_id)} · {user_ref(user)}\n"
                f"<i>{context}</i>\n"
                f"{tags('purchase', user_tag(user))}"
            )

        return subscription

    async def gift_subscription(self, user_id: UUID, duration_days: int, gifted_by: UUID | None = None):
        """Grant (or extend) a free GIFT subscription for ``duration_days``.

        Shared by the Telegram ``/giftsub`` command and the admin web endpoint so the
        two paths produce identical subscription state:
        - If the user already has an entitled subscription whose ``end_date`` is in the
          future, EXTEND it by ``duration_days`` and force it ACTIVE.
        - Otherwise CREATE a fresh GIFT_SUB/GIFT subscription running from now.

        Also flips ``is_onboarded`` (a gift unblocks onboarding-gated users). Repos use
        flush() — the transaction commits at the interface layer.
        """
        now = datetime.now(UTC)
        subscription = await self.repo.subscriptions.get_active_by_user_id(user_id)

        if subscription and subscription.end_date > now:
            new_end_date = subscription.end_date + timedelta(days=duration_days)
            subscription = await self.repo.subscriptions.update(
                subscription.id,
                {
                    "end_date": new_end_date,
                    "status": SubscriptionStatus.ACTIVE,
                },
            )
        else:
            subscription = await self.repo.subscriptions.create(
                {
                    "user_id": user_id,
                    "product_id": "GIFT_SUB",
                    "provider_id": PaymentProvider.GIFT,
                    "status": SubscriptionStatus.ACTIVE,
                    "currency": "RUB",
                    "start_date": now,
                    "end_date": now + timedelta(days=duration_days),
                    "recurring_details": {"gifted_by": str(gifted_by)} if gifted_by else {},
                }
            )

        await self.services.users.update_user(user_id, UpdateUserRequest(is_onboarded=True))
        return SubscriptionSchema.model_validate(subscription)

    async def cancel_subscription(self, user_id, reason: str | None = None, feedback: str | None = None):
        subscription = await self.repo.subscriptions.get_active_by_user_id(user_id)
        if subscription:
            await self.repo.subscriptions.update(
                subscription.id,
                {
                    "status": SubscriptionStatus.CANCELED,
                    "canceled_at": datetime.now(UTC),
                    "cancellation_reason": reason,
                    "cancellation_feedback": feedback,
                },
            )

            # Best-effort: tell the provider to stop future renewals (Telegram Stars debits on its
            # own schedule, so a DB-only cancel would keep getting charged). Never let a provider
            # failure block the user's cancel — the DB row is already CANCELED and the
            # top_up_subscription resurrection guard protects entitlement if this didn't land.
            try:
                await self.services.payments.cancel_provider_subscription(subscription)
            except Exception as e:
                logger.error(
                    f"Failed to cancel subscription {subscription.id} at provider {subscription.provider_id}: {e}",
                    exc_info=True,
                )
                await self.services.messages.queue_admin_broadcast(
                    f"🚨 <b>Cancel not propagated to {esc(subscription.provider_id)}</b>\n"
                    f"Subscription <code>{subscription.id}</code> is CANCELED in our DB, but the provider "
                    f"call failed — check it won't keep charging.\n"
                    f"<pre>{esc(e)}</pre>\n"
                    f"{tags('critical', 'cancel')}"
                )

            user = await self.services.users.get_user_by_id(user_id)

            reason_labels = {
                "tooExpensive": "Too expensive",
                "notUsing": "Not using",
                "foundAlternative": "Found alternative",
                "technicalIssues": "Technical issues",
                "other": "Other",
            }
            message = (
                f"🚫 <b>Canceled · {self._product_label(subscription.product_id)}</b>\n"
                f"{user_ref(user)} · subscribed {self._format_days(datetime.now(UTC) - subscription.start_date)}, "
                f"access until {fmt_date(subscription.end_date)}\n"
                f"<i>{await self._admin_user_context(user)}</i>"
            )
            if reason:
                message += f"\nReason: <b>{esc(reason_labels.get(reason, reason))}</b>"
            if feedback:
                message += f"\n<blockquote>{esc(feedback)}</blockquote>"
            message += f"\n{tags('cancel', user_tag(user))}"

            await self.services.messages.queue_admin_broadcast(message)
            return SubscriptionSchema.model_validate(subscription)
        return SubscriptionSchema.get_mock_subscription(user_id)

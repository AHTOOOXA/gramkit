from datetime import UTC, datetime, timedelta
from uuid import UUID

from core.domain.products import ProductCatalog
from core.infrastructure.database.models.enums import PaymentProvider, SubscriptionStatus
from core.infrastructure.database.models.payments import Payment
from core.infrastructure.logging import get_logger
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
        return subscription is not None and (
            subscription.status == SubscriptionStatus.ACTIVE or subscription.status == SubscriptionStatus.CANCELED
        )

    # INSIDE PAYMENT SERVICE
    async def top_up_subscription(self, user_id, product_id, duration_days, payment: Payment, recurring_details: dict):
        logger.info(
            f"Topping up subscription for user {user_id} with product {payment.product_id} after payment {payment.id}"
        )
        now = datetime.now(UTC)
        subscription = await self.repo.subscriptions.get_active_by_user_id(user_id)
        is_renewal = False

        # Always use the product_id from the payment record
        actual_product_id = payment.product_id

        if subscription:
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
                },
            )
        await self.repo.payments.update(payment.id, {"subscription_id": subscription.id})
        user = await self.services.users.update_user(
            user_id,
            UpdateUserRequest(
                is_onboarded=True,
            ),
        )  # FOR HANDLING IF PURCHASED BEFORE ONBOARDING FINISHED

        # Get product for logging/admin alert
        product = self.products.get_product(actual_product_id)
        product_name = product.name if product else actual_product_id

        if is_renewal:
            await self.services.messages.queue_admin_broadcast(
                f"💸💸💸 RENEWAL\n\n"
                f"User: @{user.username} (ID: {user.id})\n"
                f"Product: {product_name} (ID: {actual_product_id})\n"
                f"Amount: {payment.amount} {payment.currency}\n"
                f"Start date: {subscription.start_date}\n"
                f"End date: {subscription.end_date}\n"
                f"Duration: {self._format_days(subscription.end_date - subscription.start_date)}"
            )
        else:
            await self.services.messages.queue_admin_broadcast(
                f"💰💰💰 PURCHASE\n\n"
                f"User: @{user.username} (ID: {user.id})\n"
                f"Product: {product_name} (ID: {actual_product_id})\n"
                f"Amount: {payment.amount} {payment.currency}"
            )

        return subscription

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
            user = await self.services.users.get_user_by_id(user_id)

            # Get product for logging/admin alert
            product = self.products.get_product(subscription.product_id)
            product_name = product.name if product else subscription.product_id

            # Build admin notification message
            message = (
                f"🚫🚫🚫 CANCELED\n\n"
                f"User: @{user.username} (ID: {user.id})\n"
                f"Product: {product_name} (ID: {subscription.product_id})\n"
                f"Start date: {subscription.start_date}\n"
                f"End date: {subscription.end_date}\n"
                f"Duration: {self._format_days(subscription.end_date - subscription.start_date)}"
            )

            # Add cancellation reason if provided
            if reason:
                # Map reason codes to readable labels
                reason_labels = {
                    "tooExpensive": "Too expensive",
                    "notUsing": "Not using",
                    "foundAlternative": "Found alternative",
                    "technicalIssues": "Technical issues",
                    "other": "Other",
                }
                reason_text = reason_labels.get(reason, reason)
                message += f"\nReason: {reason_text}"

            # Add feedback if provided
            if feedback:
                message += f"\nFeedback: {feedback}"

            await self.services.messages.queue_admin_broadcast(message)
            return SubscriptionSchema.model_validate(subscription)
        return SubscriptionSchema.get_mock_subscription(user_id)

    async def charge_expiring_subscriptions(self, days_before: int):
        expiration_threshold = datetime.now(UTC) + timedelta(days=days_before)
        expiring_subs = await self.repo.subscriptions.get_expiring_subscriptions(expiration_threshold)

        # Filter out subscriptions that shouldn't be charged manually
        # - GIFT subscriptions (already excluded)
        # - TELEGRAM_STARS subscriptions (Telegram manages renewals automatically)
        manually_charged_subs = [
            sub
            for sub in expiring_subs
            if sub.provider_id not in [PaymentProvider.GIFT, PaymentProvider.TELEGRAM_STARS]
        ]

        # Separate Telegram Stars subscriptions for different handling
        telegram_stars_subs = [sub for sub in expiring_subs if sub.provider_id == PaymentProvider.TELEGRAM_STARS]

        logger.info(
            f"Found {len(expiring_subs)} expiring subscriptions: {len(manually_charged_subs)} manual, {len(telegram_stars_subs)} Telegram Stars managed"
        )

        # Handle manually charged subscriptions (YooKassa, etc.)
        if len(manually_charged_subs) > 0:
            users = [await self.services.users.get_user_by_id(sub.user_id) for sub in manually_charged_subs]
            users_str = "\n".join([f"@{user.username} (ID: {user.id})\n" for user in users])
            await self.services.messages.queue_admin_broadcast(
                f"🔧🔧🔧 CHARGING {len(manually_charged_subs)} expiring subscriptions\n\n{users_str}"
            )

            for subscription in manually_charged_subs:
                logger.info(f"Charging subscription {subscription.id} (provider: {subscription.provider_id})")
                await self.services.payments.charge_subscription(subscription)

            logger.info(f"Charged {len(manually_charged_subs)} expiring subscriptions")

        # Handle Telegram Stars subscriptions (just log, don't charge)
        if len(telegram_stars_subs) > 0:
            users = [await self.services.users.get_user_by_id(sub.user_id) for sub in telegram_stars_subs]
            users_str = "\n".join([f"@{user.username} (ID: {user.id})\n" for user in users])
            await self.services.messages.queue_admin_broadcast(
                f"⭐⭐⭐ MONITORING {len(telegram_stars_subs)} expiring Telegram Stars subscriptions (auto-renewed by Telegram)\n\n{users_str}"
            )
            logger.info(
                f"Monitoring {len(telegram_stars_subs)} Telegram Stars subscriptions - renewals managed by Telegram"
            )

        if len(manually_charged_subs) == 0 and len(telegram_stars_subs) == 0:
            logger.info("No expiring subscriptions found")

    async def expire_outdated_subscriptions(self):
        now = datetime.now(UTC)
        expiring_subs = await self.repo.subscriptions.get_expiring_subscriptions(now)
        logger.info(f"Expiring {len(expiring_subs)} subscriptions")
        if len(expiring_subs) > 0:
            expired_count = await self.repo.subscriptions.expire_outdated_subscriptions(now)
            logger.info(f"Expired {expired_count} outdated subscriptions")

            users = [await self.services.users.get_user_by_id(sub.user_id) for sub in expiring_subs]
            user_id_to_username = {user.id: user.username for user in users}
            admin_message = f"🚫🚫🚫 EXPIRED {len(expiring_subs)} outdated subscriptions\n\n"
            for subscription in expiring_subs:
                # TODO: notify users

                # Get product for logging/admin alert
                product = self.products.get_product(subscription.product_id)
                product_name = product.name if product else subscription.product_id

                admin_message += f"@{user_id_to_username[subscription.user_id]} - {product_name} (ID: {subscription.product_id}) - {self._format_days(subscription.end_date - subscription.start_date)}\n"
            await self.services.messages.queue_admin_broadcast(admin_message)
        else:
            logger.info("No outdated subscriptions found")

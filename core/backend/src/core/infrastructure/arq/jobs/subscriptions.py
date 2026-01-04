"""Core subscription background jobs - charging and expiring subscriptions."""

from datetime import UTC, datetime, timedelta

from core.domain.products import ProductCatalog
from core.infrastructure.arq.factory import WorkerContext, inject_context
from core.infrastructure.database.models.enums import (
    PaymentEventType,
    PaymentProvider,
    PaymentStatus,
    SubscriptionStatus,
)
from core.infrastructure.logging import get_logger
from core.services.payments.providers import get_provider

logger = get_logger(__name__)


@inject_context
async def charge_expiring_subscriptions_job(ctx: WorkerContext, products: ProductCatalog) -> dict[str, int]:
    """Charge expiring subscriptions with properly split transactions.

    Transaction pattern (per subscription):
    1. Transaction: Create payment record (fast, <50ms)
    2. NO TRANSACTION: Call YooKassa API (2-5 seconds)
    3. Transaction: Update payment with result (fast, <50ms)

    This ensures external API calls don't hold database locks.

    Uses settings.payment for payment configuration.

    Args:
        ctx: Worker context for transaction management
        products: Product catalog implementation (app-specific)

    Returns:
        Dict with success/failed/skipped counts
    """
    logger.info("Job started: charge_expiring_subscriptions")
    expiration_threshold = datetime.now(UTC) + timedelta(days=1)

    # Transaction 1: Get list of expiring subscriptions (read-only)
    async with ctx.with_repo() as repo:
        expiring_subs = await repo.subscriptions.get_expiring_subscriptions(expiration_threshold)

    # Filter subscriptions
    manually_charged_subs = [
        sub for sub in expiring_subs if sub.provider_id not in [PaymentProvider.GIFT, PaymentProvider.TELEGRAM_STARS]
    ]
    telegram_stars_subs = [sub for sub in expiring_subs if sub.provider_id == PaymentProvider.TELEGRAM_STARS]

    logger.info(
        f"Found {len(expiring_subs)} expiring subscriptions: {len(manually_charged_subs)} manual, {len(telegram_stars_subs)} Telegram Stars managed"
    )

    results = {"success": 0, "failed": 0, "skipped": 0}

    # Process each subscription with split transactions
    for subscription in manually_charged_subs:
        payment_id = None
        try:
            logger.info(f"Processing subscription {subscription.id} (provider: {subscription.provider_id})")
            product = products.get_product(subscription.product_id)

            if not product:
                logger.warning(
                    f"Product {subscription.product_id} not found in catalog, skipping subscription {subscription.id}"
                )
                results["skipped"] += 1
                continue

            # Transaction 2a: Create payment record
            async with ctx.with_transaction() as services:
                payment = await services.repo.payments.create(
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
                payment_id = payment.id
                await services.repo.payment_events.create(
                    {
                        "payment_id": payment.id,
                        "provider_id": subscription.provider_id,
                        "event_type": PaymentEventType.PAYMENT_CREATED,
                        "timestamp": datetime.now(UTC),
                        "raw_data": {"subscription_id": str(subscription.id)},
                        "is_recurring": True,
                    }
                )

            # NO TRANSACTION: External API call (2-5 seconds)
            provider = get_provider(subscription.provider_id, None, None, products)
            from yookassa import Payment as YooKassaPayment

            request = provider._build_payment_request(
                payment,
                return_url=None,
                description_prefix="Auto-renewal: ",
                payment_method_id=subscription.recurring_details["payment_method_id"],
            )
            response = YooKassaPayment.create(request)
            logger.info(f"YooKassa response for payment {payment_id}: status={response.status}, id={response.id}")

            # Transaction 2b: Save result
            async with ctx.with_transaction() as services:
                new_status = PaymentStatus.SUCCEEDED if response.status == "succeeded" else PaymentStatus.FAILED
                event_type = (
                    PaymentEventType.PAYMENT_SUCCEEDED
                    if response.status == "succeeded"
                    else PaymentEventType.PAYMENT_FAILED
                )

                await services.repo.payments.update(
                    payment_id,
                    {
                        "status": new_status,
                        "provider_payment_id": response.id,
                        "provider_metadata": response.metadata,
                        "is_recurring": True,
                    },
                )
                await services.repo.payment_events.create(
                    {
                        "payment_id": payment_id,
                        "provider_id": subscription.provider_id,
                        "event_type": event_type,
                        "timestamp": datetime.now(UTC),
                        "raw_data": {"subscription_id": str(subscription.id)},
                        "is_recurring": True,
                    }
                )

                # Handle success (reward user if needed)
                if event_type == PaymentEventType.PAYMENT_SUCCEEDED:
                    payment_obj = await services.repo.payments.get_by_id(payment_id)
                    if product and not payment_obj.was_rewarded:
                        await product.reward(payment_obj.user_id, payment_obj, {}, services.subscriptions)
                        await services.repo.payments.update(payment_id, {"was_rewarded": True})

            results["success"] += 1
            logger.info(f"Successfully charged subscription {subscription.id}")

        except Exception as e:
            logger.error(f"Failed to charge subscription {subscription.id}: {e}", exc_info=True)
            results["failed"] += 1

            # Mark payment as failed if we created it
            if payment_id:
                try:
                    async with ctx.with_transaction() as services:
                        await services.repo.payments.update(
                            payment_id,
                            {
                                "status": PaymentStatus.FAILED,
                                "provider_metadata": {"error": str(e)},
                            },
                        )
                except Exception as update_error:
                    logger.error(f"Failed to mark payment {payment_id} as failed: {update_error}")

    # Handle Telegram Stars subscriptions (monitoring only)
    if telegram_stars_subs:
        try:
            async with ctx.with_transaction() as services:
                users = [await services.users.get_user_by_id(sub.user_id) for sub in telegram_stars_subs]
                users_str = "\n".join([f"@{user.username} (ID: {user.id})\n" for user in users])
                await services.messages.queue_admin_broadcast(
                    f"⭐⭐⭐ MONITORING {len(telegram_stars_subs)} expiring Telegram Stars subscriptions (auto-renewed by Telegram)\n\n{users_str}"
                )
                results["skipped"] = len(telegram_stars_subs)
        except Exception as e:
            logger.error(f"Failed to send Telegram Stars notification: {e}")

    # Send summary notification
    if manually_charged_subs:
        try:
            async with ctx.with_transaction() as services:
                users = [await services.users.get_user_by_id(sub.user_id) for sub in manually_charged_subs]
                users_str = "\n".join([f"@{user.username} (ID: {user.id})\n" for user in users])
                await services.messages.queue_admin_broadcast(
                    f"🔧🔧🔧 CHARGING {len(manually_charged_subs)} expiring subscriptions\n\n{users_str}"
                )
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")

    logger.info(
        f"Job completed: charge_expiring_subscriptions - Success: {results['success']}, Failed: {results['failed']}, Skipped: {results['skipped']}"
    )
    return results


@inject_context
async def expire_outdated_subscriptions_job(ctx: WorkerContext, products: ProductCatalog) -> dict[str, int]:
    """Expire outdated subscriptions using transaction-per-subscription pattern.

    Transaction pattern (per subscription):
    - Transaction: Expire subscription + gather notification data (fast, <50ms)
    - NO external APIs, so this is simpler than charge_expiring_subscriptions_job

    Each subscription is expired in its own transaction to ensure:
    - If one expiration fails, others continue processing

    Args:
        ctx: Worker context for transaction management
        products: Product catalog implementation (app-specific)

    Returns:
        Dict with expired/total counts
    """
    logger.info("Job started: expire_outdated_subscriptions")
    now = datetime.now(UTC)

    # Transaction 1: Get list of expiring subscriptions (read-only)
    async with ctx.with_repo() as repo:
        expiring_subs = await repo.subscriptions.get_expiring_subscriptions(now)

    if not expiring_subs:
        logger.info("No outdated subscriptions found")
        return {"expired": 0}

    logger.info(f"Found {len(expiring_subs)} subscriptions to expire")
    expired_count = 0
    admin_messages = []

    # Process each subscription in its own transaction
    for subscription in expiring_subs:
        try:
            logger.info(f"Expiring subscription {subscription.id} for user {subscription.user_id}")

            # Transaction 2: Expire subscription and gather data
            async with ctx.with_transaction() as services:
                # Expire the subscription
                await services.repo.subscriptions.update(subscription.id, {"status": SubscriptionStatus.EXPIRED})

                # Get user for notification
                user = await services.users.get_user_by_id(subscription.user_id)

                # Get product info (gracefully handle missing products)
                product = products.get_product(subscription.product_id)
                product_name = product.name if product else subscription.product_id

                # Calculate duration
                duration_days = (subscription.end_date - subscription.start_date).days

                # Prepare admin message
                admin_messages.append(
                    f"@{user.username} - {product_name} (ID: {subscription.product_id}) - {duration_days} days"
                )

                expired_count += 1

            logger.info(f"Successfully expired subscription {subscription.id}")

        except Exception as e:
            logger.error(f"Failed to expire subscription {subscription.id}: {e}", exc_info=True)
            # This subscription failed, continue with next

    # Send consolidated admin notification (separate transaction)
    if admin_messages:
        try:
            async with ctx.with_transaction() as services:
                admin_message = f"🚫🚫🚫 EXPIRED {expired_count} outdated subscriptions\n\n" + "\n".join(admin_messages)
                await services.messages.queue_admin_broadcast(admin_message)
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")

    logger.info(f"Job completed: expire_outdated_subscriptions - Expired: {expired_count}/{len(expiring_subs)}")
    return {"expired": expired_count, "total": len(expiring_subs)}

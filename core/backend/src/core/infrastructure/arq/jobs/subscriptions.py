"""Core subscription background jobs - charging and expiring subscriptions."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from core.domain.products import ProductCatalog
from core.infrastructure.arq.factory import WorkerContext, inject_context
from core.infrastructure.database.models.enums import (
    PaymentEventType,
    PaymentProvider,
    PaymentStatus,
    SubscriptionStatus,
)
from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.infrastructure.telegram.admin_messages import bullet_list, esc, tags, user_ref, user_tag
from core.services.payments.providers import get_provider
from core.services.payments.providers.telegram_stars import is_native_stars_subscription
from core.services.payments.providers.yookassa import renewal_idempotency_key

logger = get_logger(__name__)

# Dunning tuning. The renewal cron runs several times a day; RENEWAL_RETRY_SPACING throttles a
# declining card to ~1 real attempt/day, so MAX_RENEWAL_ATTEMPTS spreads over ~3 days of grace.
MAX_RENEWAL_ATTEMPTS = 3
RENEWAL_RETRY_SPACING = timedelta(hours=20)
# A non-terminal renewal row older than this is treated as stranded (worker died mid-flow), not
# as a concurrent in-flight attempt — comfortably longer than a create()+result-write (seconds).
RECOVERY_STALE_AFTER = timedelta(minutes=30)
# Hard entitlement ceiling for a PAST_DUE sub: expired once end_date + GRACE_PERIOD has passed,
# even if the renewal job stopped selecting it. Covers the daily dunning retries plus slack.
GRACE_PERIOD = timedelta(days=4)


@inject_context
async def charge_expiring_subscriptions_job(ctx: WorkerContext, products: ProductCatalog) -> dict[str, int]:
    """Charge expiring subscriptions with split transactions + a dunning state machine.

    Transaction pattern (per subscription):
    1. Transaction: Create payment record (fast, <50ms)
    2. NO TRANSACTION: Call YooKassa API (2-5 seconds)
    3. Transaction: Update payment + advance dunning state (fast, <50ms)

    Dunning: a declined renewal moves the sub to PAST_DUE (still entitled, in grace) and is
    retried ~once/day up to MAX_RENEWAL_ATTEMPTS; a hard decline (permission_revoked) or an
    exhausted budget expires it. A success resets the counter back to ACTIVE. A bare transport
    exception does NOT advance dunning (the card may have been charged) — it only stamps the
    attempt time so recovery resolves it on the next run.

    Args:
        ctx: Worker context for transaction management
        products: Product catalog implementation (app-specific)

    Returns:
        Dict with success/failed/skipped/past_due/dunning_expired/recovered counts
    """
    logger.info("Job started: charge_expiring_subscriptions")
    now = datetime.now(UTC)
    expiration_threshold = now + timedelta(days=1)

    # Transaction 1: Get list of chargeable subscriptions (ACTIVE + PAST_DUE dunning retries)
    async with ctx.with_repo() as repo:
        expiring_subs = await repo.subscriptions.get_chargeable_subscriptions(expiration_threshold)

    # Filter subscriptions
    manually_charged_subs = [
        sub for sub in expiring_subs if sub.provider_id not in [PaymentProvider.GIFT, PaymentProvider.TELEGRAM_STARS]
    ]
    telegram_stars_subs = [sub for sub in expiring_subs if sub.provider_id == PaymentProvider.TELEGRAM_STARS]

    logger.info(
        f"Found {len(expiring_subs)} chargeable subscriptions: {len(manually_charged_subs)} manual, {len(telegram_stars_subs)} Telegram Stars managed"
    )

    results = {"success": 0, "failed": 0, "skipped": 0, "past_due": 0, "dunning_expired": 0, "recovered": 0}
    dunning_events: list[dict] = []  # consolidated admin summary of dunning transitions

    # Process each subscription with split transactions
    for subscription in manually_charged_subs:
        payment_id = None
        was_past_due = subscription.status == SubscriptionStatus.PAST_DUE
        try:
            logger.info(f"Processing subscription {subscription.id} (provider: {subscription.provider_id})")
            product = products.get_product(subscription.product_id)

            if not product:
                logger.warning(
                    f"Product {subscription.product_id} not found in catalog, skipping subscription {subscription.id}"
                )
                results["skipped"] += 1
                continue

            # Retry-spacing: a PAST_DUE card retried within the window is left for the next day so
            # a several-times-daily cron doesn't hammer a declining card (~1 real attempt/day).
            if (
                was_past_due
                and subscription.last_renewal_attempt_at
                and now - subscription.last_renewal_attempt_at < RENEWAL_RETRY_SPACING
            ):
                logger.info(f"Subscription {subscription.id} retried within spacing window; skipping this run")
                results["skipped"] += 1
                continue

            # Deterministic key for this (subscription, billing period): a re-fired renewal reuses
            # it, so a concurrent double-create is rejected by uq_payment_idempotency_key and a
            # same-period retry is deduped by YooKassa's Idempotence-Key.
            renewal_key = renewal_idempotency_key(subscription.id, subscription.end_date)

            async with ctx.with_repo() as repo:
                already_charged = await repo.payments.get_succeeded_renewal_for_period(renewal_key)
                stranded = await repo.payments.get_nonterminal_renewal_for_period(renewal_key)

            # Dedup: if this period already has a SUCCEEDED renewal, do not charge again. A prior
            # FAILED attempt does NOT block here — the dunning budget must be able to retry it.
            if already_charged:
                logger.info(
                    f"Subscription {subscription.id} already has a SUCCEEDED renewal "
                    f"(payment {already_charged.id}) for end_date {subscription.end_date}; skipping"
                )
                results["skipped"] += 1
                continue

            # Recover a renewal stranded mid-flow: a non-terminal row still holds the period key
            # (blocking a fresh insert via the unique index). Fresh => a concurrent run owns it,
            # skip. Stale => the worker died after create; mark it FAILED so we can re-attempt
            # (the deterministic key keeps the re-charge idempotent on YooKassa's side).
            if stranded:
                if now - stranded.created_at < RECOVERY_STALE_AFTER:
                    logger.info(f"Subscription {subscription.id}: renewal in flight (payment {stranded.id}); skipping")
                    results["skipped"] += 1
                    continue
                logger.warning(
                    f"Recovering stranded renewal {stranded.id} for subscription {subscription.id} (key {renewal_key})"
                )
                try:
                    async with ctx.with_transaction() as services:
                        await services.repo.payments.update(
                            stranded.id,
                            {"status": PaymentStatus.FAILED, "provider_metadata": {"recovered": "stranded_mid_flow"}},
                        )
                except Exception as recover_error:
                    # If we can't mark the stranded row FAILED, the unique index still blocks a
                    # fresh insert — skip this period and retry next run rather than crashing the
                    # loop (and looping on the same row forever).
                    logger.error(f"Failed to recover stranded renewal {stranded.id}: {recover_error}")
                    results["skipped"] += 1
                    continue

            # Transaction 2a: Create payment record
            amount = product.get_price_for(subscription.currency).amount
            try:
                async with ctx.with_transaction() as services:
                    payment = await services.repo.payments.create(
                        {
                            "user_id": subscription.user_id,
                            "product_id": subscription.product_id,
                            "provider_id": subscription.provider_id,
                            "amount": amount,
                            "currency": subscription.currency,
                            "status": PaymentStatus.CREATED,
                            "idempotency_key": renewal_key,
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
                            "timestamp": now,
                            "raw_data": {"subscription_id": str(subscription.id)},
                            "is_recurring": True,
                        }
                    )
            except IntegrityError:
                # A concurrent run already created the renewal payment for this period
                # (uq_payment_idempotency_key). Skip — the other run owns the charge.
                logger.warning(
                    f"Concurrent renewal create for subscription {subscription.id} (key {renewal_key}); skipping"
                )
                results["skipped"] += 1
                continue

            # NO TRANSACTION: External API call (2-5 seconds)
            provider = get_provider(subscription.provider_id, None, None, products)
            from yookassa import Payment as YooKassaPayment

            request = provider._build_payment_request(
                payment,
                return_url=None,
                description_prefix="Auto-renewal: ",
                payment_method_id=(
                    subscription.payment_method_id or subscription.recurring_details.get("payment_method_id")
                ),
            )
            response = YooKassaPayment.create(request, renewal_key)
            logger.info(f"YooKassa response for payment {payment_id}: status={response.status}, id={response.id}")
            succeeded = response.status == "succeeded"

            # Transaction 2b: Save result + advance dunning state
            analytics: tuple[str, dict] | None = None  # (event, extra props), captured after commit
            async with ctx.with_transaction() as services:
                new_status = PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED
                event_type = PaymentEventType.PAYMENT_SUCCEEDED if succeeded else PaymentEventType.PAYMENT_FAILED

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
                        "timestamp": now,
                        "raw_data": {"subscription_id": str(subscription.id)},
                        "is_recurring": True,
                    }
                )

                if succeeded:
                    # Reward (extends end_date + sets ACTIVE via top_up), then reset dunning state.
                    payment_obj = await services.repo.payments.get_by_id(payment_id)
                    if product and not payment_obj.was_rewarded:
                        await product.reward(payment_obj.user_id, payment_obj, {}, services.subscriptions)
                        await services.repo.payments.update(payment_id, {"was_rewarded": True})
                        # Reported by whichever path rewards — a webhook that got here first
                        # has already captured it.
                        analytics = ("payment_succeeded", {})
                    await services.repo.subscriptions.update(
                        subscription.id,
                        {
                            "status": SubscriptionStatus.ACTIVE,
                            "failed_renewal_count": 0,
                            "last_renewal_attempt_at": now,
                        },
                    )
                    results["success"] += 1
                    if was_past_due:
                        results["recovered"] += 1
                        dunning_events.append({"user_id": subscription.user_id, "kind": "recovered"})
                    logger.info(f"Successfully charged subscription {subscription.id}")
                else:
                    # Decline: advance the dunning state machine.
                    cancellation = getattr(response, "cancellation_details", None)
                    reason = getattr(cancellation, "reason", None) if cancellation is not None else None
                    revoked = reason == "permission_revoked"
                    new_count = (subscription.failed_renewal_count or 0) + 1
                    exhausted = new_count >= MAX_RENEWAL_ATTEMPTS
                    if revoked or exhausted:
                        sub_status = SubscriptionStatus.EXPIRED
                        results["dunning_expired"] += 1
                        dunning_events.append(
                            {
                                "user_id": subscription.user_id,
                                "kind": "expired",
                                "count": new_count,
                                "reason": "card revoked" if revoked else "retries exhausted",
                            }
                        )
                    else:
                        sub_status = SubscriptionStatus.PAST_DUE
                        results["past_due"] += 1
                        dunning_events.append({"user_id": subscription.user_id, "kind": "past_due", "count": new_count})
                    await services.repo.subscriptions.update(
                        subscription.id,
                        {
                            "status": sub_status,
                            "failed_renewal_count": new_count,
                            "last_renewal_attempt_at": now,
                        },
                    )
                    results["failed"] += 1
                    analytics = (
                        "payment_failed",
                        {"provider_id": subscription.provider_id, "reason": reason, "attempt": new_count},
                    )
                    logger.info(
                        f"Renewal declined for subscription {subscription.id}: -> {sub_status} "
                        f"(attempt {new_count}/{MAX_RENEWAL_ATTEMPTS}, reason={reason})"
                    )

            # Same event + props as the webhook path (PaymentsService), so revenue insights see
            # renewals; is_recurring=True is what marks them. Only after the commit, so a
            # rolled-back result is never reported.
            if analytics:
                event, extra = analytics
                posthog.capture(
                    distinct_id=str(subscription.user_id),
                    event=event,
                    properties={
                        "user_id": str(subscription.user_id),
                        "product_id": subscription.product_id,
                        "amount": amount,
                        "currency": subscription.currency,
                        "is_recurring": True,
                        "payment_id": str(payment_id),
                        **extra,
                    },
                )

        except Exception as e:
            logger.error(f"Failed to charge subscription {subscription.id}: {e}", exc_info=True)
            results["failed"] += 1

            # A transport failure may mean the card WAS charged (timeout after charge). Do NOT
            # advance the dunning counter or downgrade the sub on a bare exception — only mark the
            # payment FAILED and stamp the attempt time so retry-spacing applies and the stranded
            # recovery path re-fetches/re-attempts (idempotently) on the next run.
            try:
                async with ctx.with_transaction() as services:
                    if payment_id:
                        await services.repo.payments.update(
                            payment_id,
                            {"status": PaymentStatus.FAILED, "provider_metadata": {"error": str(e)}},
                        )
                    await services.repo.subscriptions.update(subscription.id, {"last_renewal_attempt_at": now})
            except Exception as update_error:
                logger.error(f"Failed to record renewal error for subscription {subscription.id}: {update_error}")

    # Handle Telegram Stars subscriptions (monitoring only)
    if telegram_stars_subs:
        try:
            async with ctx.with_transaction() as services:
                # Only a live native monthly sub renews at Telegram; weekly and yearly Stars are
                # one-time purchases that simply end (the same check cancel() makes).
                renewing, ending = [], []
                for sub in telegram_stars_subs:
                    user = await services.users.get_user_by_id(sub.user_id)
                    (renewing if is_native_stars_subscription(sub, products) else ending).append(user)
                parts = [f"⭐ <b>{len(telegram_stars_subs)} Stars subscriptions expiring</b>"]
                if renewing:
                    parts.append(f"Telegram renews these itself:\n{bullet_list(user_ref(user) for user in renewing)}")
                if ending:
                    parts.append(f"One-time, these end:\n{bullet_list(user_ref(user) for user in ending)}")
                await services.messages.queue_admin_broadcast(
                    "\n".join(parts) + f"\n{tags('stars')}",
                    silent=True,
                )
                results["skipped"] += len(telegram_stars_subs)
        except Exception as e:
            logger.error(f"Failed to send Telegram Stars notification: {e}")

    # Send summary notification
    if manually_charged_subs:
        try:
            async with ctx.with_transaction() as services:
                users = [await services.users.get_user_by_id(sub.user_id) for sub in manually_charged_subs]
                await services.messages.queue_admin_broadcast(
                    f"🔧 <b>Charging {len(manually_charged_subs)} expiring subscriptions</b>\n"
                    + bullet_list(user_ref(user) for user in users)
                    + f"\n{tags('charging')}",
                    silent=True,
                )
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")

    # Dunning summary: PAST_DUE entered / dunning-EXPIRED / recovered — the revenue-at-risk signals.
    if dunning_events:
        try:
            async with ctx.with_transaction() as services:
                lines, user_tags = [], []
                for ev in dunning_events:
                    user = await services.users.get_user_by_id(ev["user_id"])
                    handle = user_ref(user) if user else f"<code>{ev['user_id']}</code>"
                    if user:
                        user_tags.append(user_tag(user))
                    if ev["kind"] == "past_due":
                        lines.append(f"⚠️ Past due {handle} — attempt {ev['count']}/{MAX_RENEWAL_ATTEMPTS}")
                    elif ev["kind"] == "expired":
                        lines.append(f"🚫 Lost {handle} — {esc(ev['reason'])} after {ev['count']} attempts")
                    elif ev["kind"] == "recovered":
                        lines.append(f"✅ Recovered {handle} — renewal went through after past due")
                await services.messages.queue_admin_broadcast(
                    "💳 <b>Dunning</b>\n" + "\n".join(lines) + f"\n{tags('dunning', *user_tags)}"
                )
        except Exception as e:
            logger.error(f"Failed to send dunning notification: {e}")

    logger.info(
        f"Job completed: charge_expiring_subscriptions - Success: {results['success']}, Failed: {results['failed']}, "
        f"Skipped: {results['skipped']}, PastDue: {results['past_due']}, DunningExpired: {results['dunning_expired']}, "
        f"Recovered: {results['recovered']}"
    )
    return results


@inject_context
async def expire_outdated_subscriptions_job(ctx: WorkerContext, products: ProductCatalog) -> dict[str, int]:
    """Expire outdated subscriptions using transaction-per-subscription pattern.

    Transaction pattern (per subscription):
    - Transaction: Expire subscription + gather notification data (fast, <50ms)
    - NO external APIs, so this is simpler than charge_expiring_subscriptions_job

    Expires ACTIVE subs past their end_date, plus PAST_DUE subs whose dunning grace window has
    fully elapsed (end_date + GRACE_PERIOD) — the safety net that guarantees a stuck PAST_DUE row
    cannot grant free access forever if the renewal job stops selecting it.

    Args:
        ctx: Worker context for transaction management
        products: Product catalog implementation (app-specific)

    Returns:
        Dict with expired/total counts
    """
    logger.info("Job started: expire_outdated_subscriptions")
    now = datetime.now(UTC)

    # Transaction 1: Get list of subscriptions to expire (read-only)
    async with ctx.with_repo() as repo:
        expiring_subs = await repo.subscriptions.get_expirable_subscriptions(now, now - GRACE_PERIOD)

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
                await services.repo.subscriptions.update(
                    subscription.id, {"status": SubscriptionStatus.EXPIRED, "canceled_at": now}
                )

                # Get user for notification
                user = await services.users.get_user_by_id(subscription.user_id)

                # Get product info (gracefully handle missing products)
                product = products.get_product(subscription.product_id)
                product_name = product.name if product else subscription.product_id

                # Calculate duration
                duration_days = (subscription.end_date - subscription.start_date).days

                # Prepare admin message (flag dunning grace-expiry distinctly from natural expiry)
                grace_note = " · past-due grace elapsed" if subscription.status == SubscriptionStatus.PAST_DUE else ""
                admin_messages.append(f"{user_ref(user)} — {esc(product_name)}, {duration_days}d{grace_note}")

                expired_count += 1

            logger.info(f"Successfully expired subscription {subscription.id}")

        except Exception as e:
            logger.error(f"Failed to expire subscription {subscription.id}: {e}", exc_info=True)
            # This subscription failed, continue with next

    # Send consolidated admin notification (separate transaction)
    if admin_messages:
        try:
            async with ctx.with_transaction() as services:
                admin_message = (
                    f"⌛ <b>{expired_count} subscriptions expired</b>\n"
                    + bullet_list(admin_messages)
                    + f"\n{tags('expired')}"
                )
                await services.messages.queue_admin_broadcast(admin_message, silent=True)
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")

    logger.info(f"Job completed: expire_outdated_subscriptions - Expired: {expired_count}/{len(expiring_subs)}")
    return {"expired": expired_count, "total": len(expiring_subs)}

from core.infrastructure.arq import WorkerContext, inject_context
from core.infrastructure.arq.jobs.admin import (
    admin_broadcast_job,  # noqa: F401 — registered by worker.py
    daily_admin_statistics_job,  # noqa: F401 — registered by worker.py
)
from core.infrastructure.arq.jobs.broadcasts import user_broadcast_job  # noqa: F401 — registered by worker.py
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


async def charge_expiring_subscriptions_job(ctx):
    """App wrapper for core charge_expiring_subscriptions_job.

    Injects app-specific dependencies (products, yookassa_config).
    Core job has @inject_context, so this wrapper should not.
    """
    from app.domain import products
    from core.infrastructure.arq.jobs import charge_expiring_subscriptions_job as core_charge_job

    # Call core job with app-specific dependencies
    return await core_charge_job(ctx, products)


async def expire_outdated_subscriptions_job(ctx):
    """App wrapper for core expire_outdated_subscriptions_job.

    Injects app-specific dependencies (products).
    Core job has @inject_context, so this wrapper should not.
    """
    from app.domain import products
    from core.infrastructure.arq.jobs import expire_outdated_subscriptions_job as core_expire_job

    # Call core job with app-specific dependencies
    return await core_expire_job(ctx, products)


@inject_context
async def test_error_job(ctx: WorkerContext):
    """Test error handling in worker jobs."""
    raise Exception("Test error")


@inject_context
async def send_delayed_notification(ctx: WorkerContext, telegram_user_id: int, delay_seconds: int):
    """Send a delayed Telegram notification for demo purposes.

    Args:
        ctx: Worker context with bot access
        telegram_user_id: Telegram user ID to notify (int, not UUID)
        delay_seconds: How long the delay was (for message text)
    """
    from core.infrastructure.i18n import t

    logger.info(f"Job started: send_delayed_notification - telegram_user_id={telegram_user_id}, delay={delay_seconds}s")
    try:
        # Get user's locale from database
        async with ctx.with_transaction() as services:
            user = await services.users.get_by_telegram_id(telegram_user_id)
            lang = "en"
            if user:
                lang = user.language_code or user.tg_language_code or "en"

        # Get localized message
        message = t("demo.notification.message", lang, delay_seconds=delay_seconds)

        # Send directly via bot (no transaction needed for external API)
        await ctx.bot.send_message(
            chat_id=telegram_user_id,
            text=message,
            parse_mode="HTML",
        )
        logger.info(f"Job completed: send_delayed_notification - telegram_user_id={telegram_user_id}")
    except Exception as e:
        logger.error(f"Job failed: send_delayed_notification - {e}", exc_info=True)
        raise

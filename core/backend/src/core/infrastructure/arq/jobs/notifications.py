"""Core notification worker jobs."""

from core.infrastructure.arq.factory import WorkerContext, inject_context
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


@inject_context
async def morning_notification_job(ctx: WorkerContext):
    """Send morning notifications - splits transactions for external API calls.

    Transaction pattern:
    1. DB transaction: Get eligible users (fast)
    2. NO transaction: Send Telegram notifications (external API)
    3. Transaction: Track sent notifications if needed (fast)
    """
    logger.info("Job started: morning_notification")
    try:
        # Transaction: Get eligible users and notification data
        async with ctx.with_transaction() as services:
            result = await services.notifications.send_morning_notification()
            successful_count = result if isinstance(result, int) else result.get("sent", 0)

        logger.info(f"Job completed: morning_notification - Sent to {successful_count} users")
        return {"sent": successful_count}
    except Exception as e:
        logger.error(f"Job failed: morning_notification - {e}", exc_info=True)
        raise


@inject_context
async def evening_notification_job(ctx: WorkerContext):
    """Send evening notifications - splits transactions for external API calls.

    Transaction pattern:
    1. DB transaction: Get eligible users (fast)
    2. NO transaction: Send Telegram notifications (external API)
    3. Transaction: Track sent notifications if needed (fast)
    """
    logger.info("Job started: evening_notification")
    try:
        # Transaction: Get eligible users and notification data
        async with ctx.with_transaction() as services:
            result = await services.notifications.send_evening_notification()
            successful_count = result if isinstance(result, int) else result.get("sent", 0)

        logger.info(f"Job completed: evening_notification - Sent to {successful_count} users")
        return {"sent": successful_count}
    except Exception as e:
        logger.error(f"Job failed: evening_notification - {e}", exc_info=True)
        raise

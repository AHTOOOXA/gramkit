"""Core balance worker jobs."""

from core.infrastructure.arq.factory import WorkerContext, inject_context
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


@inject_context
async def topup_daily_chat_messages_job(ctx: WorkerContext):
    """Top up daily chat messages for free users (single bulk UPDATE query).

    Transaction pattern:
    - Single transaction: Bulk UPDATE (fast, <100ms)
    - No external APIs, safe to use single transaction
    """
    logger.info("Job started: topup_daily_chat_messages")
    try:
        async with ctx.with_transaction() as services:
            topup_count = await services.balance.topup_daily_chat_messages()

        logger.info(f"Job completed: topup_daily_chat_messages - {topup_count} users affected")
        return {"topup_count": topup_count}
    except Exception as e:
        logger.error(f"Job failed: topup_daily_chat_messages - {e}", exc_info=True)
        raise

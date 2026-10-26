"""Core admin-notification worker jobs: the generic admin broadcast and the daily owner digest."""

from core.infrastructure.arq.factory import WorkerContext, inject_context
from core.infrastructure.logging import get_logger
from core.infrastructure.telegram.admin_messages import send_admin_message
from core.services.admin_metrics import digest_row_fns

logger = get_logger(__name__)


@inject_context
async def admin_broadcast_job(ctx: WorkerContext, text: str, rich_html: str | None = None, silent: bool = False):
    """Send an admin message (Telegram HTML, optional rich body) to all owners.

    Transaction pattern:
    - NO transaction: Send Telegram messages directly (external API)
    - Admin broadcasts are typically small (1-5 admins), so no DB tracking needed
    """
    logger.info(f"Job started: admin_broadcast - Text length: {len(text)}, rich: {rich_html is not None}")
    sent = await send_admin_message(ctx.bot, text, rich_html=rich_html, silent=silent)
    logger.info(f"Job completed: admin_broadcast - Sent to {sent} admins")
    return {"sent": sent}


@inject_context
async def daily_admin_statistics_job(ctx: WorkerContext):
    """Send the daily owner digest (``services.statistics``) to all owners.

    Apps schedule it in their worker (``cron(daily_admin_statistics_job, minute=55, hour=1)``: the
    end of the 02:00-UTC day). A routine digest is silent; one that failed to gather its numbers
    is an alert, so it sounds.

    Transaction pattern:
    1. Transaction: Gather statistics (fast, <100ms)
    2. NO transaction: Send via bot (external API)
    """
    logger.info("Job started: daily_admin_statistics")
    if not digest_row_fns():
        # Fine for an app that adds nothing; for one that does, its rows are missing because
        # register_admin_metrics() didn't run in this process (setup_infrastructure()).
        logger.info("daily_admin_statistics: no app digest rows registered (core rows only)")
    try:
        async with ctx.with_transaction() as services:
            digest = await services.statistics.get_daily_digest()
            text, rich_html = services.statistics.format_daily_digest(digest)

        sent = await send_admin_message(ctx.bot, text, rich_html=rich_html, silent=digest.error is None)
        logger.info(f"Job completed: daily_admin_statistics - Sent to {sent} admins")
        return {"sent": sent}
    except Exception as e:
        logger.error(f"Job failed: daily_admin_statistics - {e}", exc_info=True)
        raise

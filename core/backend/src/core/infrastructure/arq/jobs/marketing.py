"""Core marketing-links worker job: hourly owner alerts about the app's marketing links.

Apps register it in their worker (``job_functions`` + ``cron(..., minute=20)``). Alerts go to
``RBAC__OWNER_IDS`` through ``send_admin_message``; with no owners configured nothing is sent.
"""

from core.infrastructure.arq.factory import WorkerContext, inject_context
from core.infrastructure.logging import get_logger
from core.infrastructure.telegram.admin_messages import send_admin_message

logger = get_logger(__name__)


@inject_context
async def marketing_links_alerts_job(ctx: WorkerContext):
    """Hourly: tell the owners about their marketing links — first user, first payment, and a
    digest on days 1, 7 and 14 after the post went out. Each alert goes out once per link."""
    async with ctx.with_transaction() as services:
        alerts = await services.marketing_links.pending_alerts()
    for alert in alerts:
        await send_admin_message(ctx.bot, alert.text, silent=alert.silent)
    if alerts:
        async with ctx.with_transaction() as services:
            await services.marketing_links.mark_alerts_sent(alerts)
    logger.info(f"Job completed: marketing_links_alerts - {len(alerts)} alerts")
    return {"sent": len(alerts)}

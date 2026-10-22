"""Core admin-notification worker job."""

from core.infrastructure.arq.factory import WorkerContext, inject_context
from core.infrastructure.logging import get_logger
from core.infrastructure.telegram.admin_messages import send_admin_message

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

"""Webhook utility functions for error handling and dead letter queue."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.infrastructure.database.models.webhooks import FailedWebhook

logger = logging.getLogger(__name__)


async def store_failed_webhook(
    session: AsyncSession,
    provider: str,
    payload: dict,
    error: str,
    error_type: str,
) -> None:
    """Store failed webhook in dead letter queue."""
    try:
        failed_webhook = FailedWebhook(provider=provider, payload=payload, error_message=error, error_type=error_type)
        session.add(failed_webhook)
        await session.flush()
        logger.info(f"Stored failed webhook in DLQ: {provider} - {error_type}")
    except Exception as e:
        logger.error(f"Failed to store failed webhook in DLQ: {e}", exc_info=True)


async def alert_webhook_failure(payload: dict, error: Exception, severity: str) -> None:
    """Send alert for webhook failure."""
    alert_message = {
        "alert_type": "webhook_failure",
        "severity": severity,
        "payment_id": payload.get("payment_id") or payload.get("object", {}).get("id"),
        "error": str(error),
    }

    if severity == "critical":
        logger.critical(f"CRITICAL webhook failure: {alert_message}")
    else:
        logger.error(f"Webhook failure: {alert_message}")

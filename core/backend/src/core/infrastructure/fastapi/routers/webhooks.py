"""Payment webhook routes for external payment providers."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLTimeoutError

from core.infrastructure.database.models.enums import PaymentProvider
from core.infrastructure.fastapi.dependencies import get_services
from core.infrastructure.fastapi.webhooks import alert_webhook_failure, store_failed_webhook
from core.infrastructure.logging import get_logger
from core.infrastructure.webhooks.telegram_validator import TelegramWebhookValidator
from core.infrastructure.webhooks.yookassa_validator import YooKassaWebhookValidator
from core.services.requests import CoreRequestsService

logger = get_logger(__name__)

# YooKassa webhook router
yookassa_router = APIRouter(prefix="/yookassa")


@yookassa_router.post("/webhook")
async def yookassa_webhook(
    request: Request,
    services: CoreRequestsService = Depends(get_services),
):
    """
    Webhook endpoint for YooKassa payment confirmations.

    Returns:
        - 200 OK: Webhook processed successfully
        - 400 Bad Request: Invalid JSON, missing fields, permanent business errors
        - 500 Internal Error: Transient business errors, unknown errors
        - 503 Service Unavailable: Infrastructure errors (DB, Redis)
    """
    try:
        # Parse JSON payload
        try:
            payload = await request.json()
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON payload: {e}"
            logger.error(error_msg)
            await alert_webhook_failure(payload={}, error=e, severity="error")
            return Response(status_code=400, content=error_msg)

        logger.info(f"Received YooKassa webhook payload: {payload}")

        # Validate signature (if secret configured)
        yookassa_secret = getattr(request.app.state, "yookassa_webhook_secret", None)
        if yookassa_secret:
            validator = YooKassaWebhookValidator(yookassa_secret)
            authorization_header = request.headers.get("Authorization")

            try:
                validator.validate_signature(payload, authorization_header)
                logger.info("YooKassa webhook signature validated")
            except HTTPException as e:
                logger.warning(f"Invalid YooKassa webhook signature: {e.detail}")
                await alert_webhook_failure(
                    payload=payload, error=Exception(f"Invalid signature: {e.detail}"), severity="critical"
                )
                raise

        # Process payment callback
        await services.payments.process_callback(payload, provider_id="YOOKASSA")

        logger.info("YooKassa webhook processed successfully")
        return Response(status_code=200)

    except (OperationalError, SQLTimeoutError, RedisConnectionError, RedisTimeoutError) as e:
        # Infrastructure errors - provider should retry
        error_msg = f"Infrastructure error processing YooKassa webhook: {e}"
        logger.error(error_msg, exc_info=True)
        await store_failed_webhook(
            session=services.repo.session,
            provider="YOOKASSA",
            payload=payload if "payload" in locals() else {},
            error=str(e),
            error_type="infrastructure",
        )
        await alert_webhook_failure(payload=payload if "payload" in locals() else {}, error=e, severity="critical")
        return Response(status_code=503, content="Service temporarily unavailable")

    except ValueError as e:
        # Business logic errors - classify as permanent or transient
        error_msg = str(e).lower()

        # Permanent errors - no retry
        if any(keyword in error_msg for keyword in ["not found", "invalid product", "invalid payment"]):
            logger.error(f"Permanent error in YooKassa webhook: {e}", exc_info=True)
            await store_failed_webhook(
                session=services.repo.session,
                provider="YOOKASSA",
                payload=payload if "payload" in locals() else {},
                error=str(e),
                error_type="permanent",
            )
            await alert_webhook_failure(payload=payload if "payload" in locals() else {}, error=e, severity="error")
            return Response(status_code=400, content=str(e))

        # Transient errors - provider should retry
        logger.error(f"Transient error in YooKassa webhook: {e}", exc_info=True)
        await store_failed_webhook(
            session=services.repo.session,
            provider="YOOKASSA",
            payload=payload if "payload" in locals() else {},
            error=str(e),
            error_type="transient",
        )
        await alert_webhook_failure(payload=payload if "payload" in locals() else {}, error=e, severity="error")
        return Response(status_code=500, content="Internal server error")

    except Exception as e:
        # Unknown errors - provider should retry
        logger.error(f"Unknown error processing YooKassa webhook: {e}", exc_info=True)
        await store_failed_webhook(
            session=services.repo.session,
            provider="YOOKASSA",
            payload=payload if "payload" in locals() else {},
            error=str(e),
            error_type="unknown",
        )
        await alert_webhook_failure(payload=payload if "payload" in locals() else {}, error=e, severity="critical")
        return Response(status_code=500, content="Internal server error")


# Telegram Stars webhook router
telegram_stars_router = APIRouter(prefix="/telegram-stars")


@telegram_stars_router.post("/webhook")
async def telegram_stars_webhook(
    request: Request,
    services: CoreRequestsService = Depends(get_services),
):
    """
    Webhook endpoint for Telegram Stars payment confirmations from web interface.

    This endpoint receives payment notifications from Telegram when payments
    are made through the web interface and processes them through the unified
    payment system.

    Returns:
        - 200 OK: Webhook processed successfully
        - 400 Bad Request: Invalid JSON, missing fields, permanent business errors
        - 500 Internal Error: Transient business errors, unknown errors
        - 503 Service Unavailable: Infrastructure errors (DB, Redis)
    """
    try:
        # Parse JSON payload
        try:
            payload = await request.json()
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON payload: {e}"
            logger.error(error_msg)
            await alert_webhook_failure(payload={}, error=e, severity="error")
            return Response(status_code=400, content=error_msg)

        logger.info(f"Received Telegram Stars webhook payload: {payload}")

        # Validate secret token (if secret configured)
        telegram_secret = getattr(request.app.state, "telegram_webhook_secret", None)
        if telegram_secret:
            validator = TelegramWebhookValidator(telegram_secret)
            secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

            try:
                validator.validate_secret(secret_header)
                logger.info("Telegram webhook secret validated")
            except HTTPException as e:
                logger.warning(f"Invalid Telegram webhook secret: {e.detail}")
                await alert_webhook_failure(
                    payload=payload, error=Exception(f"Invalid secret: {e.detail}"), severity="critical"
                )
                raise

        # Process payment callback
        await services.payments.process_callback(payload, provider_id=PaymentProvider.TELEGRAM_STARS.value)

        logger.info("Telegram Stars webhook processed successfully")
        return Response(status_code=200)

    except (OperationalError, SQLTimeoutError, RedisConnectionError, RedisTimeoutError) as e:
        # Infrastructure errors - provider should retry
        error_msg = f"Infrastructure error processing Telegram Stars webhook: {e}"
        logger.error(error_msg, exc_info=True)
        await store_failed_webhook(
            session=services.repo.session,
            provider="TELEGRAM_STARS",
            payload=payload if "payload" in locals() else {},
            error=str(e),
            error_type="infrastructure",
        )
        await alert_webhook_failure(payload=payload if "payload" in locals() else {}, error=e, severity="critical")
        return Response(status_code=503, content="Service temporarily unavailable")

    except ValueError as e:
        # Business logic errors - classify as permanent or transient
        error_msg = str(e).lower()

        # Permanent errors - no retry
        if any(keyword in error_msg for keyword in ["not found", "invalid product", "invalid payment"]):
            logger.error(f"Permanent error in Telegram Stars webhook: {e}", exc_info=True)
            await store_failed_webhook(
                session=services.repo.session,
                provider="TELEGRAM_STARS",
                payload=payload if "payload" in locals() else {},
                error=str(e),
                error_type="permanent",
            )
            await alert_webhook_failure(payload=payload if "payload" in locals() else {}, error=e, severity="error")
            return Response(status_code=400, content=str(e))

        # Transient errors - provider should retry
        logger.error(f"Transient error in Telegram Stars webhook: {e}", exc_info=True)
        await store_failed_webhook(
            session=services.repo.session,
            provider="TELEGRAM_STARS",
            payload=payload if "payload" in locals() else {},
            error=str(e),
            error_type="transient",
        )
        await alert_webhook_failure(payload=payload if "payload" in locals() else {}, error=e, severity="error")
        return Response(status_code=500, content="Internal server error")

    except Exception as e:
        # Unknown errors - provider should retry
        logger.error(f"Unknown error processing Telegram Stars webhook: {e}", exc_info=True)
        await store_failed_webhook(
            session=services.repo.session,
            provider="TELEGRAM_STARS",
            payload=payload if "payload" in locals() else {},
            error=str(e),
            error_type="unknown",
        )
        await alert_webhook_failure(payload=payload if "payload" in locals() else {}, error=e, severity="critical")
        return Response(status_code=500, content="Internal server error")

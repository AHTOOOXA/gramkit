"""Core admin command handlers for Telegram bot."""

from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command

from core.infrastructure.config import settings
from core.infrastructure.logging import get_logger
from core.schemas.users import UserSchema
from core.services.requests import CoreRequestsService

router = Router()
logger = get_logger(__name__)


@router.message(Command("backup"))
async def backup_command(message: types.Message, user: UserSchema, services: CoreRequestsService):
    """Handler for /backup command. Creates database backup and sends it to the admin."""
    # Check if user is admin
    if not user.telegram_id or user.telegram_id not in settings.rbac.owner_ids:
        await message.answer("You don't have permission to use this command")
        return

    await message.answer("⏳ Creating database backup...")

    try:
        # Queue backup job (sends file when done)
        await services.worker.enqueue_job(
            "backup_database_job",
            requester_telegram_id=user.telegram_id,
        )

        await message.answer("✅ Backup job queued! You'll receive the file shortly.")

        logger.info(f"Backup job queued by admin {user.telegram_id}")

    except Exception as e:
        logger.error(f"Failed to queue backup job: {e}", exc_info=True)
        await message.answer(f"❌ Failed to start backup: {str(e)}")

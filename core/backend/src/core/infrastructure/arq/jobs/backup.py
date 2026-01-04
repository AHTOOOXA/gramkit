"""Core database backup worker jobs."""

from core.infrastructure.arq.factory import WorkerContext, inject_context
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


@inject_context
async def backup_database_job(ctx: WorkerContext, requester_telegram_id: int):
    """Create database backup and send to requester via Telegram.

    Transaction pattern:
    - NO transaction: Uses subprocess for pg_dump (external process)
    - NO transaction: Send via bot (external API)
    """
    from aiogram.types import FSInputFile

    from core.infrastructure.config import settings
    from core.scripts.common.backup_database import create_backup

    logger.info(f"Job started: backup_database - Requester: {requester_telegram_id}")

    try:
        # Create backup (no transaction - uses subprocess)
        result = await create_backup(
            db_config=settings.db,
            app_name=settings.app_name,
            compress=True,
        )

        if not result.success:
            error_msg = f"❌ Backup failed: {result.error}"
            await ctx.bot.send_message(requester_telegram_id, error_msg)
            logger.error(f"Job failed: backup_database - {result.error}")
            return {"success": False, "error": result.error}

        # Send file to requester (no transaction - external API)
        caption = (
            f"📦 Database Backup\n\n"
            f"🏷 App: {result.app_name}\n"
            f"💾 Size: {result.size_display}\n"
            f"🗂 Tables: {result.tables_count}\n"
            f"⏱ Time: {result.duration_seconds:.1f}s"
        )

        await ctx.bot.send_document(
            chat_id=requester_telegram_id,
            document=FSInputFile(result.file_path, filename=result.filename),
            caption=caption,
        )

        logger.info(
            f"Job completed: backup_database - "
            f"File: {result.filename}, Size: {result.size_mb:.2f}MB, Duration: {result.duration_seconds:.1f}s"
        )

        return {
            "success": True,
            "file_path": result.file_path,
            "size_mb": result.size_mb,
            "tables_count": result.tables_count,
        }

    except Exception as e:
        logger.error(f"Job failed: backup_database - {e}", exc_info=True)
        try:
            await ctx.bot.send_message(requester_telegram_id, f"❌ Backup failed: {str(e)}")
        except Exception:
            pass
        raise


@inject_context
async def scheduled_backup_job(ctx: WorkerContext):
    """Scheduled daily database backup - sends to all owners via Telegram.

    Transaction pattern:
    - NO transaction: Uses subprocess for pg_dump (external process)
    - NO transaction: Send via bot (external API)
    """
    import asyncio

    from aiogram.types import FSInputFile

    from core.infrastructure.config import settings
    from core.scripts.common.backup_database import create_backup

    logger.info("Job started: scheduled_backup")

    try:
        # Create backup
        result = await create_backup(
            db_config=settings.db,
            app_name=settings.app_name,
            compress=True,
        )

        if not result.success:
            # Notify admins of failure
            error_msg = f"❌ Scheduled backup failed: {result.error}"
            for owner_id in settings.rbac.owner_ids:
                try:
                    await ctx.bot.send_message(owner_id, error_msg)
                except Exception:
                    pass
            logger.error(f"Job failed: scheduled_backup - {result.error}")
            return {"success": False, "error": result.error}

        # Send to all owners via Telegram
        caption = (
            f"🗓 Scheduled Backup\n\n"
            f"🏷 App: {result.app_name}\n"
            f"💾 Size: {result.size_display}\n"
            f"🗂 Tables: {result.tables_count}\n"
            f"⏱ Time: {result.duration_seconds:.1f}s"
        )

        document = FSInputFile(result.file_path, filename=result.filename)

        for owner_id in settings.rbac.owner_ids:
            try:
                await ctx.bot.send_document(
                    chat_id=owner_id,
                    document=document,
                    caption=caption,
                )
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to send backup to owner {owner_id}: {e}")

        logger.info(f"Job completed: scheduled_backup - File: {result.filename}, Size: {result.size_mb:.2f}MB")

        return {
            "success": True,
            "file_path": result.file_path,
            "size_mb": result.size_mb,
        }

    except Exception as e:
        logger.error(f"Job failed: scheduled_backup - {e}", exc_info=True)
        # Try to notify admins
        for owner_id in settings.rbac.owner_ids:
            try:
                await ctx.bot.send_message(owner_id, f"❌ Scheduled backup failed: {str(e)}")
            except Exception:
                pass
        raise

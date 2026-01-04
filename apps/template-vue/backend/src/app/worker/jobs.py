from core.infrastructure.arq import WorkerContext, inject_context
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


@inject_context
async def admin_broadcast_job(ctx: WorkerContext, text: str):
    """Send admin broadcast message - uses bot directly (no transaction for external API).

    Transaction pattern:
    - NO transaction: Send Telegram messages directly (external API)
    - Admin broadcasts are typically small (3-5 admins), so no DB tracking needed
    """
    logger.info(f"Job started: admin_broadcast - Text length: {len(text)}")
    try:
        # Send directly via bot (no transaction)
        import asyncio

        from core.infrastructure.config import settings

        count = 0
        for admin_id in settings.rbac.owner_ids:
            try:
                await ctx.bot.send_message(admin_id, text)
                count += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Failed to send to admin {admin_id}: {e}")

        logger.info(f"Job completed: admin_broadcast - Sent to {count}/{len(settings.rbac.owner_ids)} admins")
        return {"sent": count}
    except Exception as e:
        logger.error(f"Job failed: admin_broadcast - {e}", exc_info=True)
        raise


@inject_context
async def user_broadcast_job(ctx: WorkerContext, broadcast_data: dict, requester_telegram_id: int):
    """Send broadcast message to all users - splits transactions for external API.

    Transaction pattern:
    1. Transaction: Get all users (fast, <100ms)
    2. NO transaction: Send Telegram messages (external API, 30-250 seconds)
    3. Transaction: Send completion notification to admin (fast, <100ms)

    Args:
        broadcast_data: Dict containing message details (type, content, keyboard)
        requester_telegram_id: Telegram ID of admin who requested broadcast
    """
    import asyncio

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from app.tgbot.keyboards.keyboards import command_keyboard
    from core.infrastructure.config import settings
    from core.infrastructure.i18n import i18n

    logger.info(f"Job started: user_broadcast - Type: {broadcast_data.get('message_type')}")

    try:
        # Transaction 1: Get all users
        async with ctx.with_transaction() as services:
            all_users = await services.users.get_all()
            # Extract just the data we need (avoid holding user objects)
            user_data = [(u.id, u.telegram_id) for u in all_users if u.telegram_id]

        total_users = len(user_data)
        logger.info(f"Broadcasting to {total_users} users")

        # Prepare keyboard based on selection
        keyboard = None
        keyboard_type = broadcast_data.get("keyboard_type")
        if keyboard_type == "main":
            keyboard = command_keyboard()
        elif keyboard_type == "daily":
            kb = InlineKeyboardBuilder()
            kb.button(
                text=i18n("tarot.open_app_button"),
                url=f"{settings.web.app_url}?startapp=r-dailycardnotification",
            )
            kb.adjust(1)
            keyboard = kb.as_markup()

        # NO TRANSACTION: Send messages to all users
        successful_count = 0
        message_type = broadcast_data.get("message_type", "text")

        if message_type == "text":
            # Text broadcast
            message_text = (
                broadcast_data.get("message_html")
                if broadcast_data.get("has_formatting")
                else broadcast_data.get("message_text", "")
            )
            parse_mode = "HTML" if broadcast_data.get("has_formatting") else None

            for user_id, telegram_id in user_data:
                try:
                    await ctx.bot.send_message(
                        telegram_id,
                        message_text,
                        reply_markup=keyboard,
                        parse_mode=parse_mode,
                    )
                    successful_count += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"Failed to send to user {user_id} (telegram_id={telegram_id}): {e}")

        elif message_type == "photo":
            # Photo broadcast
            caption = (
                broadcast_data.get("caption_html")
                if broadcast_data.get("has_caption_formatting")
                else broadcast_data.get("caption", "")
            )
            parse_mode = "HTML" if broadcast_data.get("has_caption_formatting") else None
            file_id = broadcast_data.get("photo_file_id")

            for user_id, telegram_id in user_data:
                try:
                    await ctx.bot.send_photo(
                        telegram_id,
                        photo=file_id,
                        caption=caption,
                        reply_markup=keyboard,
                        parse_mode=parse_mode,
                    )
                    successful_count += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"Failed to send to user {user_id} (telegram_id={telegram_id}): {e}")

        # Transaction 2: Send completion notification to requester
        try:
            success_rate = (successful_count / total_users * 100) if total_users > 0 else 0
            completion_message = (
                f"✅ Broadcast complete!\n"
                f"Successfully delivered to {successful_count} out of {total_users} users "
                f"({success_rate:.1f}% success rate)."
            )
            await ctx.bot.send_message(requester_telegram_id, completion_message)
        except Exception as e:
            logger.error(f"Failed to send completion notification to {requester_telegram_id}: {e}")

        logger.info(
            f"Job completed: user_broadcast - Sent to {successful_count}/{total_users} users ({success_rate:.1f}%)"
        )
        return {"sent": successful_count, "total": total_users, "success_rate": success_rate}

    except Exception as e:
        logger.error(f"Job failed: user_broadcast - {e}", exc_info=True)
        # Try to notify admin of failure
        try:
            await ctx.bot.send_message(
                requester_telegram_id, f"❌ Broadcast failed: {str(e)}\n\nPlease check logs for details."
            )
        except Exception:
            pass
        raise


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
async def daily_admin_statistics_job(ctx: WorkerContext):
    """Send daily app usage statistics to admins.

    Transaction pattern:
    1. Transaction: Gather statistics (fast, <100ms)
    2. NO transaction: Send via bot (external API)
    """
    logger.info("Job started: daily_admin_statistics")
    try:
        # Transaction: Gather statistics
        async with ctx.with_transaction() as services:
            stats = await services.statistics.get_daily_statistics()
            message = services.statistics.format_statistics_message(stats)

        # NO TRANSACTION: Send admin broadcast (external API)
        import asyncio

        from core.infrastructure.config import settings

        count = 0
        for admin_id in settings.rbac.owner_ids:
            try:
                await ctx.bot.send_message(admin_id, message)
                count += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Failed to send to admin {admin_id}: {e}")

        logger.info(f"Job completed: daily_admin_statistics - Sent to {count}/{len(settings.rbac.owner_ids)} admins")

        return {"sent": count}
    except Exception as e:
        logger.error(f"Job failed: daily_admin_statistics - {e}", exc_info=True)
        raise


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

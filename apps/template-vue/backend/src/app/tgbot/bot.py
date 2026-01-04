"""Tarot Telegram bot application."""

import asyncio

from app.infrastructure import setup_infrastructure

setup_infrastructure()

from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService
from app.tgbot.handlers import routers_list
from core.infrastructure.config import settings
from core.infrastructure.dependencies import Dependencies
from core.infrastructure.logging import get_logger
from core.infrastructure.telegram import create_tg_bot

logger = get_logger(__name__)


async def on_startup(bot, owner_ids: list[int]):
    for owner_id in owner_ids:
        try:
            await bot.send_message(owner_id, "Bot has been started")
        except Exception as e:
            logger.warning(f"Could not send startup message to owner {owner_id}: {e}")


async def main():
    logger.info("Starting bot")

    # Create bot with auto-managed dependencies
    bot, dp, deps = await create_tg_bot(
        config=settings.bot,
        db_config=settings.db,
        redis_config=settings.redis,
        repo_class=RequestsRepo,
        service_class=RequestsService,
        routers=routers_list,
        dependencies=Dependencies(
            redis_config=settings.redis,
            rabbit_config=settings.rabbit,
        ),
    )

    await on_startup(bot, settings.rbac.owner_ids)

    try:
        logger.info("Starting polling")
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Shutting down")
        await bot.session.close()
        await deps.close()
        await dp["engine"].dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot has been stopped")

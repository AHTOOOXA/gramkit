from collections.abc import AsyncGenerator

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from core.infrastructure.config import settings


async def get_bot() -> AsyncGenerator[Bot]:
    bot = Bot(token=settings.bot.token, default=DefaultBotProperties(parse_mode="Markdown"))
    try:
        yield bot
    finally:
        await bot.session.close()

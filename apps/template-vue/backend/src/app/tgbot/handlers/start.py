"""Tarot bot start handlers."""

from functools import partial

from aiogram import Router
from aiogram.filters import Command, CommandStart

from app.tgbot.keyboards.keyboards import command_keyboard
from core.infrastructure.config import settings
from core.infrastructure.telegram.handlers.start import ref_command as core_ref_command
from core.infrastructure.telegram.handlers.start import start_command as core_start_command

router = Router()

# Configure core start handler for Tarot app
tarot_start_handler = partial(
    core_start_command,
    menu_i18n_key="tarot.menu",
    keyboard_factory=command_keyboard,
    posthog_event="bot_command_start",
)

# Configure core ref handler for Tarot app
tarot_ref_handler = partial(
    core_ref_command,
    bot_url=settings.bot.url,
    web_app_path="/app",
    referral_prefix="r-",
)

# Register configured handlers
router.message.register(tarot_start_handler, CommandStart())
router.message.register(tarot_ref_handler, Command("ref"))

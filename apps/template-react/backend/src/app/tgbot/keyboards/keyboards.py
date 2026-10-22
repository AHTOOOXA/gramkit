from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.infrastructure.config import settings
from core.infrastructure.i18n import i18n


# BOT
def command_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text=i18n("app.open_app_button"), web_app=WebAppInfo(url=f"{settings.web.frontend_url}"))
    kb.adjust(1)
    return kb.as_markup()

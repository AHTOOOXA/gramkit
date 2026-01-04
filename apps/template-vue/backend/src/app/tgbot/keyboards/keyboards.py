from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.infrastructure.config import settings
from core.infrastructure.i18n import i18n


# BOT
def command_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text=i18n("tarot.open_app_button"), web_app=WebAppInfo(url=f"{settings.web.frontend_url}"))
    kb.adjust(1)
    return kb.as_markup()


# WEBHOOK
def share_reading_result_kb(reading_id: str, invite_code: str):
    kb = InlineKeyboardBuilder()
    kb.button(
        text=i18n("tarot.share_open_reading_button"),
        url=f"{settings.web.app_url}?startapp=r-share-i-{invite_code}-p-reading_{reading_id}",
    )
    kb.button(
        text=i18n("tarot.share_message_button"),
        url=f"{settings.web.app_url}?startapp=r-share-i-{invite_code}",
    )
    kb.adjust(1)
    return kb.as_markup()


def keygo_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(
        text=i18n("tarot.open_app_button"),
        url=f"{settings.web.app_url}?startapp=r-keygo-m-keygo",
    )
    kb.adjust(1)
    return kb.as_markup()

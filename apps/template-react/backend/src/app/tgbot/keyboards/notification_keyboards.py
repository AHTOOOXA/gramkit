from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.infrastructure.config import settings
from core.infrastructure.i18n import i18n


# Helper function to create standard notification keyboards
def create_notification_keyboard(key: str, startapp_param: str, locale: str | None = None):
    """
    Create a standard notification keyboard with a single button

    Args:
        key: The i18n key for the button text
        startapp_param: The startapp parameter for the URL
        locale: Optional locale for i18n
    """
    kb = InlineKeyboardBuilder()
    kb.button(
        text=i18n(key, locale=locale),
        url=f"{settings.web.app_url}?startapp={startapp_param}",
    )
    kb.adjust(1)
    return kb.as_markup()


# Example notification keyboard (see ExampleDailyNotification.get_keyboard_func)
def daily_notification_kb(locale: str | None = None):
    return create_notification_keyboard("app.open_app_button", "r-dailynotification", locale)


# Promotional Broadcast Main Keyboard - Worker Safe Version
def promotional_broadcast_main_kb(locale: str | None = None, button_text: str | None = None):
    """Worker-safe promotional broadcast main keyboard that doesn't depend on i18n"""
    kb = InlineKeyboardBuilder()
    kb.button(
        text=button_text or "Open App",  # Use custom text or fallback
        url=f"{settings.web.app_url}",
    )
    kb.adjust(1)
    return kb.as_markup()

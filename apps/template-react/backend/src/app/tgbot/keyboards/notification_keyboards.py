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


# Daily Card Notification
def daily_card_notification_kb(locale: str | None = None):
    return create_notification_keyboard("notification_buttons.daily_card", "r-dailycardnotification", locale)


# Premium Notification
def premium_notification_kb(locale: str | None = None):
    return create_notification_keyboard("notification_buttons.premium", "r-premium", locale)


# Self Discovery Journey Notification
def self_discovery_journey_notification_kb(locale: str | None = None):
    return create_notification_keyboard("notification_buttons.self_discovery", "r-selfdiscovery", locale)


# Teasing Notification
def teasing_notification_kb(locale: str | None = None):
    return create_notification_keyboard("notification_buttons.teasing", "r-teasing", locale)


# Emotional Wellness Notification
def emotional_wellness_notification_kb(locale: str | None = None):
    return create_notification_keyboard("notification_buttons.emotional_wellness", "r-emotionalwellness", locale)


# Lapsed Recovery Notification
def lapsed_recovery_notification_kb(locale: str | None = None):
    return create_notification_keyboard("notification_buttons.welcome_back", "r-lapsedrecovery", locale)


# Out of Readings Follow Up Notification
def out_of_readings_follow_up_kb(locale: str | None = None):
    return create_notification_keyboard(
        "notification_buttons.out_of_readings_follow_up", "r-outofreadingsfollowup", locale
    )


# Out of Readings Follow Up 2 Notification
def out_of_readings_follow_up_2_kb(locale: str | None = None):
    return create_notification_keyboard(
        "notification_buttons.out_of_readings_follow_up_2", "r-outofreadingsfollowup2", locale
    )


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

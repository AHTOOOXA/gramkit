from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.infrastructure.config import settings
from core.infrastructure.i18n import i18n, t


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
        # With a locale, translate into it: ``i18n(key, locale=...)`` ignores the locale whenever a
        # process-global translation is set (the webhook sets one per request, e.g. for a preview).
        text=t(key, locale) if locale else i18n(key),
        url=f"{settings.web.app_url}?startapp={startapp_param}",
    )
    kb.adjust(1)
    return kb.as_markup()


# Example notification keyboard (see ExampleDailyNotification.get_keyboard_func)
def daily_notification_kb(locale: str | None = None):
    return create_notification_keyboard("app.open_app_button", "r-dailynotification", locale)


def register_broadcast_keyboards() -> None:
    """Register this app's broadcast keyboard types with core (``setup_infrastructure`` calls this).

    ``daily``: the open-app button with the daily-notification link. Core provides ``main``
    (open the app with the composer's custom button text). Add your own types here; the
    admin composer offers the ``KeyboardType`` values of ``core.schemas.broadcasts``.
    """
    from core.services.broadcast_formatting import register_broadcast_keyboard

    register_broadcast_keyboard("daily", lambda _button_text, locale: daily_notification_kb(locale))

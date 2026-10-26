"""This app's broadcast keyboards in core's registry.

``setup_infrastructure()`` (run by every entrypoint at import) registers ``daily``; the admin
preview, send-now, the bot's ``/broadcast`` and the scheduled slot all build the keyboard
through core's ``build_keyboard_markup``, so they show the same localized button.
"""

import pytest
from arq.worker import Function

from app.tgbot.keyboards.notification_keyboards import daily_notification_kb
from core.infrastructure.config import settings
from core.infrastructure.i18n import i18n, t
from core.services.broadcast_formatting import build_keyboard_markup


def _button(markup):
    assert markup is not None
    [[button]] = markup.inline_keyboard
    return button


@pytest.fixture(autouse=True)
def app_started():
    """The webhook app module runs setup_infrastructure() at import (the root conftest imports it)."""
    import app.webhook.app  # noqa: F401


@pytest.mark.business_logic
class TestBroadcastKeyboards:
    @pytest.mark.parametrize("locale", ["en", "ru"])
    def test_daily_is_registered_and_localized(self, locale):
        markup = build_keyboard_markup({"keyboard_type": "daily"}, locale)

        assert markup == daily_notification_kb(locale)
        button = _button(markup)
        assert button.text == t("app.open_app_button", locale)
        assert button.url == f"{settings.web.app_url}?startapp=r-dailynotification"

    def test_daily_ignores_a_global_translation_in_another_locale(self):
        """The webhook sets a process-global translation per request; the builder must still use ``locale``."""
        i18n.update_locale("en")
        try:
            button = _button(build_keyboard_markup({"keyboard_type": "daily"}, "ru"))
        finally:
            i18n.reset_translation()
        assert button.text == t("app.open_app_button", "ru")

    def test_main_opens_the_app_with_the_custom_text(self):
        button = _button(build_keyboard_markup({"keyboard_type": "main", "keyboard_button_text": "Go"}, "en"))
        assert (button.text, button.url) == ("Go", settings.web.app_url)


@pytest.mark.business_logic
def test_scheduled_slots_send_the_core_promo_templates():
    from app.services.notifications import NotificationsService
    from core.services.notifications.broadcasts import EveningPromotionalBroadcast, MorningPromotionalBroadcast

    service = NotificationsService(None, None, None, None)

    assert service.get_morning_notifications_with_promotions()[0] is MorningPromotionalBroadcast
    assert service.get_evening_notifications_with_promotions()[0] is EveningPromotionalBroadcast


@pytest.mark.business_logic
def test_worker_registers_the_slot_crons_and_the_core_broadcast_job():
    from app.worker.worker import WorkerSettings
    from core.infrastructure.arq.jobs import (
        USER_BROADCAST_JOB_TIMEOUT,
        evening_notification_job,
        morning_notification_job,
        user_broadcast_job,
    )

    functions = {f.name: f for f in WorkerSettings.functions if isinstance(f, Function)}
    broadcast = functions["user_broadcast_job"]  # the name the API and the bot enqueue
    assert (broadcast.coroutine, broadcast.timeout_s) == (user_broadcast_job, USER_BROADCAST_JOB_TIMEOUT)
    crons = {c.coroutine: (c.minute, c.hour) for c in WorkerSettings.cron_jobs}
    assert crons[morning_notification_job] == (0, None)  # hourly: each user's local slot hour
    assert crons[evening_notification_job] == (0, None)

"""The app's own link codes are never acquisition (``app/domain/referrals.py``).

The notification button opens the Mini App with ``?startapp=r-<code>``; that code must be in
``INTERNAL_REFERRAL_CODES`` and reach core (``StartService`` / the Marketing screen) through
``CoreRequestsService(internal_referal_ids=...)``, or the app would store its own notification
as a user's acquisition source.
"""

from urllib.parse import parse_qs, urlparse

import pytest

from app.domain.referrals import INTERNAL_REFERRAL_CODES
from app.tgbot.keyboards.notification_keyboards import daily_notification_kb


@pytest.mark.business_logic
def test_the_notification_button_code_is_internal():
    [[button]] = daily_notification_kb("en").inline_keyboard
    [start_param] = parse_qs(urlparse(button.url).query)["startapp"]
    assert start_param.startswith("r-")
    assert start_param.removeprefix("r-") in INTERNAL_REFERRAL_CODES


@pytest.mark.business_logic
async def test_internal_codes_reach_core(services):
    assert set(services.start.internal_referal_ids) == INTERNAL_REFERRAL_CODES

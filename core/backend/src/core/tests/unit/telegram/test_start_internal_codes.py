"""Bot ``/start <code>`` never stores one of the app's own link codes as an acquisition source.

Same rule as ``StartService`` for the Mini App's ``?startapp=r-<code>``: the codes come from
``services.start.internal_referal_ids``. Core's conftest doesn't load the bot fixtures, so
``mock_bot`` / ``message_factory`` are imported here.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram.filters import CommandObject

from core.infrastructure.telegram.handlers import start as start_handlers
from core.testing.fixtures.bot import message_factory, mock_bot  # noqa: F401 — pytest fixtures


@pytest.fixture
def services() -> SimpleNamespace:
    return SimpleNamespace(
        start=SimpleNamespace(internal_referal_ids=frozenset({"ownlink"})),
        users=SimpleNamespace(process_referal=AsyncMock(), clear_bot_blocked=AsyncMock()),
        invites=SimpleNamespace(process_invite=AsyncMock()),
    )


@pytest.fixture(autouse=True)
def quiet(monkeypatch) -> AsyncMock:
    send_menu = AsyncMock()
    monkeypatch.setattr(start_handlers, "send_menu", send_menu)
    monkeypatch.setattr(start_handlers.posthog, "capture", lambda *args, **kwargs: None)
    return send_menu


async def _start(message_factory, services, args: str | None, **kwargs) -> SimpleNamespace:  # noqa: F811
    user = SimpleNamespace(id=uuid4(), telegram_id=123, bot_blocked_at=None)
    await start_handlers.start_command(
        message=message_factory(text=f"/start {args or ''}".strip()),
        command=CommandObject(command="start", args=args),
        user=user,
        services=services,
        **kwargs,
    )
    return user


@pytest.mark.business_logic
async def test_the_apps_own_code_is_not_stored(message_factory, services, quiet):  # noqa: F811
    await _start(message_factory, services, "ownlink")
    services.users.process_referal.assert_not_called()
    quiet.assert_awaited_once()  # the menu still goes out


@pytest.mark.business_logic
async def test_an_external_code_is_stored(message_factory, services):  # noqa: F811
    user = await _start(message_factory, services, "partner_post3")
    services.users.process_referal.assert_awaited_once_with("partner_post3", user.id)


@pytest.mark.business_logic
async def test_the_apps_own_code_skips_a_custom_processor_too(message_factory, services):  # noqa: F811
    processor = AsyncMock()
    await _start(message_factory, services, "ownlink", referral_processor=processor)
    processor.assert_not_called()


@pytest.mark.business_logic
async def test_invites_and_plain_start_are_unchanged(message_factory, services):  # noqa: F811
    await _start(message_factory, services, "i_abc")
    services.invites.process_invite.assert_awaited_once()
    await _start(message_factory, services, None)
    services.users.process_referal.assert_not_called()

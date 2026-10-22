"""Unit tests for AuthMiddleware user-creation gating.

The bot must only persist users for genuine interactions where it has a private
chat it can reply in (private message, callback query, payment query). Service /
membership / observation updates (``my_chat_member``, ``chat_member``,
``message_reaction``, …) reference a user the bot merely *sees* — persisting them
mints "ghost" users who never started the bot, can't be messaged, and pollute
user counts and DAU/MAU.

Links:
    https://core.telegram.org/bots/api#update
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Update

from core.infrastructure.telegram.middlewares.auth import (
    AuthMiddleware,
    _is_user_creating_event,
)

_TS = 1700000000
_TG_USER = {"id": 42, "is_bot": False, "first_name": "Test", "username": "test"}


def _update(payload: dict) -> Update:
    return Update.model_validate({"update_id": 1, **payload})


# Genuine interactions in a private chat the bot can reply in → create a user.
PRIVATE_MESSAGE = {
    "message": {"message_id": 1, "date": _TS, "chat": {"id": 42, "type": "private"}, "from": _TG_USER, "text": "hi"}
}
CALLBACK = {"callback_query": {"id": "cb", "from": _TG_USER, "chat_instance": "ci", "data": "x"}}
PRE_CHECKOUT = {
    "pre_checkout_query": {"id": "p", "from": _TG_USER, "currency": "XTR", "total_amount": 100, "invoice_payload": "p"}
}

# Observation / membership updates → must NOT create a user.
GROUP_MESSAGE = {
    "message": {
        "message_id": 1,
        "date": _TS,
        "chat": {"id": -100, "type": "supergroup"},
        "from": _TG_USER,
        "text": "hi",
    }
}
MY_CHAT_MEMBER = {
    "my_chat_member": {
        "chat": {"id": 42, "type": "private"},
        "from": _TG_USER,
        "date": _TS,
        "old_chat_member": {"status": "member", "user": _TG_USER},
        "new_chat_member": {"status": "left", "user": _TG_USER},
    }
}
REACTION = {
    "message_reaction": {
        "chat": {"id": 42, "type": "private"},
        "message_id": 5,
        "date": _TS,
        "old_reaction": [],
        "new_reaction": [{"type": "emoji", "emoji": "👍"}],
        "user": _TG_USER,
    }
}


class TestIsUserCreatingEvent:
    """The pure predicate that decides whether an update may create a user."""

    @pytest.mark.parametrize("payload", [PRIVATE_MESSAGE, CALLBACK, PRE_CHECKOUT])
    def test_real_interactions_create(self, payload):
        assert _is_user_creating_event(_update(payload)) is True

    @pytest.mark.parametrize("payload", [GROUP_MESSAGE, MY_CHAT_MEMBER, REACTION])
    def test_observation_updates_do_not_create(self, payload):
        assert _is_user_creating_event(_update(payload)) is False


class TestAuthMiddlewareGate:
    """The middleware only calls get_or_create_user for real interactions."""

    @staticmethod
    async def _run(update: Update):
        middleware = AuthMiddleware()
        handler = AsyncMock(return_value="handled")
        services = MagicMock()
        services.users.get_or_create_user = AsyncMock(return_value=MagicMock())
        # aiogram injects event_from_user for the dispatched event.
        from_user = getattr(update.event, "from_user", None)
        data = {"services": services, "event_from_user": from_user}
        result = await middleware(handler, update, data)
        return result, handler, services

    async def test_private_message_creates_user(self):
        result, handler, services = await self._run(_update(PRIVATE_MESSAGE))
        services.users.get_or_create_user.assert_awaited_once()
        handler.assert_awaited_once()
        assert result == "handled"

    async def test_my_chat_member_does_not_create_user(self):
        result, handler, services = await self._run(_update(MY_CHAT_MEMBER))
        services.users.get_or_create_user.assert_not_called()
        handler.assert_awaited_once()  # handler still runs; we just don't persist a user
        assert result == "handled"

    async def test_reaction_does_not_create_user(self):
        _, handler, services = await self._run(_update(REACTION))
        services.users.get_or_create_user.assert_not_called()
        handler.assert_awaited_once()

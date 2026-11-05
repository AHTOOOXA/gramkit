"""Re-export: authentication lives in core (``core.infrastructure.fastapi.auth``, the ``get_user`` dependency in
``core.infrastructure.fastapi.dependencies``). An app configures it through ``create_api`` (``guest_locale``,
``services_class``) and ``app.state.telegram_auth``."""

from core.infrastructure.fastapi.auth import MOCK_GUEST_USER_ID, get_mock_guest_user
from core.infrastructure.fastapi.dependencies import get_user, get_user_streaming

__all__ = ["MOCK_GUEST_USER_ID", "get_mock_guest_user", "get_user", "get_user_streaming"]

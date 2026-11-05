"""Who is calling: the request's user, for every app.

``resolve_user`` is the body of core's ``get_user`` dependency (``core.infrastructure.fastapi.dependencies``).
It used to live, copied almost line for line, in every app's ``webhook/auth.py``; apps now only configure it:

- ``app.state.telegram_auth``: the ``TelegramAuthenticator`` for the app's bot token (``create_api``'s caller sets it);
- ``app.state.guest_locale``: the language of the shared guest when the request doesn't say
  (``create_api(guest_locale=...)``; ``None`` = the guest row's own language).

Order: the ``Mock-Platform`` header (debug only), then Telegram ``initData``, then the session cookie. With none of
them the request gets the **shared mock guest user**: never a 401 for "not logged in", so gate endpoints with
``core.auth.rbac``.
"""

import json
from datetime import UTC, datetime
from json import JSONDecodeError
from urllib.parse import parse_qsl, unquote
from uuid import UUID

from fastapi import HTTPException, Request

from core.infrastructure.auth.telegram import InvalidInitDataError, NoInitDataError
from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import UserType
from core.infrastructure.i18n import i18n, supported_locale
from core.infrastructure.logging import get_logger
from core.infrastructure.sentry_context import set_sentry_user
from core.schemas.users import UserSchema

logger = get_logger(__name__)

MOCK_GUEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")  # the one shared guest row


def get_mock_guest_user() -> UserSchema:
    return UserSchema(
        id=MOCK_GUEST_USER_ID,
        display_name="Guest",
        username=None,
        avatar_url=None,
        user_type=UserType.GUEST,
        telegram_id=None,
        language_code="en",
        tg_first_name="Guest",
        tg_last_name=None,
        tg_username=None,
        tg_language_code="en",
        tg_is_premium=None,
        tg_is_bot=None,
        tg_added_to_attachment_menu=None,
        tg_allows_write_to_pm=None,
        tg_photo_url=None,
        male=None,
        birth_date=None,
        is_onboarded=False,
        is_terms_accepted=False,
        timezone="UTC",
        current_streak=0,
        best_streak=0,
        last_activity_date=None,
        total_active_days=0,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),  # Fixed old date to avoid "is_new" logic
        updated_at=datetime.now(UTC),
    )


def _set_sentry(user) -> None:
    set_sentry_user(
        user_id=str(user.id),
        username=user.username,
        email=getattr(user, "email", None),
        tg_username=user.tg_username,
    )


async def _mock_user_from_init_data(init_data: str, services) -> UserSchema | None:
    """Debug "login as": the user carried in the frontend's mock initData (not signed), got or created."""
    try:
        init_data_dict = dict(parse_qsl(init_data))
        if init_data_dict.get("mock_init_data") != "true":
            return None
        user_data_encoded = init_data_dict.get("user")
        if not user_data_encoded:
            return None
        user_data = json.loads(unquote(user_data_encoded))

        first_name = user_data.get("first_name", "Mock User")
        last_name = user_data.get("last_name")
        display_name = f"{first_name} {last_name or ''}".strip()
        db_user = await services.users.get_or_create_user(
            UserSchema(
                telegram_id=user_data.get("user_id"),
                display_name=display_name,
                username=user_data.get("username"),
                avatar_url=user_data.get("photo_url"),
                language_code="en",
                user_type=UserType.REGISTERED,  # Mock users are treated as registered
                tg_first_name=first_name,
                tg_last_name=last_name,
                tg_username=user_data.get("username"),
                tg_is_bot=False,
                tg_language_code="en",
                tg_is_premium=False,
                tg_added_to_attachment_menu=False,
                tg_allows_write_to_pm=True,
                tg_photo_url=user_data.get("photo_url"),
            )
        )
        logger.info(f"Mock user {db_user.id} authenticated from frontend selector")
        i18n.set_user_locale(db_user)
        _set_sentry(db_user)
        return UserSchema.model_validate(db_user)
    except (JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Failed to parse mock user data: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing mock user data: {e}")
        return None


async def _authenticate_telegram(request: Request, services, init_data: str) -> UserSchema:
    """The Telegram user signed into ``initData``, registered or refreshed in the DB."""
    user = request.app.state.telegram_auth.verify_token(init_data)
    display_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or "User"
    db_user = await services.users.get_or_create_user(
        UserSchema(
            telegram_id=user.id,
            # App profile fields (populated from TG data on first login)
            display_name=display_name,
            username=user.username,
            avatar_url=user.photo_url,
            language_code=user.language_code,
            # Telegram data (read-only from TG API)
            tg_first_name=user.first_name,
            tg_last_name=user.last_name,
            tg_username=user.username,
            tg_language_code=user.language_code,
            tg_is_bot=user.is_bot,
            tg_is_premium=user.is_premium,
            tg_added_to_attachment_menu=user.added_to_attachment_menu,
            tg_allows_write_to_pm=user.allows_write_to_pm,
            tg_photo_url=user.photo_url,
            user_type=UserType.REGISTERED,
        )
    )
    logger.debug("Telegram user %s authenticated", db_user.id)  # the access-log line carries the user
    i18n.set_user_locale(db_user)
    request.state.user = db_user
    _set_sentry(db_user)
    return db_user  # get_or_create_user already returns a UserSchema


async def _authenticate_session(request: Request, services) -> UserSchema | None:
    """The user of the session cookie (web logins), or None."""
    session_id = request.cookies.get(settings.session.cookie_name)
    if not session_id:
        return None
    session_data = await services.sessions.validate_session(session_id)
    if not session_data:
        return None
    user_id_str = session_data.get("user_id")
    if not user_id_str:
        return None
    try:
        user_db = await services.users.get_user_by_id(UUID(user_id_str))
    except ValueError as e:
        logger.warning(f"Invalid UUID in session {session_id}: {e}")
        return None
    except Exception as e:
        # UserService.get_user_by_id fails validating None when the row is gone
        logger.error(f"Error authenticating session {session_id}: {e}")
        return None

    logger.debug("Session user %s authenticated", user_db.id)
    i18n.set_user_locale(user_db)
    request.state.user = user_db
    _set_sentry(user_db)
    return user_db


async def _mock_guest_user(request: Request, services) -> UserSchema:
    """The shared guest row (created on first use, so update operations work on it)."""
    mock_user_for_db = get_mock_guest_user().model_copy(update={"created_at": None, "updated_at": None})
    user_schema = UserSchema.model_validate(await services.users.get_or_create_user(mock_user_for_db))
    request.state.user = user_schema
    # The guest is ONE shared row for every logged-out web visitor, so its language must not come from the
    # row: the frontend sends its UI locale in X-App-Locale. Without it, the app's guest_locale (None = the row's).
    app_locale = request.headers.get("x-app-locale")
    fallback = getattr(request.app.state, "guest_locale", None)
    if app_locale:
        i18n.update_locale(supported_locale(app_locale))
    elif fallback:
        i18n.update_locale(fallback)
    else:
        i18n.set_user_locale(user_schema)
    logger.info(f"Mock guest user {MOCK_GUEST_USER_ID} provided (from database)")
    set_sentry_user(user_id=str(user_schema.id), username=user_schema.username, email=None, tg_username=None)
    return user_schema


async def resolve_user(request: Request, services) -> UserSchema:
    # Debug "login as" (frontend mock initData)
    if request.headers.get("Mock-Platform") == "true" and settings.debug:
        init_data = request.headers.get("initData")
        if init_data:
            mock_user = await _mock_user_from_init_data(init_data, services)
            if mock_user:
                request.state.user = mock_user
                return mock_user
        logger.info("No mock user data in initData, falling through to normal auth")

    init_data = request.headers.get("initData")
    if init_data:
        try:
            return await _authenticate_telegram(request, services, init_data)
        except (InvalidInitDataError, NoInitDataError) as e:
            # A present but invalid initData is a 401, never a silent fall-through to the cookie or the guest.
            # (The per-app copies meant to fall through, but caught their own exception classes, so core's
            # authenticator's errors always ended up in the catch-all below: 401. Kept, now on purpose.)
            logger.warning(f"Telegram authentication failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
        except Exception as e:
            logger.error(f"Unexpected error in Telegram auth: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")

    session_user = await _authenticate_session(request, services)
    if session_user:
        return session_user

    return await _mock_guest_user(request, services)

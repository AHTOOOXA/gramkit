import dataclasses
import hashlib
import hmac
import json
from datetime import UTC, datetime
from json import JSONDecodeError
from urllib.parse import parse_qsl, unquote
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request, Response

from app.services.requests import RequestsService
from app.webhook.dependencies.service import get_services
from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import UserType
from core.infrastructure.i18n import i18n
from core.infrastructure.logging import get_logger
from core.infrastructure.redis import RedisClient
from core.infrastructure.sentry_context import set_sentry_user
from core.schemas.users import UserSchema

logger = get_logger(__name__)

MOCK_GUEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")  # Fixed UUID for the mock guest user

# Session Configuration - app-specific to avoid conflicts between apps
SESSION_COOKIE_NAME = f"{settings.app_name}_session"
SESSION_KEY_PREFIX = f"{settings.app_name}:session:"

# Initialize Redis client for sessions
session_redis = RedisClient(settings.redis)


@dataclasses.dataclass
class TelegramUser:
    """Represents a Telegram user.

    Links:
        https://core.telegram.org/bots/webapps#webappuser
    """

    id: int
    first_name: str
    is_bot: bool | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None
    added_to_attachment_menu: bool | None = None
    allows_write_to_pm: bool | None = None
    photo_url: str | None = None


def generate_secret_key(token: str) -> bytes:
    """Generates a secret key from a Telegram token.

    Links:
        https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Args:
        token: Telegram Bot Token

    Returns:
        bytes: secret key
    """
    base = b"WebAppData"
    token_enc = token.encode("utf-8")
    return hmac.digest(base, token_enc, hashlib.sha256)


class TelegramAuthenticator:
    def __init__(self, secret: bytes):
        self._secret = secret

    @staticmethod
    def _parse_init_data(data: str) -> dict:
        """Convert init_data string into dictionary.

        Args:
            data: the query string passed by the webapp
        """
        if not data:
            raise InvalidInitDataError("Init Data cannot be empty")
        return dict(parse_qsl(data))

    @staticmethod
    def _parse_user_data(data: str) -> dict:
        """Convert user value from WebAppInitData to Python dictionary.

        Links:
            https://core.telegram.org/bots/webapps#webappinitdata

        Raises:
            InvalidInitDataError
        """
        try:
            return json.loads(unquote(data))
        except JSONDecodeError:
            raise InvalidInitDataError("Cannot decode init data")

    def _validate(self, hash_: str, token: str) -> bool:
        """Validates the data received from the Telegram web app, using the method from Telegram documentation.

        Links:
            https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

        Args:
            hash_: hash from init data
            token: init data from webapp

        Returns:
            bool: Validation result
        """
        token_bytes = token.encode("utf-8")
        client_hash = hmac.new(self._secret, token_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(client_hash, hash_)

    def verify_token(self, token: str) -> TelegramUser:
        """Verifies the data using the method from documentation. Returns Telegram user if data is valid.

        Links:
            https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

        Args:
            hash_: hash from init data
            token: init data from webapp

        Returns:
            TelegramUser: Telegram user if token is valid

        Raises:
            InvalidInitDataError: if the token is invalid
        """
        init_data = self._parse_init_data(token)
        token = "\n".join(
            f"{key}={val}" for key, val in sorted(init_data.items(), key=lambda item: item[0]) if key != "hash"
        )
        token = unquote(token)
        hash_ = init_data.get("hash")
        if not hash_:
            raise InvalidInitDataError("Init data does not contain hash")

        hash_ = hash_.strip()

        if not self._validate(hash_, token):
            raise InvalidInitDataError("Invalid token")

        user_data = init_data.get("user")
        if not user_data:
            raise InvalidInitDataError("Init data does not contain user")

        user_data = unquote(user_data)
        user_data = self._parse_user_data(user_data)
        return TelegramUser(**user_data)


class NoInitDataError(Exception):
    pass


class InvalidInitDataError(Exception):
    pass


def get_telegram_authenticator() -> TelegramAuthenticator:
    secret_key = generate_secret_key(settings.bot.token)
    return TelegramAuthenticator(secret_key)


# =============================================================================
# Guest Authentication
# =============================================================================


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


# =============================================================================
# Session Management Functions
# =============================================================================


async def create_session(user_id: UUID, user_type: str) -> str:
    """
    Create a new session for the user and store it in Redis.

    Returns:
        str: Session ID (UUID) for setting in cookie
    """
    session_id = str(uuid4())
    session_key = f"{SESSION_KEY_PREFIX}{session_id}"

    session_data = {
        "user_id": str(user_id),  # Convert UUID to string for JSON serialization
        "user_type": user_type,
        "created_at": datetime.now(UTC).isoformat(),
        "last_accessed": datetime.now(UTC).isoformat(),
    }

    # Store session with TTL
    expire_seconds = settings.session.expire_days * 24 * 60 * 60
    await session_redis.set(session_key, json.dumps(session_data), ex=expire_seconds)

    logger.info(f"Created session {session_id} for user {user_id}")
    return session_id


async def validate_session(session_id: str) -> dict | None:
    """
    Validate session ID and return user data if valid.

    Returns:
        dict: Session data with user info if valid
        None: If session is invalid or expired
    """
    if not session_id:
        return None

    session_key = f"{SESSION_KEY_PREFIX}{session_id}"

    try:
        session_data_raw = await session_redis.get(session_key)
        if not session_data_raw:
            return None

        session_data = json.loads(session_data_raw.decode("utf-8"))

        # Update last accessed time and extend TTL
        session_data["last_accessed"] = datetime.now(UTC).isoformat()
        expire_seconds = settings.session.expire_days * 24 * 60 * 60

        await session_redis.set(session_key, json.dumps(session_data), ex=expire_seconds)

        return session_data

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Invalid session data for {session_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error validating session {session_id}: {e}")
        return None


async def destroy_session(session_id: str) -> bool:
    """
    Destroy a session by removing it from Redis.

    Returns:
        bool: True if session was destroyed, False if not found
    """
    if not session_id:
        return False

    session_key = f"{SESSION_KEY_PREFIX}{session_id}"

    try:
        result = await session_redis.delete(session_key)
        logger.info(f"Destroyed session {session_id}")
        return bool(result)
    except Exception as e:
        logger.error(f"Error destroying session {session_id}: {e}")
        return False


def set_session_cookie(response: Response, session_id: str) -> None:
    """
    Set session cookie in the response.
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.session.expire_days * 24 * 60 * 60,
        httponly=settings.session.cookie_httponly,
        secure=settings.session.cookie_secure,
        samesite=settings.session.cookie_samesite,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """
    Clear session cookie from the response.
    """
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=settings.session.cookie_httponly,
        secure=settings.session.cookie_secure,
        samesite=settings.session.cookie_samesite,
        path="/",
    )


# =============================================================================
# Internal Authentication Functions
# =============================================================================


async def _get_mock_user_from_init_data(init_data: str, services: RequestsService) -> UserSchema | None:
    """Parse mock user data from frontend initData and get or create the user."""
    try:
        # Parse the mock init data
        init_data_dict = dict(parse_qsl(init_data))

        # Check if this is mock data
        if init_data_dict.get("mock_init_data") != "true":
            return None

        # Extract user data
        user_data_encoded = init_data_dict.get("user")
        if not user_data_encoded:
            return None

        # Decode and parse user data
        user_data_str = unquote(user_data_encoded)
        user_data = json.loads(user_data_str)

        # Create or get the mock user
        first_name = user_data.get("first_name", "Mock User")
        last_name = user_data.get("last_name")
        display_name = f"{first_name} {last_name or ''}".strip()
        mock_user_schema = UserSchema(
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

        # Get or create the user in database
        db_user = await services.users.get_or_create_user(mock_user_schema)
        logger.info(f"Mock user {db_user.id} authenticated from frontend selector")
        i18n.set_user_locale(db_user)

        # Set Sentry user context
        set_sentry_user(
            user_id=str(db_user.id),
            username=db_user.username,
            email=db_user.email,
            tg_username=db_user.tg_username,
        )

        return UserSchema.model_validate(db_user)

    except (JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Failed to parse mock user data: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing mock user data: {e}")
        return None


async def _authenticate_telegram(request: Request, services: RequestsService) -> UserSchema:
    """Authenticate Telegram user via initData"""
    init_data = request.headers.get("initData")

    # TODO: to be removed, never will be called with new logic
    # if not init_data:
    #     if settings.debug:
    #         user = await _get_debug_user(services)
    #         request.state.user = user
    #         return user
    #     logger.error("Init data is missing")
    #     raise HTTPException(status_code=401, detail="Init data is missing")

    # Get telegram authenticator from app state (configured in app.py)
    telegram_authenticator = request.app.state.telegram_auth
    user = telegram_authenticator.verify_token(init_data)

    # Register or update user in the database
    # Map TelegramUser fields to UserSchema with tg_ prefix
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

    logger.info(f"Telegram user {db_user.id} authenticated")
    i18n.set_user_locale(db_user)
    request.state.user = db_user

    # Set Sentry user context
    set_sentry_user(
        user_id=str(db_user.id),
        username=db_user.username,
        email=db_user.email,
        tg_username=db_user.tg_username,
    )

    return UserSchema.model_validate(db_user)


async def _authenticate_session(request: Request, services: RequestsService) -> UserSchema | None:
    """
    Authenticate user via session cookie.

    Returns:
        UserSchema if valid session
        None if no session or invalid session
    """
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None

    session_data = await validate_session(session_id)
    if not session_data:
        return None

    user_id_str = session_data.get("user_id")
    if not user_id_str:
        return None

    try:
        # Convert user_id from string to UUID
        user_id = UUID(user_id_str)

        # Get user from database
        user_db = await services.users.get_user_by_id(user_id)
        if not user_db:
            logger.warning(f"User {user_id} not found for session {session_id}")
            # Clean up invalid session
            await destroy_session(session_id)
            return None

        logger.info(f"Session user {user_db.id} authenticated")
        i18n.set_user_locale(user_db)
        request.state.user = user_db

        # Set Sentry user context
        set_sentry_user(
            user_id=str(user_db.id),
            username=user_db.username,
            email=user_db.email,
            tg_username=user_db.tg_username,
        )

        return UserSchema.model_validate(user_db)

    except ValueError as e:
        logger.warning(f"Invalid UUID in session {session_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error authenticating session {session_id}: {e}")
        return None


async def _get_mock_guest_user(request: Request, services: RequestsService) -> UserSchema:
    """Return mock guest user - creates in database if needed for update operations"""
    mock_user_data = get_mock_guest_user()

    # Exclude created_at/updated_at as repo sets these automatically
    mock_user_for_db = mock_user_data.model_copy(update={"created_at": None, "updated_at": None})

    # Create or get the mock guest user in database to support update operations
    db_user = await services.users.get_or_create_user(mock_user_for_db)

    user_schema = UserSchema.model_validate(db_user)
    request.state.user = user_schema
    i18n.set_user_locale(user_schema)
    logger.info(f"Mock guest user {MOCK_GUEST_USER_ID} provided (from database)")

    # Set Sentry user context for guest
    set_sentry_user(
        user_id=str(user_schema.id),
        username=user_schema.username,
        email=None,
        tg_username=None,
    )

    return user_schema


# =============================================================================
# Universal Authentication Function
# =============================================================================


async def get_user(
    request: Request,
    services: RequestsService = Depends(get_services),
) -> UserSchema:
    """
    Universal user authentication that detects platform and returns UserSchema.

    Priority order:
    1. Mock Platform (debug mode only)
    2. Telegram (via initData header)
    3. Guest (via guest-token header)
    4. Create new guest user

    Always returns UserSchema - universal authentication for all platforms.
    """

    # Check for mock platform mode in debug environment
    if request.headers.get("Mock-Platform") == "true" and settings.debug:
        logger.info("Mock platform mode enabled - checking for mock user data")

        # Try to get mock user from frontend initData
        init_data = request.headers.get("initData")
        if init_data:
            mock_user = await _get_mock_user_from_init_data(init_data, services)
            if mock_user:
                request.state.user = mock_user
                return mock_user

        # No mock user data - fall through to normal auth flow (will return guest)
        logger.info("No mock user data in initData, falling through to normal auth")

    # Check for Telegram authentication first
    if request.headers.get("initData"):
        try:
            return await _authenticate_telegram(request, services)
        except (InvalidInitDataError, NoInitDataError) as e:
            # Telegram auth failed, fall through to next auth method
            logger.warning(f"Telegram authentication failed: {e}")
            pass
        except Exception as e:
            logger.error(f"Unexpected error in Telegram auth: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")

    # Check for session authentication
    session_user = await _authenticate_session(request, services)
    if session_user:
        return session_user

    # No authentication provided, return mock guest user
    return await _get_mock_guest_user(request, services)

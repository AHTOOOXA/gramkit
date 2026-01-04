"""Handler for authentication via Telegram bot.

This handler processes /start auth_{token} commands to authenticate web users
through Telegram. The flow:

API Side:
1. Web calls POST /auth/login/telegram/deeplink/start
2. API returns bot_url with auth_{token}
3. Web polls GET /auth/login/telegram/deeplink/poll

Bot Side:
4. User clicks bot link, sends /start auth_{token}
5. This handler validates token, creates/gets user, creates session
6. Updates token status to "verified" with session info
7. Sends confirmation to user
"""

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from core.infrastructure.logging import get_logger
from core.schemas.users import UserSchema, UserType

logger = get_logger(__name__)

router = Router(name="auth")

AUTH_PREFIX = "auth_"


@router.message(CommandStart(deep_link=True, magic=F.args.startswith(AUTH_PREFIX)))
async def handle_auth(
    message: Message,
    command: CommandObject,
    services,
):
    """
    Handle /start auth_{token} for web authentication.

    This authenticates the Telegram user and updates the web auth token
    so the web browser can complete the login.

    Args:
        message: Telegram message with /start command
        command: Parsed command object with args
        services: RequestsService instance (injected by middleware)
    """
    if not command.args:
        await message.answer("Invalid authentication link.")
        return

    token = command.args[len(AUTH_PREFIX) :]

    if not token:
        await message.answer("Invalid authentication link.")
        return

    tg_user = message.from_user
    logger.info(f"Auth attempt: token={token[:8]}..., telegram_id={tg_user.id}")

    token_data = await services.auth.get_link_status(token)

    if not token_data:
        logger.warning(f"Auth token not found or expired: {token[:8]}...")
        await message.answer("This login link has expired.\n\nPlease go back to the website and try again.")
        return

    if token_data.get("status") != "pending":
        logger.warning(f"Auth token not pending: {token[:8]}..., status={token_data.get('status')}")
        await message.answer("This login link has already been used.\n\nPlease go back to the website and try again.")
        return

    # Map TelegramUser fields to UserSchema with tg_ prefix
    display_name = f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip() or tg_user.username or "User"
    user_data = UserSchema(
        telegram_id=tg_user.id,
        # App profile fields (populated from TG data on first login)
        display_name=display_name,
        username=tg_user.username,
        language_code=tg_user.language_code,
        # Telegram data (read-only from TG API)
        tg_first_name=tg_user.first_name or "User",
        tg_last_name=tg_user.last_name,
        tg_username=tg_user.username,
        tg_language_code=tg_user.language_code,
        tg_is_bot=tg_user.is_bot,
        tg_is_premium=tg_user.is_premium,
        user_type=UserType.REGISTERED,
    )

    db_user = await services.users.get_or_create_user(user_data)

    logger.info(f"Auth user: telegram_id={tg_user.id}, db_user_id={db_user.id}")

    user_type_str = db_user.user_type.value if hasattr(db_user.user_type, "value") else str(db_user.user_type)
    session_id = await services.sessions.create_session(
        user_id=db_user.id,
        user_type=user_type_str,
        metadata={
            "auth_method": "telegram_link",
            "telegram_id": tg_user.id,
        },
    )

    logger.info(f"Auth session created: session_id={session_id}, user_id={db_user.id}")

    success = await services.auth.verify_link_token(token, db_user.id, session_id)

    if not success:
        logger.error(f"Failed to verify link token: {token[:8]}...")
        await message.answer("Authentication failed.\n\nPlease go back to the website and try again.")
        return

    logger.info(f"Auth completed: token={token[:8]}..., user_id={db_user.id}")

    await message.answer("Login successful!\n\nYou can now return to the website. Your session has been activated.")

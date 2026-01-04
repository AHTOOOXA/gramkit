"""Handler for linking Telegram account to existing web users.

This handler processes /start link_{token} commands to link Telegram accounts
to existing users (who signed up via email). The flow:

API Side:
1. Authenticated user calls POST /auth/link/telegram/start
2. API returns bot_url with link_{token}
3. Web polls GET /auth/link/telegram/poll

Bot Side:
4. User clicks bot link, sends /start link_{token}
5. This handler validates token, links TG data to existing user
6. Updates token status to "completed"
7. Sends confirmation to user
"""

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from core.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = Router(name="telegram_link")

LINK_PREFIX = "link_"


@router.message(CommandStart(deep_link=True, magic=F.args.startswith(LINK_PREFIX)))
async def handle_telegram_link(
    message: Message,
    command: CommandObject,
    services,
):
    """
    Handle /start link_{token} for Telegram account linking.

    This links the Telegram account to an existing web user (email auth).

    Args:
        message: Telegram message with /start command
        command: Parsed command object with args
        services: RequestsService instance (injected by middleware)
    """
    if not command.args:
        await message.answer("Invalid link.")
        return

    token = command.args[len(LINK_PREFIX) :]

    if not token:
        await message.answer("Invalid link.")
        return

    tg_user = message.from_user
    logger.info(f"Telegram link attempt: token={token[:8]}..., telegram_id={tg_user.id}")

    # Check if service is available
    if not hasattr(services, "telegram_link"):
        logger.error("TelegramLinkService not configured")
        await message.answer("Account linking is not available.\n\nPlease contact support.")
        return

    # Build telegram user data with tg_ prefixed field names
    telegram_user_data = {
        "telegram_id": tg_user.id,
        "tg_first_name": tg_user.first_name or "User",
        "tg_last_name": tg_user.last_name,
        "tg_username": tg_user.username,
        "tg_language_code": tg_user.language_code,
        "tg_is_bot": tg_user.is_bot,
        "tg_is_premium": tg_user.is_premium,
    }

    try:
        result = await services.telegram_link.complete_link(
            token=token,
            telegram_id=tg_user.id,
            telegram_user_data=telegram_user_data,
        )

        logger.info(f"Telegram link completed: token={token[:8]}..., user_id={result['user_id']}")

        await message.answer(
            "Account linked successfully!\n\n"
            "Your Telegram account is now connected to your web account. "
            "You can return to the website."
        )

    except ValueError as e:
        error_code = str(e)

        if error_code == "token_invalid":
            logger.warning(f"Link token not found or expired: {token[:8]}...")
            await message.answer("This link has expired or is invalid.\n\nPlease go back to the website and try again.")
        elif error_code == "telegram_already_used":
            logger.warning(f"Telegram already linked: telegram_id={tg_user.id}")
            await message.answer(
                "This Telegram account is already linked to another account.\n\n"
                "If you want to link to a different account, please unlink it first."
            )
        elif error_code == "user_not_found":
            logger.error(f"User not found for link token: {token[:8]}...")
            await message.answer("Account not found.\n\nPlease go back to the website and try again.")
        else:
            logger.error(f"Unexpected error linking Telegram: {error_code}")
            await message.answer("Failed to link account.\n\nPlease try again later or contact support.")

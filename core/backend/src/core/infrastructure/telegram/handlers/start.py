"""Generic start command handler for Telegram bots.

This module provides a reusable /start command handler that can be configured
for different TMA applications.
"""

from collections.abc import Callable

from aiogram import Router, types
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import ReplyKeyboardMarkup

from core.infrastructure.i18n import i18n
from core.infrastructure.posthog import posthog
from core.schemas.users import UserSchema

router = Router()


async def send_menu(
    message: types.Message | types.CallbackQuery,
    menu_i18n_key: str = "tarot.menu",
    keyboard_factory: Callable[[], ReplyKeyboardMarkup] | None = None,
):
    """
    Send menu message to user.

    This is a generic menu sender that can be customized via parameters.

    Args:
        message: Message or callback query to respond to
        menu_i18n_key: i18n key for menu text (default: "tarot.menu")
        keyboard_factory: Optional function that returns keyboard markup

    Example:
        >>> from app.tgbot.keyboards.keyboards import command_keyboard
        >>> await send_menu(message, keyboard_factory=command_keyboard)
    """
    text = i18n(menu_i18n_key)
    keyboard = keyboard_factory() if keyboard_factory else None

    if isinstance(message, types.CallbackQuery):
        await message.message.answer(text=text, reply_markup=keyboard)
    else:
        await message.answer(text=text, reply_markup=keyboard)


@router.message(CommandStart())
async def start_command(
    message: types.Message,
    command: CommandObject,
    user: UserSchema,
    services,
    menu_i18n_key: str = "tarot.menu",
    keyboard_factory: Callable[[], ReplyKeyboardMarkup] | None = None,
    referral_processor: Callable | None = None,
    posthog_event: str = "bot_command_start",
):
    """
    Handle /start command with user creation, telemetry, and referral processing.

    This is a generic start handler that can be customized for different apps.

    Args:
        message: Start command message
        command: Parsed command object (contains args like referral code)
        user: User schema (injected by AuthMiddleware)
        services: RequestsService instance (injected by middleware)
        menu_i18n_key: i18n key for menu text (default: "tarot.menu")
        keyboard_factory: Optional function that returns keyboard markup
        referral_processor: Optional async function(referral_code, user_id) for custom referral logic
        posthog_event: Event name for analytics (default: "bot_command_start")

    Flow:
        1. Capture analytics event with PostHog
        2. Process referral code if provided (via command args)
        3. Send menu message

    Referral code format:
        /start r-123456 → referral_code = "r-123456"

    Example:
        Configure in app's bot setup:
        >>> from functools import partial
        >>> from app.tgbot.keyboards.keyboards import command_keyboard
        >>>
        >>> # Create configured handler
        >>> app_start_handler = partial(
        ...     start_command,
        ...     menu_i18n_key="myapp.menu",
        ...     keyboard_factory=command_keyboard,
        ...     referral_processor=lambda code, user_id: services.users.process_referal(code, user_id)
        ... )
        >>> router.message(CommandStart())(app_start_handler)
    """
    # Capture analytics event
    posthog.capture(
        distinct_id=user.telegram_id or user.id,
        event=posthog_event,
        properties={
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "referral_code": command.args,
            "username": message.from_user.username,
            "language": message.from_user.language_code,
        },
    )

    # Process referral code or invite code if provided
    referral_code = command.args
    if referral_code:
        if referral_code.startswith("i_"):
            # Process invite code
            invite_code = referral_code[2:]  # Remove "i_" prefix
            if hasattr(services, "invites") and hasattr(services.invites, "process_invite"):
                await services.invites.process_invite(invite_code, user.id)
        elif referral_processor:
            # Use custom referral processor if provided
            await referral_processor(referral_code, user.id)
        else:
            # Default behavior: call services.users.process_referal if it exists
            if hasattr(services, "users") and hasattr(services.users, "process_referal"):
                await services.users.process_referal(referral_code, user.id)

    # Send menu
    await send_menu(message, menu_i18n_key=menu_i18n_key, keyboard_factory=keyboard_factory)


@router.message(Command("ref"))
async def ref_command(
    message: types.Message,
    command: CommandObject,
    bot_url: str,
    web_app_path: str = "/app",
    referral_prefix: str = "r-",
):
    """
    Generate referral links for bot and web app.

    This is a generic referral link generator that can be configured
    for different apps via parameters.

    Args:
        message: Command message
        command: Parsed command object (contains args like user ID)
        bot_url: Base bot URL (e.g., "https://t.me/mybot")
        web_app_path: Path to web app (default: "/app")
        referral_prefix: Prefix for referral codes (default: "r-")

    Command format:
        /ref [user_id] - Generate referral links, optionally for specific user

    Example:
        Configure in app's bot setup:
        >>> from functools import partial
        >>> from core.infrastructure.config import settings
        >>>
        >>> app_ref_command = partial(
        ...     ref_command,
        ...     bot_url=settings.bot.url,
        ...     web_app_path="/app",
        ...     referral_prefix="r-",
        ... )
        >>> router.message(Command("ref"))(app_ref_command)
    """
    bot_link = bot_url
    app_link = f"{bot_url}{web_app_path}"

    if command.args:
        referral_code = f"{referral_prefix}{command.args}"
        bot_link = f"{bot_link}?start={referral_code}"
        app_link = f"{app_link}?startapp={referral_code}"

    await message.answer(text=f"{bot_link}\n\n{app_link}", disable_web_page_preview=True)

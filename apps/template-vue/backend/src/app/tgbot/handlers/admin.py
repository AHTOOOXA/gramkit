from datetime import UTC, datetime, timedelta
from uuid import uuid4

from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.requests import RequestsService
from core.infrastructure.config import settings
from core.infrastructure.logging import get_logger
from core.schemas.users import UpdateUserRequest, UserSchema
from core.services.broadcast_formatting import build_keyboard_markup, entities_to_html
from core.services.messages import user_language

router = Router()
logger = get_logger(__name__)


# Define states for broadcast flow
class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_keyboard = State()
    confirmation = State()


@router.message(Command("admin"))
async def admin_command(message: types.Message, user: UserSchema):
    """Handler for /admin command. Shows all available admin commands."""
    # Check if user is admin
    if not user.telegram_id or user.telegram_id not in settings.rbac.owner_ids:
        await message.answer("You don't have permission to use this command")
        return

    admin_commands = (
        "🔧 Admin Commands\n\n"
        "Broadcasting:\n"
        "• /broadcast - Send a message to all users now\n"
        "• Scheduled broadcasts: the web admin, /admin/broadcasts\n\n"
        "User Management:\n"
        "• /giftsub <user\\_id> <week|month|year|max> - Gift subscription to user\n\n"
        "Statistics:\n"
        "• /stats - Daily digest so far (sent only to you)\n\n"
        "This Menu:\n"
        "• /admin - Show this admin commands list"
    )

    await message.answer(admin_commands, parse_mode="Markdown")


@router.message(Command("broadcast"))
async def broadcast_command(message: types.Message, state: FSMContext, user: UserSchema):
    """Handler for /broadcast command. Initiates the broadcast flow."""
    # Check if user is admin
    if not user.telegram_id or user.telegram_id not in settings.rbac.owner_ids:
        await message.answer("You don't have permission to use this command")
        return

    await message.answer("Please forward the message you want to broadcast to all users.")
    await state.set_state(BroadcastStates.waiting_for_message)


@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    """Handler for the broadcasted message. Stores it and asks about keyboard."""
    # Store the message text or details
    if message.text:
        # Store both the raw text and the HTML formatted version to preserve formatting
        message_text = message.text
        # Convert message with entities to HTML format to preserve formatting like bold, italics, etc.
        if message.entities:
            message_html = entities_to_html(message_text, message.entities)
            await state.update_data(
                message_type="text", message_text=message_text, message_html=message_html, has_formatting=True
            )
        else:
            await state.update_data(message_type="text", message_text=message_text, has_formatting=False)
    elif message.photo:
        photo = message.photo[-1]  # Get the largest photo
        # Also store caption formatting if present
        caption = message.caption or ""
        has_caption_formatting = bool(message.caption_entities)

        # Captions with entities are converted to HTML the same way
        caption_html = None
        if has_caption_formatting and caption:
            caption_html = entities_to_html(caption, message.caption_entities)

        await state.update_data(
            message_type="photo",
            photo_file_id=photo.file_id,
            caption=caption,
            caption_html=caption_html,
            has_caption_formatting=has_caption_formatting,
        )
    else:
        await message.answer("Please send a text message or a photo with optional caption.")
        return

    # Ask about keyboard
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="No keyboard", callback_data="keyboard_none")],
            [InlineKeyboardButton(text="Main menu keyboard", callback_data="keyboard_main")],
            [InlineKeyboardButton(text="Daily keyboard", callback_data="keyboard_daily")],
        ]
    )

    await message.answer("Please select a keyboard to attach to the broadcast message:", reply_markup=keyboard)
    await state.set_state(BroadcastStates.waiting_for_keyboard)


@router.callback_query(BroadcastStates.waiting_for_keyboard)
async def process_keyboard_selection(callback: types.CallbackQuery, state: FSMContext, user: UserSchema):
    """Handler for keyboard selection. Shows preview and asks for confirmation."""
    await callback.answer()
    if not callback.data or not callback.message:
        return

    keyboard_type = callback.data.split("_")[1]
    await state.update_data(keyboard_type=keyboard_type)
    data = await state.get_data()
    # The keyboard the job sends (core registry), in the admin's language.
    keyboard = build_keyboard_markup(data, user_language(user))

    # Prepare preview based on message type
    if data["message_type"] == "photo":
        # Use HTML caption if available
        caption = data.get("caption_html") if data.get("has_caption_formatting") else data.get("caption", "")
        parse_mode = "HTML" if data.get("has_caption_formatting") else None

        await callback.message.answer_photo(
            photo=data["photo_file_id"], caption=caption, parse_mode=parse_mode, reply_markup=keyboard
        )
    else:
        # Use HTML text if available
        message_text = data.get("message_html") if data.get("has_formatting") else data.get("message_text", "")
        parse_mode = "HTML" if data.get("has_formatting") else None

        await callback.message.answer(text=message_text or "", parse_mode=parse_mode, reply_markup=keyboard)

    # Create confirmation buttons
    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Confirm Broadcast", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="broadcast_cancel"),
            ]
        ]
    )

    await callback.message.answer(
        "Above is a preview of your broadcast message. Would you like to proceed with sending it to all users?",
        reply_markup=confirm_keyboard,
    )
    await state.set_state(BroadcastStates.confirmation)


@router.callback_query(BroadcastStates.confirmation, F.data == "broadcast_cancel")
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Handler for cancelling the broadcast."""
    await callback.answer()
    if not callback.message:
        return
    await callback.message.answer("Broadcast cancelled.")
    await state.clear()


@router.callback_query(BroadcastStates.confirmation, F.data == "broadcast_confirm")
async def confirm_broadcast(callback: types.CallbackQuery, state: FSMContext, services: RequestsService):
    """Handler for confirming and queueing the broadcast job."""
    await callback.answer()
    if not callback.message:
        return

    data = await state.get_data()

    # Queue the broadcast job (fast transaction)
    try:
        await services.worker.enqueue_job(
            "user_broadcast_job",
            # run_id: the job skips users this run already reached if arq re-runs it
            broadcast_data={**data, "run_id": uuid4().hex},
            requester_telegram_id=callback.from_user.id,
        )

        await callback.message.answer(
            "✅ Broadcast queued successfully!\n\n"
            "The broadcast is now processing in the background. "
            "You'll receive a notification when it's complete.\n\n"
            "This may take several minutes depending on the number of users."
        )

        logger.info(f"Broadcast job queued by admin {callback.from_user.id} (type: {data.get('message_type')})")

    except Exception as e:
        logger.error(f"Failed to queue broadcast job: {e}", exc_info=True)
        await callback.message.answer("❌ Failed to queue broadcast job. Please try again or check logs.")

    await state.clear()


@router.message(Command("giftsub"))
async def giftsub_command(message: types.Message, command: CommandObject, user: UserSchema, services: RequestsService):
    """Handler for /giftsub command. Gift a subscription to a user."""
    # Check if user is admin
    if not user.telegram_id or user.telegram_id not in settings.rbac.owner_ids:
        await message.answer("You don't have permission to use this command")
        return

    if not command.args:
        await message.answer("Usage: /giftsub <user_id> <week|month|year|max>")
        return

    # Parse arguments
    args = command.args.split()
    if len(args) != 2:
        await message.answer("Invalid arguments. Usage: /giftsub <user_id> <week|month|year|max>")
        return

    user_identifier, duration_type = args

    # Convert duration to days
    duration_days = 0
    if duration_type == "week":
        duration_days = 7
    elif duration_type == "month":
        duration_days = 30
    elif duration_type == "year":
        duration_days = 365
    elif duration_type == "max":
        duration_days = 365 * 5  # 5 years
    else:
        await message.answer("Invalid duration. Use week, month, year, or max")
        return

    # Find the target user
    try:
        telegram_id = int(user_identifier)
        target_user = await services.users.get_by_telegram_id(telegram_id)

        if not target_user:
            await message.answer(f"User with Telegram ID {telegram_id} not found")
            return
    except ValueError:
        await message.answer("Invalid Telegram ID. Please provide a numeric Telegram ID")
        return

    # Gift the subscription
    try:
        # Get current subscription if exists
        subscription = await services.subscriptions.get_subscription_for_user(target_user.id)
        now = datetime.now(UTC)

        # Calculate the new end date
        if subscription and subscription.end_date > now:
            # Extend existing subscription
            new_end_date = subscription.end_date + timedelta(days=duration_days)

            # Update the subscription
            subscription = await services.repo.subscriptions.update(
                subscription.id,
                {
                    "end_date": new_end_date,
                    "status": "ACTIVE",
                },
            )
        else:
            # Create new subscription
            subscription = await services.repo.subscriptions.create(
                {
                    "user_id": target_user.id,
                    "product_id": "GIFT_SUB",
                    "provider_id": "GIFT",
                    "status": "ACTIVE",
                    "currency": "RUB",
                    "start_date": now,
                    "end_date": now + timedelta(days=duration_days),
                    "recurring_details": {"gifted_by": user.id},
                }
            )

        # Update user's onboarding status if needed
        await services.users.update_user(target_user.id, UpdateUserRequest(is_onboarded=True))

        # Notify the admin
        end_date_str = subscription.end_date.strftime("%Y-%m-%d %H:%M:%S")
        username_display = f"@{target_user.username}" if target_user.username else "No username"
        await message.answer(
            f"✅ Successfully gifted {duration_type} subscription to user {username_display}, telegram_id: {target_user.telegram_id}.\n"
            f"Subscription active until: {end_date_str}"
        )

    except Exception as e:
        logger.error(f"Failed to gift subscription: {e}")
        await message.answer(f"❌ Failed to gift subscription: {str(e)}")

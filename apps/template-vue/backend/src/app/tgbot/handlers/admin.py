from datetime import UTC, datetime, timedelta

from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.infrastructure import file_manager
from app.services.requests import RequestsService
from app.tgbot.keyboards.keyboards import command_keyboard, keygo_keyboard
from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import NotificationTimeSlot
from core.infrastructure.i18n import i18n
from core.infrastructure.logging import get_logger
from core.schemas.users import UpdateUserRequest, UserSchema

router = Router()
logger = get_logger(__name__)


async def _process_media_message(state: FSMContext, media_type: str, file_id: str, message: types.Message):
    """Helper function to process media messages (photo, video, animation, document)"""
    caption = message.caption or ""
    caption_html = caption
    has_caption_formatting = bool(message.caption_entities)

    if has_caption_formatting and message.caption_entities:
        for entity in sorted(message.caption_entities, key=lambda e: e.offset, reverse=True):
            text_part = caption[entity.offset : entity.offset + entity.length]
            if entity.type == "bold":
                replacement = f"<b>{text_part}</b>"
            elif entity.type == "italic":
                replacement = f"<i>{text_part}</i>"
            elif entity.type == "code":
                replacement = f"<code>{text_part}</code>"
            elif entity.type == "pre":
                replacement = f"<pre>{text_part}</pre>"
            elif entity.type == "underline":
                replacement = f"<u>{text_part}</u>"
            elif entity.type == "strikethrough":
                replacement = f"<s>{text_part}</s>"
            elif entity.type == "text_link" and entity.url:
                replacement = f'<a href="{entity.url}">{text_part}</a>'
            elif entity.type == "spoiler":
                replacement = f'<span class="tg-spoiler">{text_part}</span>'
            else:
                continue

            caption_html = caption_html[: entity.offset] + replacement + caption_html[entity.offset + entity.length :]

    await state.update_data(
        message_type=media_type,
        media_file_id=file_id,
        caption=caption,
        caption_html=caption_html,
        has_caption_formatting=has_caption_formatting,
    )


# Define states for broadcast flow
class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_keyboard = State()
    confirmation = State()


# Define states for promotional broadcast flow
class PromoStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_time_slot = State()
    waiting_for_repeat_count = State()
    waiting_for_keyboard = State()
    waiting_for_button_text = State()
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
        "• /broadcast - Send message to all users\n"
        "• /promo - Schedule promotional broadcasts\n"
        "• /promo\\_list - View active promotional broadcasts\n"
        "• /promo\\_cancel <id> - Cancel promotional broadcast\n\n"
        "User Management:\n"
        "• /giftsub <user\\_id> <week|month|year|max> - Gift subscription to user\n\n"
        "Statistics:\n"
        "• /stats - Generate and send daily statistics manually\n\n"
        "Special:\n"
        "• /keygo\\_prediction - Send keygo prediction message\n\n"
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
            message_html = message.text
            # Process entities from end to beginning to preserve offsets
            for entity in sorted(message.entities, key=lambda e: e.offset, reverse=True):
                text_part = message_text[entity.offset : entity.offset + entity.length]
                if entity.type == "bold":
                    replacement = f"<b>{text_part}</b>"
                elif entity.type == "italic":
                    replacement = f"<i>{text_part}</i>"
                elif entity.type == "code":
                    replacement = f"<code>{text_part}</code>"
                elif entity.type == "pre":
                    replacement = f"<pre>{text_part}</pre>"
                elif entity.type == "underline":
                    replacement = f"<u>{text_part}</u>"
                elif entity.type == "strikethrough":
                    replacement = f"<s>{text_part}</s>"
                elif entity.type == "text_link" and entity.url:
                    replacement = f'<a href="{entity.url}">{text_part}</a>'
                elif entity.type == "spoiler":
                    replacement = f'<span class="tg-spoiler">{text_part}</span>'
                elif entity.type == "mention":
                    replacement = f'<a href="https://t.me/{text_part[1:]}">{text_part}</a>'
                elif entity.type == "hashtag":
                    replacement = f'<a href="https://t.me/hashtag/{text_part[1:]}">{text_part}</a>'
                elif entity.type == "url":
                    replacement = f'<a href="{text_part}">{text_part}</a>'
                else:
                    continue  # Skip unsupported entity types

                # Replace the formatted part in the text
                message_html = (
                    message_html[: entity.offset] + replacement + message_html[entity.offset + entity.length :]
                )

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

        # For captions with entities, we need to manually format to HTML
        caption_html = None
        if has_caption_formatting and caption:
            # Simple manual formatting to HTML
            caption_html = caption
            if message.caption_entities:
                # Handle basic formatting
                for entity in sorted(message.caption_entities, key=lambda e: e.offset, reverse=True):
                    text_part = caption[entity.offset : entity.offset + entity.length]
                    if entity.type == "bold":
                        replacement = f"<b>{text_part}</b>"
                    elif entity.type == "italic":
                        replacement = f"<i>{text_part}</i>"
                    elif entity.type == "code":
                        replacement = f"<code>{text_part}</code>"
                    elif entity.type == "pre":
                        replacement = f"<pre>{text_part}</pre>"
                    elif entity.type == "underline":
                        replacement = f"<u>{text_part}</u>"
                    elif entity.type == "strikethrough":
                        replacement = f"<s>{text_part}</s>"
                    elif entity.type == "text_link" and entity.url:
                        replacement = f'<a href="{entity.url}">{text_part}</a>'
                    elif entity.type == "spoiler":
                        replacement = f'<span class="tg-spoiler">{text_part}</span>'
                    elif entity.type == "mention":
                        replacement = f'<a href="https://t.me/{text_part[1:]}">{text_part}</a>'
                    elif entity.type == "hashtag":
                        replacement = f'<a href="https://t.me/hashtag/{text_part[1:]}">{text_part}</a>'
                    elif entity.type == "url":
                        replacement = f'<a href="{text_part}">{text_part}</a>'
                    else:
                        continue  # Skip unsupported entity types

                    # Replace the formatted part in the text
                    caption_html = (
                        caption_html[: entity.offset] + replacement + caption_html[entity.offset + entity.length :]
                    )

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
            [InlineKeyboardButton(text="Daily card keyboard", callback_data="keyboard_daily")],
        ]
    )

    await message.answer("Please select a keyboard to attach to the broadcast message:", reply_markup=keyboard)
    await state.set_state(BroadcastStates.waiting_for_keyboard)


@router.callback_query(BroadcastStates.waiting_for_keyboard)
async def process_keyboard_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handler for keyboard selection. Shows preview and asks for confirmation."""
    await callback.answer()
    if not callback.data or not callback.message:
        return

    keyboard_type = callback.data.split("_")[1]
    await state.update_data(keyboard_type=keyboard_type)
    data = await state.get_data()

    # Prepare preview based on message type
    if data["message_type"] == "photo":
        # Preview with selected keyboard
        keyboard = None
        if keyboard_type == "main":
            keyboard = command_keyboard()
        elif keyboard_type == "daily":
            kb = InlineKeyboardBuilder()
            kb.button(
                text=i18n("tarot.open_app_button"),
                url=f"{settings.web.app_url}?startapp=r-dailycardnotification",
            )
            kb.adjust(1)
            keyboard = kb.as_markup()

        # Use HTML caption if available
        caption = data.get("caption_html") if data.get("has_caption_formatting") else data.get("caption", "")
        parse_mode = "HTML" if data.get("has_caption_formatting") else None

        await callback.message.answer_photo(
            photo=data["photo_file_id"], caption=caption, parse_mode=parse_mode, reply_markup=keyboard
        )
    else:
        # Text message preview
        keyboard = None
        if keyboard_type == "main":
            keyboard = command_keyboard()
        elif keyboard_type == "daily":
            kb = InlineKeyboardBuilder()
            kb.button(
                text=i18n("tarot.open_app_button"),
                url=f"{settings.web.app_url}?startapp=r-dailycardnotification",
            )
            kb.adjust(1)
            keyboard = kb.as_markup()

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
            broadcast_data=data,
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


@router.message(Command("keygo_prediction"))
async def keygo_prediction_command(message: types.Message, user: UserSchema):
    """Handler for /keygo_prediction command. Sends a prediction message with keygo image."""
    # Check if user is admin
    if not user.telegram_id or user.telegram_id not in settings.rbac.owner_ids:
        await message.answer("You don't have permission to use this command")
        return

    # Get the keygo keyboard
    keygo_kb = keygo_keyboard()

    # Get the path to the keygo image
    image_path = file_manager.get_full_path("images/keygo/placeholder.png")

    # Send the prediction message with the image
    await message.answer_photo(
        photo=types.FSInputFile(image_path), caption="Предсказание на сегодняшнюю встречу", reply_markup=keygo_kb
    )


@router.message(Command("stats"))
async def stats_command(message: types.Message, user: UserSchema, services: RequestsService):
    """Handler for /stats command. Manually triggers daily statistics generation and broadcast."""
    # Check if user is admin
    if not user.telegram_id or user.telegram_id not in settings.rbac.owner_ids:
        await message.answer("You don't have permission to use this command")
        return

    try:
        # Gather statistics using the same logic as the scheduled job
        stats = await services.statistics.get_daily_statistics()

        # Format the message
        formatted_message = services.statistics.format_statistics_message(stats)

        # Send to all admins (same as the scheduled job)
        await services.messages.admin_broadcast(formatted_message)

    except Exception as e:
        logger.error(f"Failed to manually generate daily statistics: {e}", exc_info=True)

        # Send error message to the requesting admin
        error_message = f"❌ Failed to generate statistics: {str(e)}"
        await message.answer(error_message)

        # Also send error notification to all admins
        admin_error_message = (
            f"📊 Manual Statistics Error\n\n❌ Failed to generate statistics (requested by admin): {str(e)}"
        )
        await services.messages.admin_broadcast(admin_error_message)


# Promotional Broadcast Commands


@router.message(Command("promo"))
async def promo_command(message: types.Message, state: FSMContext, user: UserSchema):
    """Handler for /promo command. Initiates the promotional broadcast scheduling flow."""
    # Check if user is admin
    if not user.telegram_id or user.telegram_id not in settings.rbac.owner_ids:
        await message.answer("You don't have permission to use this command")
        return

    await message.answer(
        "🎯 **Promotional Broadcast Scheduler**\n\n"
        "Forward or send the message you want to schedule for promotional broadcasts.\n"
        "This message will be sent during regular notification times instead of normal notifications.",
        parse_mode="Markdown",
    )
    await state.set_state(PromoStates.waiting_for_message)


@router.message(PromoStates.waiting_for_message)
async def process_promo_message(message: types.Message, state: FSMContext):
    """Handler for the promotional message. Stores it and asks about time slot."""
    # Store the message (reuse logic from broadcast_command)
    if message.text:
        message_text = message.text
        message_html = message_text

        # Process entities for formatting
        if message.entities:
            for entity in sorted(message.entities, key=lambda e: e.offset, reverse=True):
                text_part = message_text[entity.offset : entity.offset + entity.length]
                if entity.type == "bold":
                    replacement = f"<b>{text_part}</b>"
                elif entity.type == "italic":
                    replacement = f"<i>{text_part}</i>"
                elif entity.type == "code":
                    replacement = f"<code>{text_part}</code>"
                elif entity.type == "pre":
                    replacement = f"<pre>{text_part}</pre>"
                elif entity.type == "underline":
                    replacement = f"<u>{text_part}</u>"
                elif entity.type == "strikethrough":
                    replacement = f"<s>{text_part}</s>"
                elif entity.type == "text_link" and entity.url:
                    replacement = f'<a href="{entity.url}">{text_part}</a>'
                elif entity.type == "spoiler":
                    replacement = f'<span class="tg-spoiler">{text_part}</span>'
                else:
                    continue

                message_html = (
                    message_html[: entity.offset] + replacement + message_html[entity.offset + entity.length :]
                )

            await state.update_data(
                message_type="text", message_text=message_text, message_html=message_html, has_formatting=True
            )
        else:
            await state.update_data(
                message_type="text", message_text=message_text, message_html=message_text, has_formatting=False
            )

    elif message.photo:
        await _process_media_message(state, "photo", message.photo[-1].file_id, message)
    elif message.video:
        await _process_media_message(state, "video", message.video.file_id, message)
    elif message.animation:
        await _process_media_message(state, "animation", message.animation.file_id, message)
    elif message.document:
        await _process_media_message(state, "document", message.document.file_id, message)
    else:
        await message.answer("Please send a text message, photo, video, GIF/animation, or document.")
        return

    # Ask about time slot
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌅 Morning (10 AM)", callback_data="timeslot_morning")],
            [InlineKeyboardButton(text="🌙 Evening (7 PM)", callback_data="timeslot_evening")],
            [InlineKeyboardButton(text="🔄 Both Morning & Evening", callback_data="timeslot_both")],
        ]
    )

    await message.answer(
        "📅 **Choose when to send this promotional message:**\n\n"
        "• Morning notifications are sent at 10 AM local time\n"
        "• Evening notifications are sent at 7 PM local time\n"
        "• Both will create separate scheduled broadcasts",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(PromoStates.waiting_for_time_slot)


@router.callback_query(PromoStates.waiting_for_time_slot)
async def process_time_slot(callback: types.CallbackQuery, state: FSMContext):
    """Handler for time slot selection. Asks about repeat count."""
    await callback.answer()
    if not callback.data or not callback.message:
        return

    time_slot = callback.data.split("_")[1]
    await state.update_data(time_slot=time_slot)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="repeat_1"),
                InlineKeyboardButton(text="2", callback_data="repeat_2"),
                InlineKeyboardButton(text="3", callback_data="repeat_3"),
            ],
            [
                InlineKeyboardButton(text="5", callback_data="repeat_5"),
                InlineKeyboardButton(text="7", callback_data="repeat_7"),
                InlineKeyboardButton(text="10", callback_data="repeat_10"),
            ],
        ]
    )

    await callback.message.answer(
        "🔢 **How many times should this message be sent?**\n\n"
        "The message will be sent during the next X notification cycles.\n"
        "For example, choosing '3' means it will be sent 3 times over the next 3 days.",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(PromoStates.waiting_for_repeat_count)


@router.callback_query(PromoStates.waiting_for_repeat_count)
async def process_repeat_count(callback: types.CallbackQuery, state: FSMContext):
    """Handler for repeat count selection. Asks about keyboard."""
    await callback.answer()
    if not callback.data or not callback.message:
        return

    repeat_count = int(callback.data.split("_")[1])
    await state.update_data(repeat_count=repeat_count)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="No keyboard", callback_data="keyboard_none")],
            [InlineKeyboardButton(text="Main menu keyboard (custom text)", callback_data="keyboard_main")],
            [InlineKeyboardButton(text="Daily card keyboard", callback_data="keyboard_daily")],
        ]
    )

    await callback.message.answer("⌨️ **Choose a keyboard to attach:**", reply_markup=keyboard)
    await state.set_state(PromoStates.waiting_for_keyboard)


@router.callback_query(PromoStates.waiting_for_keyboard)
async def process_promo_keyboard_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handler for keyboard selection. Asks for button text if main keyboard is selected."""
    await callback.answer()
    if not callback.data or not callback.message:
        return

    keyboard_type = callback.data.split("_")[1]
    await state.update_data(keyboard_type=keyboard_type)

    # If main keyboard is selected, ask for custom button text
    if keyboard_type == "main":
        await callback.message.answer(
            "📝 **Custom Button Text**\n\n"
            "Please enter the text you want to display on the button.\n"
            "Example: 'Open App', 'Get Reading', 'Try Now', etc.",
            parse_mode="Markdown",
        )
        await state.set_state(PromoStates.waiting_for_button_text)
        return

    # For other keyboard types, proceed directly to preview
    await _show_promo_preview_and_confirmation(callback, state)


@router.message(PromoStates.waiting_for_button_text)
async def process_button_text(message: types.Message, state: FSMContext):
    """Handler for custom button text input."""
    if not message.text:
        await message.answer("❌ Please enter text for the button:")
        return
    button_text = message.text.strip()

    if not button_text:
        await message.answer("❌ Button text cannot be empty. Please enter some text:")
        return

    if len(button_text) > 64:  # Telegram button text limit
        await message.answer("❌ Button text is too long (max 64 characters). Please enter a shorter text:")
        return

    await state.update_data(keyboard_button_text=button_text)
    await _show_promo_preview_and_confirmation(message, state)


async def _show_promo_preview_and_confirmation(message_or_callback, state: FSMContext):
    """Helper function to show preview and confirmation for promotional broadcast"""
    data = await state.get_data()
    keyboard_type = data["keyboard_type"]

    # Show preview
    keyboard = None
    if keyboard_type == "main":
        # Use custom button text if available
        button_text = data.get("keyboard_button_text", "Open App")
        kb = InlineKeyboardBuilder()
        kb.button(
            text=button_text,
            url=f"{settings.web.app_url}",
        )
        kb.adjust(1)
        keyboard = kb.as_markup()
    elif keyboard_type == "daily":
        kb = InlineKeyboardBuilder()
        kb.button(
            text=i18n("tarot.open_app_button"),
            url=f"{settings.web.app_url}?startapp=r-dailycardnotification",
        )
        kb.adjust(1)
        keyboard = kb.as_markup()

    if data["message_type"] == "text":
        message_text = data.get("message_html") if data.get("has_formatting") else data.get("message_text", "")
        parse_mode = "HTML" if data.get("has_formatting") else None

        await message_or_callback.answer(text=message_text, parse_mode=parse_mode, reply_markup=keyboard)
    else:
        # Media messages (photo, video, animation, document)
        caption = data.get("caption_html") if data.get("has_caption_formatting") else data.get("caption", "")
        parse_mode = "HTML" if data.get("has_caption_formatting") else None
        file_id = data["media_file_id"]

        if data["message_type"] == "photo":
            await message_or_callback.answer_photo(
                photo=file_id, caption=caption, parse_mode=parse_mode, reply_markup=keyboard
            )
        elif data["message_type"] == "video":
            await message_or_callback.answer_video(
                video=file_id, caption=caption, parse_mode=parse_mode, reply_markup=keyboard
            )
        elif data["message_type"] == "animation":
            await message_or_callback.answer_animation(
                animation=file_id, caption=caption, parse_mode=parse_mode, reply_markup=keyboard
            )
        elif data["message_type"] == "document":
            await message_or_callback.answer_document(
                document=file_id, caption=caption, parse_mode=parse_mode, reply_markup=keyboard
            )

    # Show summary and confirmation
    time_slot_text = {
        "morning": "🌅 Morning (10 AM)",
        "evening": "🌙 Evening (7 PM)",
        "both": "🔄 Both Morning & Evening",
    }[data["time_slot"]]

    keyboard_display = keyboard_type.title()
    if keyboard_type == "main" and data.get("keyboard_button_text"):
        keyboard_display = f"Main ('{data['keyboard_button_text']}')"

    summary = (
        f"📋 **Promotional Broadcast Summary:**\n\n"
        f"📅 Time Slot: {time_slot_text}\n"
        f"🔢 Repeat Count: {data['repeat_count']} times\n"
        f"⌨️ Keyboard: {keyboard_display}\n"
        f"📱 Message Type: {data['message_type'].title()}\n\n"
        f"This will replace regular notifications during the selected time slots."
    )

    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Schedule Broadcast", callback_data="promo_confirm"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="promo_cancel"),
            ]
        ]
    )

    await message_or_callback.answer(summary, reply_markup=confirm_keyboard, parse_mode="Markdown")
    await state.set_state(PromoStates.confirmation)


@router.callback_query(PromoStates.confirmation, F.data == "promo_cancel")
async def cancel_promo(callback: types.CallbackQuery, state: FSMContext):
    """Handler for cancelling the promotional broadcast."""
    await callback.answer()
    if not callback.message:
        return
    await callback.message.answer("❌ Promotional broadcast cancelled.")
    await state.clear()


@router.callback_query(PromoStates.confirmation, F.data == "promo_confirm")
async def confirm_promo(callback: types.CallbackQuery, state: FSMContext, services: RequestsService):
    """Handler for confirming and scheduling the promotional broadcast."""

    await callback.answer()
    if not callback.message:
        return
    await callback.message.answer("⏳ Scheduling promotional broadcast...")

    data = await state.get_data()

    deadline = datetime.now(UTC) + timedelta(days=data["repeat_count"])
    deadline = deadline.replace(hour=0, minute=0, second=0, microsecond=0)  # Start of final day

    broadcast_data = {
        "message_type": data["message_type"],
        "deadline": deadline,
        "keyboard_type": data["keyboard_type"],
        "keyboard_button_text": data.get("keyboard_button_text"),  # Custom button text
        "created_by_telegram_id": callback.from_user.id,
        "is_active": True,
    }

    # Add message content based on type
    if data["message_type"] == "text":
        broadcast_data.update(
            {
                "message_text": data["message_text"],
                "message_html": data.get("message_html", data["message_text"]),
                "has_text_formatting": data.get("has_formatting", False),
            }
        )
    else:
        # Media messages (photo, video, animation, document)
        broadcast_data.update(
            {
                "media_file_id": data["media_file_id"],
                "caption": data.get("caption", ""),
                "caption_html": data.get("caption_html", ""),
                "has_caption_formatting": data.get("has_caption_formatting", False),
            }
        )

    try:
        # Create broadcasts based on time slot selection
        if data["time_slot"] == "both":
            # Create two separate broadcasts
            morning_data = broadcast_data.copy()
            morning_data["time_slot"] = NotificationTimeSlot.MORNING

            evening_data = broadcast_data.copy()
            evening_data["time_slot"] = NotificationTimeSlot.EVENING

            morning_broadcast = await services.repo.promotional_broadcasts.create(morning_data)
            evening_broadcast = await services.repo.promotional_broadcasts.create(evening_data)

            await callback.message.answer(
                f"✅ **Promotional broadcasts scheduled successfully!**\n\n"
                f"🌅 Morning Broadcast ID: #{morning_broadcast.id}\n"
                f"🌙 Evening Broadcast ID: #{evening_broadcast.id}\n"
                f"🔢 Each will run for {data['repeat_count']} days\n\n"
                f"They will start being sent during the next notification cycles.",
                parse_mode="Markdown",
            )
        else:
            # Create single broadcast
            time_slot = NotificationTimeSlot.MORNING if data["time_slot"] == "morning" else NotificationTimeSlot.EVENING
            broadcast_data["time_slot"] = time_slot

            broadcast = await services.repo.promotional_broadcasts.create(broadcast_data)

            slot_emoji = "🌅" if data["time_slot"] == "morning" else "🌙"
            slot_name = data["time_slot"].title()

            await callback.message.answer(
                f"✅ **Promotional broadcast scheduled successfully!**\n\n"
                f"{slot_emoji} Broadcast ID: #{broadcast.id}\n"
                f"📅 Time Slot: {slot_name}\n"
                f"🔢 Will run for {data['repeat_count']} days\n\n"
                f"It will start being sent during the next {slot_name.lower()} notification cycle.",
                parse_mode="Markdown",
            )

    except Exception as e:
        logger.error(f"Failed to create promotional broadcast: {e}")
        await callback.message.answer(
            "❌ **Error scheduling promotional broadcast.**\n\nPlease try again later or check the logs for details.",
            parse_mode="Markdown",
        )

    await state.clear()


@router.message(Command("promo_list"))
async def promo_list_command(message: types.Message, user: UserSchema, services: RequestsService):
    """Handler for /promo_list command. Shows active promotional broadcasts."""
    # Check if user is admin
    if not user.telegram_id or user.telegram_id not in settings.rbac.owner_ids:
        await message.answer("You don't have permission to use this command")
        return

    try:
        broadcasts = await services.repo.promotional_broadcasts.get_all_active()

        if not broadcasts:
            await message.answer("📭 No active promotional broadcasts found.")
            return

        text = "📋 **Active Promotional Broadcasts:**\n\n"

        for broadcast in broadcasts:
            slot_emoji = "🌅" if broadcast.time_slot.value == "MORNING" else "🌙"
            preview = broadcast.get_display_text()

            keyboard_info = broadcast.keyboard_type or "None"
            if broadcast.keyboard_type == "main" and broadcast.keyboard_button_text:
                keyboard_info = f"Main ('{broadcast.keyboard_button_text}')"

            text += (
                f"{slot_emoji} **ID #{broadcast.id}**\n"
                f"📅 {broadcast.time_slot.value.title()}\n"
                f"🔢 Expires: {broadcast.deadline.strftime('%Y-%m-%d %H:%M')}\n"
                f"📝 {preview}\n"
                f"📱 Type: {broadcast.message_type.title()}\n"
                f"⌨️ Keyboard: {keyboard_info}\n"
                f"⏰ Created: {broadcast.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )

        # Split message if too long
        if len(text) > 4000:
            await message.answer(text[:4000] + "...", parse_mode="Markdown")
            await message.answer(text[4000:], parse_mode="Markdown")
        else:
            await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Failed to list promotional broadcasts: {e}")
        await message.answer("❌ Error loading promotional broadcasts.")


@router.message(Command("promo_cancel"))
async def promo_cancel_command(message: types.Message, user: UserSchema, services: RequestsService):
    """Handler for /promo_cancel command. Cancel a promotional broadcast by ID."""
    # Check if user is admin
    if not user.telegram_id or user.telegram_id not in settings.rbac.owner_ids:
        await message.answer("You don't have permission to use this command")
        return

    # Extract broadcast ID from command
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(
            "❌ **Usage:** `/promo_cancel <broadcast_id>`\n\n"
            "Example: `/promo_cancel 123`\n"
            "Use `/promo_list` to see active broadcasts.",
            parse_mode="Markdown",
        )
        return

    try:
        broadcast_id = int(parts[1])
        success = await services.repo.promotional_broadcasts.deactivate_broadcast(broadcast_id)

        if success:
            await message.answer(f"✅ Promotional broadcast #{broadcast_id} has been cancelled.")
        else:
            await message.answer(f"❌ Promotional broadcast #{broadcast_id} not found or already inactive.")

    except ValueError:
        await message.answer("❌ Invalid broadcast ID. Please provide a number.")
    except Exception as e:
        logger.error(f"Failed to cancel promotional broadcast: {e}")
        await message.answer("❌ Error cancelling promotional broadcast.")


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

import asyncio
from collections.abc import Callable
from functools import wraps

from aiogram import exceptions
from aiogram.types import (
    FSInputFile,
    InlineKeyboardMarkup,
    InlineQueryResult,
    InputMediaPhoto,
    PreparedInlineMessage,
)

from core.infrastructure.config import settings
from core.infrastructure.i18n import t
from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.schemas.users import UserSchema
from core.services.base import BaseService

logger = get_logger(__name__)


class MessageService(BaseService):
    def __init__(
        self,
        repo,
        producer,
        services,
        bot,
    ):
        super().__init__(repo, producer, services, bot)

    def handle_telegram_exceptions(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract telegram_id from either args or kwargs
            telegram_id = kwargs.get("telegram_id") or kwargs.get("user_id")  # Support both for backward compatibility
            if telegram_id is None and len(args) > 1:  # args[0] is self, args[1] would be telegram_id
                telegram_id = args[1]

            try:
                return await func(*args, **kwargs)
            except exceptions.TelegramBadRequest:
                logger.warning("Telegram server says - Bad Request", exc_info=True)
            except exceptions.TelegramForbiddenError:
                logger.warning(f"Target [ID:{telegram_id}]: got TelegramForbiddenError")
            except exceptions.TelegramRetryAfter as e:
                retry_after = e.retry_after
                logger.error(f"Target [ID:{telegram_id}]: Flood limit exceeded. Sleep {retry_after}s")
                await asyncio.sleep(retry_after)
                return await func(*args, **kwargs)
            except exceptions.TelegramAPIError:
                logger.exception(f"Target [ID:{telegram_id}]: failed")
            return False

        return wrapper

    @handle_telegram_exceptions
    async def send_message(
        self,
        telegram_id: int | str,
        text: str,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str | None = None,
    ) -> bool:
        await self.bot.send_message(
            telegram_id,
            text,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        logger.info(f"Target [ID:{telegram_id}]: success")
        return True

    @handle_telegram_exceptions
    async def send_photo(
        self,
        telegram_id: int | str,
        photo_path: str,
        caption: str = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
    ) -> bool:
        await self.bot.send_photo(
            chat_id=telegram_id,
            photo=FSInputFile(photo_path),
            caption=caption,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
        )
        logger.info(f"Target [ID:{telegram_id}]: success")
        return True

    @handle_telegram_exceptions
    async def send_photo_by_file_id(
        self,
        telegram_id: int | str,
        file_id: str,
        caption: str = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str | None = None,
    ) -> bool:
        """Send a photo using its file_id instead of a local file path."""
        await self.bot.send_photo(
            chat_id=telegram_id,
            photo=file_id,  # Use file_id directly
            caption=caption,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        logger.info(f"Target [ID:{telegram_id}]: success")
        return True

    @handle_telegram_exceptions
    async def send_video_by_file_id(
        self,
        telegram_id: int | str,
        file_id: str,
        caption: str = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str | None = None,
    ) -> bool:
        """Send a video using its file_id."""
        await self.bot.send_video(
            chat_id=telegram_id,
            video=file_id,
            caption=caption,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        logger.info(f"Target [ID:{telegram_id}]: success")
        return True

    @handle_telegram_exceptions
    async def send_animation_by_file_id(
        self,
        telegram_id: int | str,
        file_id: str,
        caption: str = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str | None = None,
    ) -> bool:
        """Send an animation/GIF using its file_id."""
        await self.bot.send_animation(
            chat_id=telegram_id,
            animation=file_id,
            caption=caption,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        logger.info(f"Target [ID:{telegram_id}]: success")
        return True

    @handle_telegram_exceptions
    async def send_document_by_file_id(
        self,
        telegram_id: int | str,
        file_id: str,
        caption: str = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str | None = None,
    ) -> bool:
        """Send a document using its file_id."""
        await self.bot.send_document(
            chat_id=telegram_id,
            document=file_id,
            caption=caption,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        logger.info(f"Target [ID:{telegram_id}]: success")
        return True

    @handle_telegram_exceptions
    async def send_photos_media_group(
        self,
        telegram_id: int | str,
        media_paths: list[str],
        caption: str = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
    ) -> bool:
        media_group = [
            InputMediaPhoto(media=FSInputFile(media_path), caption=caption if index == 0 else None)
            for index, media_path in enumerate(media_paths)
        ]
        await self.bot.send_media_group(
            chat_id=telegram_id,
            media=media_group,
            disable_notification=disable_notification,
        )
        logger.info(f"Target [ID:{telegram_id}]: success")
        return True

    async def _raw_broadcast(
        self,
        telegram_ids: list[str | int],
        text: str,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
    ) -> int:
        count = 0
        try:
            for telegram_id in telegram_ids:
                if await self.send_message(telegram_id, text, disable_notification, reply_markup):
                    count += 1
                await asyncio.sleep(0.05)
        finally:
            logger.info(f"{count} messages successful sent.")
        return count

    async def _raw_photo_broadcast(
        self,
        telegram_ids: list[str | int],
        file_id: str,
        caption: str = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup = None,
    ) -> int:
        """Broadcast a photo to multiple users using file_id."""
        count = 0
        try:
            for telegram_id in telegram_ids:
                if await self.send_photo_by_file_id(telegram_id, file_id, caption, disable_notification, reply_markup):
                    count += 1
                await asyncio.sleep(0.05)
        finally:
            logger.info(f"{count} photo messages successfully sent.")
        return count

    async def broadcast(
        self,
        users: list[UserSchema],
        message_key: str,
        disable_notification: bool = False,
        reply_markup_func: Callable[[str], InlineKeyboardMarkup] = None,
        posthog_event: str = None,
        **format_kwargs,
    ) -> int:
        count = 0
        try:
            for user in users:
                lang = user.language_code or user.tg_language_code or "en"
                text = t(message_key, lang).format(**format_kwargs)

                reply_markup = reply_markup_func(lang) if reply_markup_func is not None else None

                if user.telegram_id and await self.send_message(
                    user.telegram_id, text, disable_notification, reply_markup
                ):
                    count += 1
                await asyncio.sleep(0.05)
        finally:
            if posthog_event:
                posthog.capture(
                    distinct_id=user.id,
                    event=posthog_event,
                    properties={"success_count": count, "total_count": len(users), "message_key": message_key},
                )
            logger.info(f"{count} localized messages successfully sent.")
        return count

    async def admin_broadcast(
        self, text: str, disable_notification: bool = False, reply_markup: InlineKeyboardMarkup = None, **format_kwargs
    ) -> int:
        # text_prefix = "🚨 ADMIN 🚨\n\n"
        text_prefix = ""
        return await self._raw_broadcast(
            telegram_ids=settings.rbac.owner_ids,
            text=text_prefix + text,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
            **format_kwargs,
        )

    async def get_share_message_id(self, telegram_id: int, InlineQueryResult: InlineQueryResult) -> str:
        prepared_message: PreparedInlineMessage = await self.bot.save_prepared_inline_message(
            user_id=telegram_id,
            result=InlineQueryResult,
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True,
            allow_bot_chats=True,
        )
        return prepared_message.id

    async def queue_admin_broadcast(self, text: str):
        """Queue a job to send an admin broadcast"""
        await self.services.worker.enqueue_job("admin_broadcast_job", text)

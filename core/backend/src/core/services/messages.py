import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps

from aiogram import exceptions
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineQueryResult,
    InputMediaPhoto,
    PreparedInlineMessage,
)

from core.infrastructure.i18n import supported_locale, t
from core.infrastructure.logging import get_logger
from core.infrastructure.posthog import posthog
from core.infrastructure.telegram.admin_messages import send_admin_message
from core.schemas.users import UserSchema
from core.services.base import BaseService

logger = get_logger(__name__)


class SendFailure:
    """Falsy result of a failed Telegram send (see ``MessageService.handle_telegram_exceptions``)."""

    FORBIDDEN = "forbidden"  # blocked the bot / deactivated account
    BAD_REQUEST = "bad_request"  # chat not found, bad markup, …
    OTHER = "other"  # any other Telegram API error (or an unexpected exception)

    __slots__ = ("error_code",)

    def __init__(self, error_code: str):
        self.error_code = error_code

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        # Equal to False like the bare ``False`` it replaces; equal to a failure with the same code.
        if isinstance(other, SendFailure):
            return other.error_code == self.error_code
        return other is False

    def __hash__(self) -> int:
        # Must match __eq__: a failure equals False, so it hashes like False.
        return hash(False)

    def __repr__(self) -> str:
        return f"SendFailure({self.error_code!r})"


def user_language(user: UserSchema) -> str:
    """The language a bot message to ``user`` goes out in (one we have copy for, else English)."""
    return supported_locale(user.language_code or user.tg_language_code)


def send_error_code(result: object) -> str | None:
    """``None`` for a successful send result, else the failure's error code."""
    if result:
        return None
    return result.error_code if isinstance(result, SendFailure) else SendFailure.OTHER


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
        """Catch Telegram errors of a send: success returns the send's value, a failure a falsy ``SendFailure``.

        ``if await send(...)`` keeps working; ``result.error_code`` says why it failed. On
        ``TelegramForbiddenError`` the user is also flagged ``bot_blocked_at``.
        """

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Extract telegram_id from either args or kwargs
            telegram_id = kwargs.get("telegram_id") or kwargs.get("user_id")  # Support both for backward compatibility
            if telegram_id is None and args:
                telegram_id = args[0]

            for attempt in range(2):  # one retry after a flood limit, with the same error handling
                try:
                    return await func(self, *args, **kwargs)
                except exceptions.TelegramBadRequest:
                    logger.warning("Telegram server says - Bad Request", exc_info=True)
                    return SendFailure(SendFailure.BAD_REQUEST)
                except exceptions.TelegramForbiddenError:
                    logger.warning(f"Target [ID:{telegram_id}]: got TelegramForbiddenError")
                    await self._mark_bot_blocked(telegram_id)
                    return SendFailure(SendFailure.FORBIDDEN)
                except exceptions.TelegramRetryAfter as e:
                    logger.error(f"Target [ID:{telegram_id}]: Flood limit exceeded. Sleep {e.retry_after}s")
                    if attempt == 0:
                        await asyncio.sleep(e.retry_after)
                        continue
                except exceptions.TelegramAPIError:
                    logger.exception(f"Target [ID:{telegram_id}]: failed")
                return SendFailure(SendFailure.OTHER)
            return SendFailure(SendFailure.OTHER)

        return wrapper

    async def _mark_bot_blocked(self, telegram_id: int | str | None) -> None:
        """Set ``users.bot_blocked_at``. Never breaks the send or the caller's transaction."""
        if telegram_id is None:
            return
        try:
            # A savepoint, so a failing UPDATE can't abort the caller's transaction.
            async with self.repo.session.begin_nested():
                await self.repo.users.mark_bot_blocked(int(telegram_id), datetime.now(UTC))
        except Exception:
            logger.exception(f"Target [ID:{telegram_id}]: could not flag bot_blocked_at")

    @handle_telegram_exceptions
    async def send_message(
        self,
        telegram_id: int | str,
        text: str,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
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
    async def send_poll(
        self,
        telegram_id: int | str,
        question: str,
        options: list[str],
        *,
        poll_type: str = "regular",
        correct_option_id: int | None = None,
        explanation: str | None = None,
        is_anonymous: bool = True,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> bool:
        """Send a native poll (``poll_type="quiz"`` with ``correct_option_id`` for a quiz). Plain text:
        the bot's default parse mode (HTML) is switched off for the question and the explanation."""
        await self.bot.send_poll(
            chat_id=telegram_id,
            question=question,
            options=options,
            type=poll_type,
            correct_option_ids=None if correct_option_id is None else [correct_option_id],
            explanation=explanation,
            is_anonymous=is_anonymous,
            question_parse_mode=None,
            explanation_parse_mode=None,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
        )
        logger.info(f"Target [ID:{telegram_id}]: success")
        return True

    @handle_telegram_exceptions
    async def send_photo(
        self,
        telegram_id: int | str,
        photo_path: str,
        caption: str | None = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
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
        caption: str | None = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
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
    async def send_photo_bytes(
        self,
        telegram_id: int | str,
        photo: bytes,
        *,
        filename: str = "photo.jpg",
        caption: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
        parse_mode: str | None = None,
        disable_notification: bool = False,
    ) -> bool:
        """Send a photo rendered in memory (e.g. a generated image). ``parse_mode=None`` sends the caption as
        plain text — the bot's default (HTML) is switched off, so user text in it can't break the markup."""
        await self.bot.send_photo(
            chat_id=telegram_id,
            photo=BufferedInputFile(photo, filename=filename),
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
        caption: str | None = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
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
        caption: str | None = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
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
        caption: str | None = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
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
        caption: str | None = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
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
        reply_markup: InlineKeyboardMarkup | None = None,
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
        caption: str | None = None,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
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

    async def send_localized(
        self,
        user: UserSchema,
        message_key: str,
        disable_notification: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
        **format_kwargs,
    ) -> bool | SendFailure:
        """Send the i18n text ``message_key`` in the user's language. Falsy ``SendFailure`` on failure."""
        if not user.telegram_id:
            return SendFailure(SendFailure.BAD_REQUEST)
        text = t(message_key, user_language(user)).format(**format_kwargs)
        return await self.send_message(user.telegram_id, text, disable_notification, reply_markup)

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
                if not user.telegram_id:
                    continue
                reply_markup = reply_markup_func(user_language(user)) if reply_markup_func is not None else None
                if await self.send_localized(user, message_key, disable_notification, reply_markup, **format_kwargs):
                    count += 1
                await asyncio.sleep(0.05)
        finally:
            if posthog_event:
                posthog.capture(
                    distinct_id="system",
                    event=posthog_event,
                    properties={"success_count": count, "total_count": len(users), "message_key": message_key},
                )
            logger.info(f"{count} localized messages successfully sent.")
        return count

    async def admin_broadcast(
        self, text: str, *, rich_html: str | None = None, silent: bool = False, chat_ids: list[int] | None = None
    ) -> int:
        """Send an admin message right now (Telegram HTML; see core.infrastructure.telegram.admin_messages)."""
        return await send_admin_message(self.bot, text, rich_html=rich_html, silent=silent, chat_ids=chat_ids)

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

    async def queue_admin_broadcast(self, text: str, *, rich_html: str | None = None, silent: bool = False):
        """Queue an admin message. ``text`` is Telegram HTML — escape user content with ``esc()``.

        ``rich_html`` optionally adds a Rich Message body (tables, details); ``text`` is its fallback.
        ``silent`` delivers without sound — use it for routine, non-actionable events.
        """
        await self.services.worker.enqueue_job("admin_broadcast_job", text, rich_html=rich_html, silent=silent)

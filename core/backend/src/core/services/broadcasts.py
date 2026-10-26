"""Broadcasts service: the admin composer for promotional broadcasts.

- list (active / completed) + per-slot active counts for the warning banner
- create (a ``time_slot='both'`` request creates TWO independent rows)
- edit (PATCH a single row) / cancel (soft delete: ``is_active=False``)
- preview (compose the message and send it to the acting admin's OWN chat)
- send-now (immediate all-users blast through the core ``user_broadcast_job`` arq job)
- media upload (send the uploaded file via the bot to mint a Telegram ``file_id``)
- format (text + entities -> HTML via the shared formatting helpers)
- stats (delivery counters)

Every MUTATING method records an audit row (``target_type='broadcast'``). Gating
(AdminUser vs OwnerUser for send-now) is enforced in the router; this service assumes
the caller is already authorized. Failures raise ``BroadcastNotFoundException`` /
``InvalidBroadcastException`` (the router maps them to 404 / 400); this module never
imports FastAPI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from aiogram.types import BufferedInputFile

from core.exceptions import BroadcastNotFoundException, InvalidBroadcastException
from core.infrastructure.database.models import PromotionalBroadcast
from core.infrastructure.database.models.enums import NotificationTimeSlot
from core.infrastructure.logging import get_logger
from core.schemas.broadcasts import (
    BroadcastCreateRequest,
    BroadcastCreateResponse,
    BroadcastDeliveryStats,
    BroadcastDetail,
    BroadcastListItem,
    BroadcastListResponse,
    BroadcastMediaUploadResponse,
    BroadcastPreviewRequest,
    BroadcastSendNowRequest,
    BroadcastUpdateRequest,
)
from core.schemas.users import UserSchema
from core.services.base import BaseService
from core.services.broadcast_formatting import broadcast_content, build_keyboard_markup, entities_to_html
from core.services.messages import user_language

logger = get_logger(__name__)

# Telegram media kinds we accept for upload.
_MEDIA_KINDS = {"photo", "video", "animation", "document"}

# PATCH fields whose columns are NOT NULL: an explicit null is a 400, not a failed UPDATE.
_NOT_NULL_FIELDS = ("message_type", "deadline", "priority")

# Bot API upload limits: 10 MB for photos, 50 MB for other files.
_MB = 1024 * 1024
UPLOAD_LIMITS = {"photo": 10 * _MB, "video": 50 * _MB, "animation": 50 * _MB, "document": 50 * _MB}


class BroadcastsService(BaseService):
    # ── Reads ──────────────────────────────────────────────────────────────────

    async def list_broadcasts(self) -> BroadcastListResponse:
        """Active + completed broadcasts, plus active counts per time slot."""
        active = await self.repo.promotional_broadcasts.list_for_admin(active=True)
        completed = await self.repo.promotional_broadcasts.list_for_admin(active=False)
        active_by_slot = await self.repo.promotional_broadcasts.count_active_by_time_slot()
        return BroadcastListResponse(
            active=[self._to_list_item(b) for b in active],
            completed=[self._to_list_item(b) for b in completed],
            active_by_time_slot=active_by_slot,
        )

    async def get_broadcast(self, broadcast_id: int) -> BroadcastDetail | None:
        broadcast = await self.repo.promotional_broadcasts.get_by_id(broadcast_id)
        if broadcast is None:
            return None
        return self._to_detail(broadcast)

    async def get_stats(self, broadcast_id: int) -> BroadcastDeliveryStats:
        broadcast = await self._require(broadcast_id)
        return BroadcastDeliveryStats.model_validate(broadcast)

    # ── Mutations (each records an audit row) ──────────────────────────────────

    async def create(self, actor: UserSchema, body: BroadcastCreateRequest) -> BroadcastCreateResponse:
        """Create one or (for time_slot='both') two independent broadcast rows."""
        self._validate_content(body.message_type, body.message_text, body.media_file_id)
        self._require_creator_id(actor)

        base = self._base_create_payload(actor, body)

        if body.time_slot == "both":
            slots = [NotificationTimeSlot.MORNING, NotificationTimeSlot.EVENING]
        elif body.time_slot == "morning":
            slots = [NotificationTimeSlot.MORNING]
        else:
            slots = [NotificationTimeSlot.EVENING]

        ids: list[int] = []
        for slot in slots:
            payload = {**base, "time_slot": slot}
            row = await self.repo.promotional_broadcasts.create(payload)
            ids.append(row.id)

        await self.services.audit_log.record(
            actor=actor,
            action="broadcast_create",
            target_type="broadcast",
            target_id=",".join(str(i) for i in ids),
            detail={
                "time_slot": body.time_slot,
                "message_type": body.message_type,
                "ids": ids,
                "rows_created": len(ids),
            },
        )
        return BroadcastCreateResponse(ids=ids)

    async def edit(self, actor: UserSchema, broadcast_id: int, body: BroadcastUpdateRequest) -> BroadcastDetail:
        """PATCH a single broadcast row (a 'both' pair is two independent rows)."""
        current = await self._require(broadcast_id)

        changes: dict = {}
        fields = body.model_dump(exclude_unset=True)
        for key in _NOT_NULL_FIELDS:
            if key in fields and fields[key] is None:
                raise InvalidBroadcastException(f"{key} can't be null")
        for key in (
            "message_type",
            "deadline",
            "priority",
            "media_file_id",
            "keyboard_type",
            "keyboard_button_text",
            "target_filter",
        ):
            if key in fields:
                changes[key] = fields[key]

        # Text + its HTML/flag are derived together so message_html stays consistent. A flag
        # that isn't sent (or is null) keeps the row's current value.
        text_fmt = fields.get("has_text_formatting")
        if "message_text" in fields:
            text = fields["message_text"]
            has_fmt = current.has_text_formatting if text_fmt is None else text_fmt
            changes["message_text"] = text
            changes["message_html"] = text
            changes["has_text_formatting"] = bool(has_fmt) if text else False
        elif text_fmt is not None:
            changes["has_text_formatting"] = bool(text_fmt) and bool(current.message_text)

        caption_fmt = fields.get("has_caption_formatting")
        if "caption" in fields:
            caption = fields["caption"]
            has_fmt = current.has_caption_formatting if caption_fmt is None else caption_fmt
            changes["caption"] = caption
            changes["caption_html"] = caption
            changes["has_caption_formatting"] = bool(has_fmt) if caption else False
        elif caption_fmt is not None:
            changes["has_caption_formatting"] = bool(caption_fmt) and bool(current.caption)

        # The row as it would be saved must still be sendable (e.g. not a photo without a file).
        self._validate_content(
            changes.get("message_type", current.message_type),
            changes.get("message_text", current.message_text),
            changes.get("media_file_id", current.media_file_id),
        )

        if changes:
            await self.repo.promotional_broadcasts.update(broadcast_id, changes)

        await self.services.audit_log.record(
            actor=actor,
            action="broadcast_edit",
            target_type="broadcast",
            target_id=str(broadcast_id),
            detail={"changed_fields": sorted(changes.keys())},
        )
        broadcast = await self._require(broadcast_id)
        return self._to_detail(broadcast)

    async def cancel(self, actor: UserSchema, broadcast_id: int) -> BroadcastDetail:
        """Soft-cancel a broadcast: ``is_active=False`` + ``completed_at`` stamp.

        A row that is no longer active (cancelled, completed or past its deadline) comes back
        unchanged: no new ``completed_at``, no audit row.
        """
        current = await self._require(broadcast_id)
        if not self._effective_active(current):
            return self._to_detail(current)

        await self.repo.promotional_broadcasts.update(
            broadcast_id,
            {"is_active": False, "completed_at": datetime.now(UTC)},
        )

        await self.services.audit_log.record(
            actor=actor,
            action="broadcast_cancel",
            target_type="broadcast",
            target_id=str(broadcast_id),
            detail=None,
        )
        broadcast = await self._require(broadcast_id)
        return self._to_detail(broadcast)

    async def send_now(self, actor: UserSchema, body: BroadcastSendNowRequest) -> bool:
        """Immediate all-users blast (OwnerUser) through the core ``user_broadcast_job``.

        The same worker job the bots' ``/broadcast`` confirm flow uses: it sends through the
        notification engine (delivery log, blocked users skipped) to every user who can get
        it. A saved row (``broadcast_id``) gets its delivery counters moved. Audience
        targeting is not supported.
        """
        broadcast_data = await self._build_send_payload(body)

        # Audit row FIRST, enqueue LAST: once queued the blast can't be taken back, so nothing
        # that can still fail (and roll the request back) may come after it.
        await self.services.audit_log.record(
            actor=actor,
            action="broadcast_send_now",
            target_type="broadcast",
            target_id=str(body.broadcast_id) if body.broadcast_id is not None else None,
            detail={
                "message_type": broadcast_data.get("message_type"),
                "from_broadcast_id": body.broadcast_id,
                "run_id": broadcast_data["run_id"],
            },
        )

        await self.services.worker.enqueue_job(
            "user_broadcast_job",
            broadcast_data=broadcast_data,
            requester_telegram_id=actor.telegram_id,
            broadcast_id=body.broadcast_id,
        )
        return True

    async def preview(self, actor: UserSchema, body: BroadcastPreviewRequest) -> bool:
        """Send the composed message to the acting admin's OWN chat (no DB write)."""
        if actor.telegram_id is None:
            raise InvalidBroadcastException("Acting admin has no Telegram chat to preview to")

        keyboard = build_keyboard_markup(
            {"keyboard_type": body.keyboard_type, "keyboard_button_text": body.keyboard_button_text},
            user_language(actor),
        )

        if body.message_type == "text":
            text = body.message_html if body.has_text_formatting else body.message_text
            if not text:
                raise InvalidBroadcastException("Text message requires message_text")
            content = {"type": "text", "text": text, "parse_mode": "HTML" if body.has_text_formatting else None}
        else:
            if not body.media_file_id:
                raise InvalidBroadcastException("Media message requires media_file_id")
            content = {
                "type": body.message_type,
                "media_file_id": body.media_file_id,
                "caption": body.caption_html if body.has_caption_formatting else body.caption,
                "parse_mode": "HTML" if body.has_caption_formatting else None,
            }

        sent = await self.services.messages.send_content(actor.telegram_id, content, keyboard)
        return bool(sent)  # a failed send is a falsy SendFailure, not False

    async def upload_media(
        self,
        actor: UserSchema,
        *,
        message_type: str,
        filename: str,
        content: bytes,
    ) -> BroadcastMediaUploadResponse:
        """Send the uploaded file to the acting admin via the bot to mint a file_id.

        Telegram only hands out a reusable ``file_id`` once the bot has actually sent
        the media to a chat. We send it to the acting admin's chat, read the file_id
        off the returned message, then DELETE that throwaway message immediately so it
        doesn't linger in the admin's chat looking like a duplicate broadcast — the
        ``file_id`` stays valid after the source message is deleted.
        """
        if message_type not in _MEDIA_KINDS:
            raise InvalidBroadcastException(f"Unsupported media type: {message_type}")
        if actor.telegram_id is None:
            raise InvalidBroadcastException("Acting admin has no Telegram chat to upload through")
        if not content:
            raise InvalidBroadcastException("Empty file")
        self.check_upload_size(message_type, len(content))

        input_file = BufferedInputFile(content, filename=filename or "upload")

        try:
            if message_type == "photo":
                message = await self.bot.send_photo(actor.telegram_id, photo=input_file)
                file_id = message.photo[-1].file_id if message.photo else None
            elif message_type == "video":
                message = await self.bot.send_video(actor.telegram_id, video=input_file)
                file_id = message.video.file_id if message.video else None
            elif message_type == "animation":
                message = await self.bot.send_animation(actor.telegram_id, animation=input_file)
                file_id = message.animation.file_id if message.animation else None
            else:  # document
                message = await self.bot.send_document(actor.telegram_id, document=input_file)
                file_id = message.document.file_id if message.document else None
        except Exception as e:  # noqa: BLE001 — surface a clean 400 to the composer
            logger.error(f"Broadcast media upload failed: {e}", exc_info=True)
            raise InvalidBroadcastException("Failed to upload media via Telegram") from e
        if not file_id:  # Telegram answered with another kind of message (e.g. a GIF sent as a document)
            raise InvalidBroadcastException("Failed to upload media via Telegram")

        # Remove the throwaway upload message — the minted file_id remains valid.
        try:
            await self.bot.delete_message(actor.telegram_id, message.message_id)
        except Exception as e:  # noqa: BLE001 — best-effort; file_id is already minted
            logger.warning(f"Could not delete broadcast upload-preview message: {e}")

        return BroadcastMediaUploadResponse(file_id=file_id, message_type=message_type)

    @staticmethod
    def check_upload_size(message_type: str, size: int | None) -> None:
        """Refuse a file over Telegram's upload limit for its kind (the router checks it before the body is read)."""
        limit = UPLOAD_LIMITS.get(message_type)
        if limit is not None and size is not None and size > limit:
            raise InvalidBroadcastException(f"File too large (max {limit // _MB} MB for a {message_type})")

    def format_text(self, text: str, entities: list[dict] | None) -> str:
        """Convert text + Telegram entities to HTML via the shared formatting helpers.

        The web composer sends entities as JSON dicts (``type/offset/length/url``);
        the shared helper expects attribute access, so we wrap them in a tiny shim.
        """
        normalized = [SimpleNamespace(**entity) for entity in entities] if entities else None
        return entities_to_html(text, normalized)

    # ── Internals ──────────────────────────────────────────────────────────────

    async def _require(self, broadcast_id: int) -> PromotionalBroadcast:
        broadcast = await self.repo.promotional_broadcasts.get_by_id(broadcast_id)
        if broadcast is None:
            raise BroadcastNotFoundException("Broadcast not found")
        return broadcast

    @staticmethod
    def _require_creator_id(actor: UserSchema) -> None:
        """The creator's Telegram id goes into ``created_by_user_id`` (NOT NULL)."""
        if actor.telegram_id is None:
            raise InvalidBroadcastException("Acting admin has no Telegram id")

    @staticmethod
    def _effective_active(b: PromotionalBroadcast) -> bool:
        """Active = not cancelled/completed AND the deadline is still ahead (an expired row keeps
        ``is_active`` until a send cycle flips it)."""
        return b.is_active and not b.is_expired

    @staticmethod
    def _validate_content(message_type: str, message_text: str | None, media_file_id: str | None) -> None:
        if message_type == "text":
            if not message_text:
                raise InvalidBroadcastException("Text broadcast requires message_text")
        elif not media_file_id:
            raise InvalidBroadcastException(f"{message_type} broadcast requires media_file_id")

    @staticmethod
    def _base_create_payload(actor: UserSchema, body: BroadcastCreateRequest) -> dict:
        payload: dict = {
            "message_type": body.message_type,
            "deadline": body.deadline,
            "priority": body.priority,
            "keyboard_type": body.keyboard_type,
            "keyboard_button_text": body.keyboard_button_text,
            "created_by_user_id": actor.telegram_id,  # stores telegram_id (standardized)
            "is_active": True,
            "target_filter": body.target_filter,
        }
        if body.message_type == "text":
            payload.update(
                {
                    "message_text": body.message_text,
                    "message_html": body.message_text,
                    "has_text_formatting": body.has_text_formatting,
                }
            )
        else:
            payload.update(
                {
                    "media_file_id": body.media_file_id,
                    "caption": body.caption,
                    "caption_html": body.caption,
                    "has_caption_formatting": body.has_caption_formatting,
                }
            )
        return payload

    async def _build_send_payload(self, body: BroadcastSendNowRequest) -> dict:
        """Build the ``broadcast_data`` dict the job consumes (canonical ``broadcast_content`` keys).

        From a stored broadcast (``broadcast_id``) or inline content; validated here so a bad
        payload is a 400 now, not a failed job later. ``run_id`` makes the job idempotent.
        """
        if body.broadcast_id is not None:
            broadcast = await self._require(body.broadcast_id)
            payload: dict = {
                "message_type": broadcast.message_type,
                "message_text": broadcast.message_text,
                "message_html": broadcast.message_html,
                "has_text_formatting": broadcast.has_text_formatting,
                "media_file_id": broadcast.media_file_id,
                "caption": broadcast.caption,
                "caption_html": broadcast.caption_html,
                "has_caption_formatting": broadcast.has_caption_formatting,
                "media_metadata": broadcast.media_metadata,
                "keyboard_type": broadcast.keyboard_type,
                "keyboard_button_text": broadcast.keyboard_button_text,
            }
        else:
            if not body.message_type:
                raise InvalidBroadcastException("send-now requires broadcast_id or message_type")
            payload = {
                "message_type": body.message_type,
                "message_text": body.message_text,
                "message_html": body.message_html or body.message_text,
                "has_text_formatting": body.has_text_formatting,
                "media_file_id": body.media_file_id,
                "caption": body.caption,
                "caption_html": body.caption_html or body.caption,
                "has_caption_formatting": body.has_caption_formatting,
                "keyboard_type": body.keyboard_type,
                "keyboard_button_text": body.keyboard_button_text,
            }
        broadcast_content(payload)  # raises InvalidBroadcastException with the user-facing reason
        payload["run_id"] = uuid4().hex
        return payload

    @staticmethod
    def _to_list_item(b: PromotionalBroadcast) -> BroadcastListItem:
        return BroadcastListItem(
            id=b.id,
            message_type=b.message_type,
            time_slot=str(b.time_slot),
            preview=b.get_display_text(),
            priority=b.priority,
            is_active=BroadcastsService._effective_active(b),
            deadline=b.deadline,
            completed_at=b.completed_at,
            keyboard_type=b.keyboard_type,
            created_by_user_id=b.created_by_user_id,
            created_at=b.created_at,
            sent_count=b.sent_count,
            success_count=b.success_count,
            fail_count=b.fail_count,
            cycles_run=b.cycles_run,
            last_sent_at=b.last_sent_at,
        )

    @staticmethod
    def _to_detail(b: PromotionalBroadcast) -> BroadcastDetail:
        return BroadcastDetail(
            id=b.id,
            message_type=b.message_type,
            message_text=b.message_text,
            message_html=b.message_html,
            media_file_id=b.media_file_id,
            caption=b.caption,
            caption_html=b.caption_html,
            has_text_formatting=b.has_text_formatting,
            has_caption_formatting=b.has_caption_formatting,
            time_slot=str(b.time_slot),
            deadline=b.deadline,
            priority=b.priority,
            keyboard_type=b.keyboard_type,
            keyboard_button_text=b.keyboard_button_text,
            is_active=BroadcastsService._effective_active(b),
            completed_at=b.completed_at,
            created_by_user_id=b.created_by_user_id,
            target_filter=b.target_filter,
            created_at=b.created_at,
            updated_at=b.updated_at,
            stats=BroadcastDeliveryStats.model_validate(b),
        )

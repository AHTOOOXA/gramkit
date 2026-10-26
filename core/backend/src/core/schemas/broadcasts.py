"""Schemas for the admin Broadcasts composer (core admin API, ``/admin/broadcasts``).

A broadcast is either scheduled (sent in the morning/evening notification slot until its
deadline) or sent to everyone right away. Delivery tracking is sent/success/fail/cycles
only — Telegram exposes neither read receipts nor click-through, so we never model them.

``target_filter`` is intentionally NOT modelled as an enforced audience filter: the
send pipeline ignores it. The composer surfaces it as "not enforced yet".
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Message / keyboard / slot vocabularies (kept in sync with the model + send pipeline).
MessageType = Literal["text", "photo", "video", "animation", "document"]
KeyboardType = Literal["none", "main", "daily"]
TimeSlot = Literal["morning", "evening", "both"]


class BroadcastDeliveryStats(BaseModel):
    """Delivery counters for a single broadcast row.

    Read receipts / CTR are impossible on Telegram — only these are tracked.
    """

    sent_count: int
    success_count: int
    fail_count: int
    cycles_run: int
    last_sent_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BroadcastListItem(BaseModel):
    """One row in the admin broadcasts table."""

    id: int
    message_type: str
    time_slot: str
    preview: str
    priority: int
    is_active: bool
    deadline: datetime
    completed_at: datetime | None = None
    keyboard_type: str | None = None
    created_by_user_id: int | None = None
    created_at: datetime
    # Delivery counters (flattened for the table).
    sent_count: int
    success_count: int
    fail_count: int
    cycles_run: int
    last_sent_at: datetime | None = None


class BroadcastListResponse(BaseModel):
    """Active + completed broadcasts plus a per-slot active-count map.

    ``active_by_time_slot`` lets the UI warn when >1 active broadcast share a slot
    (only the highest-priority one actually sends per cycle).
    """

    active: list[BroadcastListItem]
    completed: list[BroadcastListItem]
    active_by_time_slot: dict[str, int]


class BroadcastDetail(BaseModel):
    """Full broadcast for the detail view / edit form (incl. delivery stats)."""

    id: int
    message_type: str
    message_text: str | None = None
    message_html: str | None = None
    media_file_id: str | None = None
    caption: str | None = None
    caption_html: str | None = None
    has_text_formatting: bool
    has_caption_formatting: bool
    time_slot: str
    deadline: datetime
    priority: int
    keyboard_type: str | None = None
    keyboard_button_text: str | None = None
    is_active: bool
    completed_at: datetime | None = None
    created_by_user_id: int | None = None
    target_filter: dict | None = None
    created_at: datetime
    updated_at: datetime | None = None
    stats: BroadcastDeliveryStats


class BroadcastCreateRequest(BaseModel):
    """Create one (morning/evening) or two (both) broadcast rows.

    For media broadcasts, ``media_file_id`` must already be minted via
    ``POST /admin/broadcasts/media``. ``time_slot='both'`` creates TWO independent
    rows (one morning, one evening) — edit/cancel act on a single row.
    """

    message_type: MessageType
    time_slot: TimeSlot
    deadline: datetime
    priority: int = Field(80, ge=0, le=1000)

    # Text content (message_type == 'text').
    message_text: str | None = None
    has_text_formatting: bool = False

    # Media content (message_type != 'text').
    media_file_id: str | None = None
    caption: str | None = None
    has_caption_formatting: bool = False

    # Keyboard config.
    keyboard_type: KeyboardType = "none"
    keyboard_button_text: str | None = None

    # Cosmetic only — NOT enforced by the send pipeline.
    target_filter: dict | None = None

    @field_validator("message_text")
    @classmethod
    def _strip_text(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


class BroadcastUpdateRequest(BaseModel):
    """PATCH body — every field optional; only provided fields are changed.

    Acts on a SINGLE row (a 'both' pair is two independent rows).
    """

    message_type: MessageType | None = None
    deadline: datetime | None = None
    priority: int | None = Field(None, ge=0, le=1000)
    message_text: str | None = None
    has_text_formatting: bool | None = None
    media_file_id: str | None = None
    caption: str | None = None
    has_caption_formatting: bool | None = None
    keyboard_type: KeyboardType | None = None
    keyboard_button_text: str | None = None
    target_filter: dict | None = None


class BroadcastFormatRequest(BaseModel):
    """Convert raw text + Telegram entities to the HTML the send pipeline ships."""

    text: str
    entities: list[dict] | None = None


class BroadcastFormatResponse(BaseModel):
    html: str


class BroadcastPreviewRequest(BaseModel):
    """Compose + send a preview to the acting admin's OWN chat (no DB write)."""

    message_type: MessageType
    message_text: str | None = None
    message_html: str | None = None
    has_text_formatting: bool = False
    media_file_id: str | None = None
    caption: str | None = None
    caption_html: str | None = None
    has_caption_formatting: bool = False
    keyboard_type: KeyboardType = "none"
    keyboard_button_text: str | None = None


class BroadcastPreviewResponse(BaseModel):
    sent: bool


class BroadcastMediaUploadResponse(BaseModel):
    """Telegram ``file_id`` minted by sending the uploaded file via the bot."""

    file_id: str
    message_type: str


class BroadcastSendNowRequest(BaseModel):
    """Trigger an immediate all-users blast (OwnerUser). Reuses the arq job.

    Either send an existing broadcast by ``broadcast_id`` (re-uses its stored
    content) or pass inline content. Audience targeting is NOT supported.
    """

    broadcast_id: int | None = None
    message_type: MessageType | None = None
    message_text: str | None = None
    message_html: str | None = None
    has_text_formatting: bool = False
    media_file_id: str | None = None
    caption: str | None = None
    caption_html: str | None = None
    has_caption_formatting: bool = False
    keyboard_type: KeyboardType = "none"
    keyboard_button_text: str | None = None


class BroadcastSendNowResponse(BaseModel):
    queued: bool


class BroadcastCreateResponse(BaseModel):
    """IDs of the created row(s). 'both' yields two ids."""

    ids: list[int]

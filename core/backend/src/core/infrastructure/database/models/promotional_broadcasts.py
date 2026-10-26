from datetime import UTC, datetime

from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import func

from core.infrastructure.database.models.base import Base, CreatedAtMixin, TableNameMixin, UpdatedAtMixin, int_pk
from core.infrastructure.database.models.enums import NotificationTimeSlot


class PromotionalBroadcast(Base, TableNameMixin, CreatedAtMixin, UpdatedAtMixin):
    """
    Promotional broadcasts that are queued to be sent during regular notification cycles
    """

    id: Mapped[int_pk]

    # Message content - unified approach
    message_type: Mapped[str] = mapped_column(String(20))  # 'text', 'photo', 'video', 'animation', 'document'

    # Text content (for text messages)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_html: Mapped[str | None] = mapped_column(Text, nullable=True)  # Formatted version

    # Media content (for photos, videos, animations, documents)
    media_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Caption (for media messages or as fallback)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_html: Mapped[str | None] = mapped_column(Text, nullable=True)  # Formatted version

    # Additional media info (stored as JSON for flexibility)
    media_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Formatting flags
    has_text_formatting: Mapped[bool] = mapped_column(Boolean, default=False)
    has_caption_formatting: Mapped[bool] = mapped_column(Boolean, default=False)

    # Scheduling configuration
    time_slot: Mapped[NotificationTimeSlot] = mapped_column(Enum(NotificationTimeSlot, native_enum=False))
    deadline: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))  # When the broadcast expires
    priority: Mapped[int] = mapped_column(Integer, default=80)  # Higher than regular notifications

    # Keyboard configuration
    keyboard_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'none', 'main', 'daily'
    keyboard_button_text: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Custom button text

    # Metadata
    #
    # NOTE: ``created_by_user_id`` stores the Telegram id
    # (int) of the admin who created the broadcast — NOT the internal users.id UUID.
    # The bot has always written the Telegram id here, and the web composer does the
    # same. The column name is kept for backwards compatibility (no migration to
    # rename), but its semantics are "creator telegram_id". BIGINT: Telegram ids no
    # longer fit int4.
    created_by_user_id: Mapped[int] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Delivery tracking. Read receipts / CTR are impossible on Telegram —
    # only sent/success/fail/cycle counters are tracked. Written by
    # ``record_send_result`` after each send cycle completes.
    sent_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    success_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    fail_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cycles_run: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Optional targeting (future expansion)
    #
    # NOTE: ``target_filter`` is NOT enforced by the send pipeline — every
    # active broadcast goes to all time-eligible users. The composer surfaces it
    # clearly as "not enforced yet"; do not pretend it filters.
    target_filter: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # JSON filter criteria

    @property
    def is_completed(self) -> bool:
        """Check if the broadcast has expired based on deadline"""
        return datetime.now(UTC) >= self.deadline or not self.is_active

    @property
    def is_expired(self) -> bool:
        """Check if the broadcast deadline has passed"""
        return datetime.now(UTC) >= self.deadline

    def check_and_expire(self):
        """Check if deadline has passed and mark as completed if needed"""
        if self.is_expired and self.is_active:
            self.completed_at = func.now()
            self.is_active = False

    def get_display_text(self) -> str:
        """Get a display-friendly preview of the broadcast content"""
        if self.message_text:
            return self.message_text[:50] + ("..." if len(self.message_text) > 50 else "")
        elif self.caption:
            return self.caption[:50] + ("..." if len(self.caption) > 50 else "")
        else:
            return f"[{self.message_type.upper()} MESSAGE]"

    def get_content_for_sending(self) -> dict:
        """Get the content formatted for sending"""
        if self.message_type == "text":
            return {
                "type": "text",
                "text": self.message_html or self.message_text,
                "parse_mode": "HTML" if self.has_text_formatting else None,
            }
        else:
            # Media messages (photo, video, animation, document)
            return {
                "type": self.message_type,
                "media_file_id": self.media_file_id,
                "caption": self.caption_html or self.caption,
                "parse_mode": "HTML" if self.has_caption_formatting else None,
                "metadata": self.media_metadata or {},
            }

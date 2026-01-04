from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin, TableNameMixin


class FailedWebhook(Base, CreatedAtMixin, TableNameMixin):
    """Dead letter queue for failed webhook processing."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_retry_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self):
        return f"<FailedWebhook {self.id} provider={self.provider} error_type={self.error_type}>"

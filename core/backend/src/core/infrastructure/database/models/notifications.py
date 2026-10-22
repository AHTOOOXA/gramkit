from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import func

from .base import Base, TableNameMixin


class NotificationDelivery(Base, TableNameMixin):
    """One row per attempt to send a scheduled notification to one user.

    Written only through ``NotificationsService._record_delivery``. The lifecycle caps
    (days between invites, lapse-ladder steps, dormant cadence) are computed from it.
    """

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    message_key: Mapped[str] = mapped_column(String(128), nullable=False)
    slot: Mapped[str] = mapped_column(String(16), nullable=False)  # NotificationSlot
    sent_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # None when delivered; else SendFailure.error_code ("forbidden", "bad_request", "other")
    error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (Index("ix_notification_deliveries_user_id_sent_at", "user_id", "sent_at"),)

    def __repr__(self):
        return f"<NotificationDelivery {self.id} {self.template} user={self.user_id} delivered={self.delivered}>"

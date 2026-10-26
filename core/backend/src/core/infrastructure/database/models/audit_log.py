from uuid import UUID

from sqlalchemy import BIGINT, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database.models.base import Base, CreatedAtMixin


class AuditLog(Base, CreatedAtMixin):
    """Append-only audit trail of mutating admin/owner actions.

    Actor identity is snapshotted (telegram_id / username / role) so the row stays
    meaningful even if the user is later edited or deleted. ``actor_user_id`` is a
    nullable FK with ``ON DELETE SET NULL`` (the trail survives the user). ``target_id``
    is a PLAIN string, not an FK — it must survive deletion of whatever it points at.
    """

    __tablename__ = "admin_audit_logs"
    __table_args__ = (Index("ix_admin_audit_logs_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_telegram_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    actor_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # created_at (indexed, tz-aware) comes from CreatedAtMixin.

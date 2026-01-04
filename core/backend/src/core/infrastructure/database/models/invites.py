from datetime import datetime
from secrets import token_hex
from uuid import UUID

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, TableNameMixin
from .groups import Group
from .users import User


class GroupInvite(Base, CreatedAtMixin, TableNameMixin):
    code: Mapped[str] = mapped_column(
        String(12), primary_key=True, unique=True, nullable=False, default=lambda: token_hex(6)
    )  # 6 bytes = 12 hex chars
    creator_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id", ondelete="CASCADE"))
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    creator: Mapped[User] = relationship("User", foreign_keys=[creator_id])
    group: Mapped[Group] = relationship("Group", foreign_keys=[group_id])

    def __repr__(self):
        return f"<Invite {self.code} for group {self.group_id} created by {self.creator_id}>"

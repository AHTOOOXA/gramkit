"""Minimal Balance model for template.

This model can be extended with app-specific balance/credit fields.
The core User model expects a Balance relationship, so this provides the minimum implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.infrastructure.database.models.base import Base, CreatedAtMixin, TableNameMixin, UpdatedAtMixin

if TYPE_CHECKING:
    from core.infrastructure.database.models.users import User


class Balance(Base, CreatedAtMixin, UpdatedAtMixin, TableNameMixin):
    """User balance/credits model.

    Extend this model with app-specific fields as needed:
    - Credit counts for features
    - Usage limits
    - Timestamps for reset logic
    - etc.
    """

    __table_args__ = {"extend_existing": True}

    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, autoincrement=False
    )

    user: Mapped[User] = relationship("User", back_populates="balance", uselist=False, cascade="all, delete")

    def __repr__(self):
        return f"<Balance user_id={self.user_id}>"

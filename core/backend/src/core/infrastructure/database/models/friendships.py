from uuid import UUID

from sqlalchemy import BIGINT, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, TableNameMixin
from .users import User


class Friendship(Base, CreatedAtMixin, TableNameMixin):
    """
    This class represents a mutual Friendship relationship between two users in the application.

    Attributes:
        id (Mapped[int]): The unique identifier of the friendship relationship.
        user_id1 (Mapped[int]): The user_id of the first user in the friendship.
        user_id2 (Mapped[int]): The user_id of the second user in the friendship.
        is_active (Mapped[bool]): Whether the friendship is currently active.
        user1 (Mapped[User]): Relationship to the User model for the first user.
        user2 (Mapped[User]): Relationship to the User model for the second user.

    Methods:
        __repr__(): Returns a string representation of the Friendship object.

    Inherited Attributes:
        Inherits from Base, TimestampMixin, and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base, TimestampMixin, and TableNameMixin classes, which provide additional functionality.
    """

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id1: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user_id2: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user1: Mapped[User] = relationship("User", foreign_keys=[user_id1], back_populates="friendships")
    user2: Mapped[User] = relationship("User", foreign_keys=[user_id2], back_populates="friendships")

    __table_args__ = (UniqueConstraint("user_id1", "user_id2", name="uq_friendship"),)

    def __repr__(self):
        return f"<Friendship {self.id} user_id1={self.user_id1} user_id2={self.user_id2} is_active={self.is_active}>"

from sqlalchemy import select

from ..models.invites import GroupInvite
from .base import BaseRepo


class InviteRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = GroupInvite

    async def get_by_code(self, code: str) -> GroupInvite | None:
        """
        Get an invite by its code.

        Args:
            code: Code of the invite

        Returns:
            Optional[GroupInvite]: The invite or None if not found
        """
        stmt = select(self.model_type).where(self.model_type.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

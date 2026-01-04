from sqlalchemy import select

from ..models.groups import Group, GroupMember
from ..models.users import User
from .base import BaseRepo


class GroupRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = Group


class GroupMemberRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = GroupMember

    async def get_members(self, group_id: int) -> list[User]:
        result = await self.session.execute(
            select(User).join(GroupMember, GroupMember.user_id == User.id).where(GroupMember.group_id == group_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, data: dict) -> GroupMember | None:
        stmt = select(self.model_type).where(
            (self.model_type.group_id == data["group_id"]) & (self.model_type.user_id == data["user_id"])
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

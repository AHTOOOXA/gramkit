from uuid import UUID

from ..infrastructure.database.models.groups import Group, GroupMember
from ..infrastructure.database.models.users import User
from ..services.base import BaseService


class GroupService(BaseService):
    async def create(self, creator_id: UUID, title: str | None = None, photo_url: str | None = None) -> Group:
        """Create a new group and add the creator as an admin member."""
        group = await self.repo.groups.create({"title": title, "creator_id": creator_id, "photo_url": photo_url})

        # Add creator as admin member
        await self.repo.members.create({"group_id": group.id, "user_id": creator_id, "is_admin": True})

        return group

    async def add_member(self, group_id: int, user_id: UUID, is_admin: bool = False) -> GroupMember:
        """Add a user to a group."""
        # Check if user is already a member
        existing = await self.repo.members.get_by_id({"group_id": group_id, "user_id": user_id})
        if existing:
            raise ValueError("User is already a member of this group")

        return await self.repo.members.create({"group_id": group_id, "user_id": user_id, "is_admin": is_admin})

    async def remove_member(self, group_id: int, user_id: UUID) -> None:
        """Remove a user from a group."""
        await self.repo.members.delete({"group_id": group_id, "user_id": user_id})

    async def get_by_id(self, group_id: int) -> Group | None:
        """Get a group by its ID."""
        return await self.repo.groups.get_by_id(group_id)

    async def get_members(self, group_id: int) -> list[User]:
        """Get all members of a group."""
        return await self.repo.members.get_members(group_id)

    async def is_member(self, group_id: int, user_id: UUID) -> bool:
        """Check if a user is a member of a group."""
        return await self.repo.members.get_by_id({"group_id": group_id, "user_id": user_id}) is not None

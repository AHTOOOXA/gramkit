from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from core.schemas.users import GroupSchema
from core.services.base import BaseService


class InvitesService(BaseService):
    async def create_invite(self, user_id: UUID) -> str:
        """
        Create a new invite for a user.

        Args:
            user_id: ID of the user creating the invite

        Returns:
            str: The invite code
        """
        max_retries = 3
        last_error = None

        for _ in range(max_retries):
            try:
                group = await self.services.groups.create(
                    creator_id=user_id,
                )
                invite = await self.repo.invites.create(
                    {
                        "creator_id": user_id,
                        "group_id": group.id,
                        "expires_at": datetime.now(UTC) + timedelta(days=365),  # TODO: 1 year, change later
                    }
                )
                return invite.code

            except IntegrityError as e:
                last_error = e
                # Rollback is handled in repository layer
                continue

        # If we got here, all retries failed
        raise RuntimeError(f"Failed to create invite after {max_retries} attempts") from last_error

    async def process_invite(self, invite_code: str, invitee_id: int) -> GroupSchema:
        """
        Process a group invitation and add the user to the group and as friend to all members.

        Args:
            invite_code: Code of the invite
            invitee_id: User ID of the person to add to group

        Returns:
            GroupSchema: Group info
        """
        group_invite = await self.repo.invites.get_by_code(invite_code)

        # TODO: later change this logic, for now shit fix with 1 year expiration
        if not group_invite:
            raise ValueError("Invite not found")

        if group_invite.expires_at < datetime.now(UTC):
            await self.repo.invites.delete(group_invite.code)
            raise ValueError("Invite expired")

        group = await self.services.groups.get_by_id(group_invite.group_id)

        try:
            # Add user to the group
            await self.services.groups.add_member(group_invite.group_id, invitee_id)
            await self.repo.invites.update(group_invite.code, {"used_count": group_invite.used_count + 1})
        except ValueError:  # User already in group
            return GroupSchema.model_validate(group)

        # Get all group members
        group_members = await self.services.groups.get_members(group_invite.group_id)

        # Add user as friend to all group members (and vice versa)
        for member in group_members:
            if member.id != invitee_id:  # Don't try to friend yourself
                try:
                    await self.services.users.add_friend(member.id, invitee_id)
                except IntegrityError:
                    # Friendship already exists, continue to next member
                    continue

        return GroupSchema(id=group.id, title=group.title, photo_url=group.photo_url, users=group_members)

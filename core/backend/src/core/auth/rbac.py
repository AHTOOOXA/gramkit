"""Role-based access control (RBAC) for the platform."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.infrastructure.config import settings
from core.infrastructure.database.models.enums import UserRole
from core.infrastructure.database.models.users import User
from core.infrastructure.fastapi.dependencies import get_user
from core.infrastructure.logging import get_logger
from core.schemas.users import UserSchema

logger = get_logger(__name__)


def require_role(*allowed_roles: UserRole):
    """
    Dependency that checks if user has one of the allowed roles.
    Config owner_ids override DB role at runtime.

    Args:
        *allowed_roles: Roles that are allowed to access the endpoint

    Returns:
        Dependency function that validates user role

    Raises:
        HTTPException: 403 if user doesn't have required role

    Example:
        @router.get("/admin/stats")
        async def get_stats(user: Annotated[UserSchema, Depends(require_role(UserRole.ADMIN, UserRole.OWNER))]):
            ...
    """

    async def role_checker(
        request: Request,
        user: UserSchema = Depends(get_user),
    ):
        # Config override - these telegram_ids are ALWAYS owners
        settings = request.app.state.settings
        if user.telegram_id and user.telegram_id in settings.rbac.owner_ids:
            return user  # Owner can access anything

        # Otherwise check DB role
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {[r.value for r in allowed_roles]}",
            )
        return user

    return role_checker


def require_admin():
    """Shortcut for admin or owner access.

    Returns:
        Dependency that requires admin or owner role

    Example:
        @router.get("/admin/users")
        async def list_users(user: AdminUser):
            ...
    """
    return require_role(UserRole.ADMIN, UserRole.OWNER)


def require_owner():
    """Shortcut for owner-only access.

    Returns:
        Dependency that requires owner role

    Example:
        @router.delete("/admin/users/{user_id}")
        async def delete_user(user_id: int, user: OwnerUser):
            ...
    """
    return require_role(UserRole.OWNER)


# Type aliases for cleaner annotations
AdminUser = Annotated[UserSchema, Depends(require_admin())]
OwnerUser = Annotated[UserSchema, Depends(require_owner())]


async def sync_owner_roles(session_pool: async_sessionmaker[AsyncSession]) -> None:
    """
    Sync owner roles from config to database on startup.

    - Promotes users with telegram_id in RBAC__OWNER_IDS to owner role
    - Demotes users with owner role who are NOT in RBAC__OWNER_IDS back to user role
    """
    owner_ids = settings.rbac.owner_ids
    if not owner_ids:
        logger.info("  ℹ No RBAC owner_ids configured, skipping role sync")
        return

    async with session_pool() as session:
        # Promote: users in owner_ids list who don't have owner role
        promote_result = await session.execute(
            update(User)
            .where(User.telegram_id.in_(owner_ids))
            .where(User.role != UserRole.OWNER)
            .values(role=UserRole.OWNER)
        )
        promoted = promote_result.rowcount

        # Demote: users with owner role who are NOT in owner_ids list
        demote_result = await session.execute(
            update(User)
            .where(User.role == UserRole.OWNER)
            .where(User.telegram_id.notin_(owner_ids))
            .values(role=UserRole.USER)
        )
        demoted = demote_result.rowcount

        await session.commit()

        if promoted or demoted:
            logger.info(f"  ✓ RBAC sync: {promoted} promoted to owner, {demoted} demoted to user")
        else:
            logger.info("  ✓ RBAC roles already in sync")

"""Audit-log service: record mutating admin actions + list them for the panel.

``record`` is the single write point. It snapshots the EFFECTIVE actor identity
(id / telegram_id / username / resolved role from the injected ``UserSchema``) — the
role is never client-supplied — alongside ``datetime.now(UTC)``.
"""

import builtins
from datetime import UTC, datetime
from uuid import UUID

from core.schemas.admin_common import AdminListParams, AdminListResponse
from core.schemas.audit_log import AuditLogSchema
from core.schemas.users import UserSchema
from core.services.base import BaseService


class AuditLogService(BaseService):
    async def record(
        self,
        actor: UserSchema,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        detail: dict | None = None,
    ) -> AuditLogSchema:
        """Append an audit row for a mutating admin/owner action."""
        row = await self.repo.audit_log.create(
            {
                "actor_user_id": actor.id,
                "actor_telegram_id": actor.telegram_id,
                "actor_username": actor.username or actor.tg_username,
                "actor_role": actor.role,
                "action": action,
                "target_type": target_type,
                "target_id": str(target_id) if target_id is not None else None,
                "detail": detail,
                "created_at": datetime.now(UTC),
            }
        )
        return AuditLogSchema.model_validate(row)

    # Declared BEFORE ``list`` on purpose: below that def, ``list`` in this class scope is the
    # method, so a ``list[str]`` annotation would resolve to it.
    async def list_actions(self) -> builtins.list[str]:
        """Distinct audit actions recorded so far (fills the panel's action filter)."""
        return await self.repo.audit_log.distinct_actions()

    async def list(
        self,
        params: AdminListParams,
        action: str | None = None,
        actor_user_id: UUID | None = None,
        target_user_id: str | None = None,
    ) -> AdminListResponse[AuditLogSchema]:
        """Paginated audit-log envelope for the admin panel."""
        rows, total = await self.repo.audit_log.list_filtered(
            params,
            action=action,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
        )
        items = [AuditLogSchema.model_validate(row) for row in rows]
        return AdminListResponse.build(items, total, params)

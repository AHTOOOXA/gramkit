from uuid import UUID

from sqlalchemy import select

from core.infrastructure.database.models import AuditLog
from core.infrastructure.database.repo.admin_list import admin_list_count, apply_admin_list
from core.infrastructure.database.repo.base import BaseRepo
from core.schemas.admin_common import AdminListParams


class AuditLogRepo(BaseRepo[AuditLog]):
    def __init__(self, session):
        super().__init__(session)
        self.model_type = AuditLog

    # Whitelisted sortable columns (first entry is the default sort).
    _SORTABLE = {
        "created_at": AuditLog.created_at,
        "action": AuditLog.action,
    }
    _SEARCHABLE = [AuditLog.action, AuditLog.target_type]

    async def create(self, data: dict) -> AuditLog:
        """Insert an audit row (flush, no commit — transaction managed at interface layer)."""
        obj = AuditLog(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def distinct_actions(self, limit: int = 200) -> list[str]:
        """Every distinct ``action`` recorded so far, alphabetically (for the action filter)."""
        stmt = select(AuditLog.action).distinct().order_by(AuditLog.action).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_filtered(
        self,
        params: AdminListParams,
        action: str | None = None,
        actor_user_id: UUID | None = None,
        target_user_id: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        """Filtered + paginated audit rows plus the unpaginated total.

        The optional filters narrow to a specific action, actor, or target before the
        generic search/date/sort/paginate is applied.
        """
        base = select(AuditLog)
        if action is not None:
            base = base.where(AuditLog.action == action)
        if actor_user_id is not None:
            base = base.where(AuditLog.actor_user_id == actor_user_id)
        if target_user_id is not None:
            base = base.where(
                AuditLog.target_type == "user",
                AuditLog.target_id == str(target_user_id),
            )

        list_stmt = apply_admin_list(
            base,
            params,
            sortable=self._SORTABLE,
            searchable=self._SEARCHABLE,
            date_column=AuditLog.created_at,
        )
        count_stmt = admin_list_count(
            base,
            params,
            searchable=self._SEARCHABLE,
            date_column=AuditLog.created_at,
        )

        rows = (await self.session.execute(list_stmt)).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(rows), total

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogSchema(BaseModel):
    id: int
    actor_user_id: UUID | None = None
    actor_telegram_id: int | None = None
    actor_username: str | None = None
    actor_role: str
    action: str
    target_type: str | None = None
    target_id: str | None = None
    detail: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

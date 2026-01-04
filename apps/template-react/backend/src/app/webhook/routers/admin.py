# apps/template/backend/src/app/webhook/routers/admin.py
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select

from app.infrastructure.database.repo.requests import RequestsRepo
from app.webhook.dependencies.database import get_repo
from core.auth.rbac import AdminUser, OwnerUser
from core.infrastructure.database.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


# === Schemas ===


class AdminStatsResponse(BaseModel):
    total_users: int
    users_by_role: dict[str, int]


class MyPermissionsResponse(BaseModel):
    role: str
    is_owner_in_config: bool
    permissions: list[str]


class DemoActionResponse(BaseModel):
    success: bool
    message: str
    required_role: str


# === Routes ===


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(user: AdminUser, repo: RequestsRepo = Depends(get_repo)):
    total = await repo.session.scalar(select(func.count(User.id)))

    role_counts = await repo.session.execute(select(User.role, func.count(User.id)).group_by(User.role))
    users_by_role: dict[str, int] = {str(row[0]): int(row[1]) for row in role_counts.all()}

    return AdminStatsResponse(
        total_users=total or 0,
        users_by_role=users_by_role,
    )


@router.get("/me", response_model=MyPermissionsResponse)
async def get_my_permissions(request: Request, user: AdminUser):
    settings = request.app.state.settings
    is_config_owner = user.telegram_id in settings.rbac.owner_ids

    permissions = ["view_admin_panel", "view_stats"]
    if user.role == "admin" or is_config_owner:
        permissions.append("view_aggregate_data")
    if user.role == "owner" or is_config_owner:
        permissions.extend(["change_roles", "protected_actions"])

    return MyPermissionsResponse(
        role=user.role,
        is_owner_in_config=is_config_owner,
        permissions=permissions,
    )


@router.post("/demo-action", response_model=DemoActionResponse)
async def demo_protected_action(user: OwnerUser):
    return DemoActionResponse(
        success=True,
        message="Owner access granted! This action succeeded.",
        required_role="owner",
    )

# apps/template/backend/src/app/webhook/routers/admin.py
from fastapi import APIRouter

# App-specific admin endpoints go here. The admin API that ships with the template (users, audit log,
# tasks, broadcasts, marketing links, overview, analytics) lives in core
# (`core.infrastructure.fastapi.routers`) and is mounted before this router. Both share the `/admin`
# prefix and the `admin` tag, so generated hook names stay stable.
#
# Shadowing: core is mounted first, so its `GET /admin/users/{user_id}` (UUID) catches any
# `GET /admin/users/<word>` and answers 422. App routes under `/admin/users/` need two or
# more segments after `users/` (e.g. `/admin/users/{id}/something`) or a different prefix.
# Core and app routers must also never share a method+path pair.
#
# Example (gate with `AdminUser` / `OwnerUser` from `core.auth.rbac`):
#     @router.get("/reports", response_model=ReportsSchema)
#     async def get_reports(user: AdminUser, services: RequestsService = Depends(get_services)) -> ReportsSchema:
#         ...
router = APIRouter(prefix="/admin", tags=["admin"])

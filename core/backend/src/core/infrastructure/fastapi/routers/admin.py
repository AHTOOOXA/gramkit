"""Core admin routes: RBAC meta, audit log, admin tasks, users management, payment refunds,
and (included from ``admin_broadcasts`` / ``admin_marketing_links`` / ``admin_statistics``)
broadcasts, marketing links, the Overview snapshot and the money analytics.

Mounted by each app right BEFORE its own ``routers.admin.router``; both share the
``/admin`` prefix and the ``admin`` tag, so generated client names stay stable.
App-only admin endpoints live in the app router under the same prefix.

Gating: reads, gift and revoke = AdminUser; role change, reset and refund =
OwnerUser; tasks (list: AdminUser, run: OwnerUser); overview and analytics = AdminUser. Every mutating endpoint records
an audit row (via the service).

ROUTE ORDERING IS LOAD-BEARING: inside this router every static path is declared
before the dynamic one it would otherwise collide with. Across routers, this router
is mounted first, so ``GET /admin/users/{user_id}`` catches any app route
``GET /admin/users/<word>`` (422): app sub-routes need two or more segments after
``users/`` (e.g. ``/admin/users/{user_id}/notes``) or a different prefix.

ERROR MAPPING MUST RAISE: every failure path raises ``HTTPException`` (never returns
a response). The request transaction commits only when no exception leaves the
request, and the refund path writes the REFUNDED state before calling the provider —
a returned error response would commit a refund the provider never made.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.auth.rbac import AdminUser, OwnerUser
from core.exceptions import (
    AdminTaskNotFoundException,
    PaymentNotFoundException,
    RefundNotAllowedException,
    UserNotFoundException,
)
from core.infrastructure.config import settings
from core.infrastructure.fastapi.dependencies import get_services
from core.infrastructure.fastapi.routers import admin_broadcasts, admin_marketing_links, admin_statistics
from core.schemas.admin_common import AdminListParams, AdminListResponse, AdminRbacSchema
from core.schemas.admin_tasks import AdminTaskInfo, AdminTaskRunResult, RunAdminTaskRequest
from core.schemas.admin_users import (
    AdminPaymentListItem,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserSubscription,
    ChangeRoleRequest,
    GiftSubscriptionRequest,
)
from core.schemas.audit_log import AuditLogSchema
from core.services.payments.types import ProviderRefundError
from core.services.requests import CoreRequestsService

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Meta ──────────────────────────────────────────────────────────────────────


@router.get("/meta/rbac", response_model=AdminRbacSchema)
async def get_admin_rbac(user: AdminUser) -> AdminRbacSchema:
    """Effective RBAC capabilities of the current admin (resolved server-side)."""
    return AdminRbacSchema(
        role=user.role,
        is_admin=user.is_admin,
        is_owner=user.is_owner,
        can_perform_destructive=user.is_owner,
    )


# ── Audit log ─────────────────────────────────────────────────────────────────


@router.get("/audit-log", response_model=AdminListResponse[AuditLogSchema])
async def list_audit_log(
    user: AdminUser,
    params: AdminListParams = Depends(),
    action: str | None = None,
    actor_user_id: UUID | None = None,
    target_user_id: str | None = None,
    services: CoreRequestsService = Depends(get_services),
) -> AdminListResponse[AuditLogSchema]:
    """Paginated audit trail of mutating admin/owner actions."""
    return await services.audit_log.list(
        params,
        action=action,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
    )


@router.get("/audit-log/actions", response_model=list[str])
async def list_audit_actions(
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> list[str]:
    """Distinct audit actions recorded so far (for the action filter)."""
    return await services.audit_log.list_actions()


# ── Tasks ─────────────────────────────────────────────────────────────────────
# Registered with ``@admin_task`` (core.services.admin_tasks); each app imports its task
# module once at startup. Task exceptions are NOT caught here: they reach the catch-all
# handler (500) and the request transaction rolls the task's writes back.


@router.get("/tasks", response_model=list[AdminTaskInfo])
async def list_tasks(
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> list[AdminTaskInfo]:
    """Maintenance tasks runnable from the admin panel (run in this live process)."""
    return services.admin_tasks.list_tasks()


@router.post("/tasks/{name}", response_model=AdminTaskRunResult)
async def run_task(
    name: str,
    body: RunAdminTaskRequest,
    user: OwnerUser,
    services: CoreRequestsService = Depends(get_services),
) -> AdminTaskRunResult:
    """Run a maintenance task (owner-only). Defaults to a dry run; audit-logged.

    Runs inside the webhook process reusing the request session/transaction — no
    standalone runner (no OOM), no SSH. The task's writes and the audit row commit together.
    """
    try:
        return await services.admin_tasks.run(user, name, dry_run=body.dry_run)
    except AdminTaskNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ── Users ─────────────────────────────────────────────────────────────────────
# The static /users list is declared BEFORE the dynamic /users/{user_id} (and its
# sub-paths), and reset stays DEBUG-only.


@router.get("/users", response_model=AdminListResponse[AdminUserListItem])
async def list_users(
    user: AdminUser,
    params: AdminListParams = Depends(),
    role: str | None = None,
    user_type: str | None = None,
    services: CoreRequestsService = Depends(get_services),
) -> AdminListResponse[AdminUserListItem]:
    """Searchable/filterable user table (search + role + user_type)."""
    return await services.admin.list_users(params, role=role, user_type=user_type)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user_detail(
    user_id: UUID,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> AdminUserDetail:
    """Full admin view of a user: profile + subscription + rollups."""
    detail = await services.admin.get_user_detail(user_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="User not found")
    return detail


@router.get("/users/{user_id}/payments", response_model=AdminListResponse[AdminPaymentListItem])
async def list_user_payments(
    user_id: UUID,
    user: AdminUser,
    params: AdminListParams = Depends(),
    services: CoreRequestsService = Depends(get_services),
) -> AdminListResponse[AdminPaymentListItem]:
    """A user's payment history (paginated)."""
    return await services.admin.list_payments(user_id, params)


@router.get("/users/{user_id}/subscriptions", response_model=list[AdminUserSubscription])
async def list_user_subscriptions(
    user_id: UUID,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> list[AdminUserSubscription]:
    """A user's subscription history (newest first)."""
    return await services.admin.list_subscriptions(user_id)


@router.post("/users/{user_id}/gift-subscription", response_model=AdminUserDetail)
async def gift_user_subscription(
    user_id: UUID,
    body: GiftSubscriptionRequest,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> AdminUserDetail:
    """Gift (or extend) a free subscription; records an audit row. (AdminUser)"""
    try:
        return await services.admin.gift_subscription(user, user_id, body.duration)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/users/{user_id}/revoke-subscription", response_model=AdminUserDetail)
async def revoke_user_subscription(
    user_id: UUID,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> AdminUserDetail:
    """Cancel the user's active subscription; records an audit row. (AdminUser)"""
    try:
        return await services.admin.revoke_subscription(user, user_id)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/users/{user_id}/role", response_model=AdminUserDetail)
async def change_user_role(
    user_id: UUID,
    body: ChangeRoleRequest,
    user: OwnerUser,
    services: CoreRequestsService = Depends(get_services),
) -> AdminUserDetail:
    """Change a user's RBAC role; records an audit row. (OwnerUser)"""
    try:
        return await services.admin.change_role(user, user_id, body.new_role)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/users/{user_id}/reset", status_code=204)
async def reset_user_data(
    user_id: UUID,
    user: OwnerUser,
    services: CoreRequestsService = Depends(get_services),
):
    """DEBUG-only hard delete (CASCADE) of a user; records an audit row. (OwnerUser)

    Returns 404 when DEBUG is off, so the endpoint is invisible in production. An owner can't reset
    their own account here (400): the audit row would point at the deleted actor.
    """
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Can't reset your own account")
    try:
        await services.admin.reset_user(user, user_id)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ── Payments ──────────────────────────────────────────────────────────────────


@router.post("/payments/{payment_id}/refund", response_model=AdminPaymentListItem)
async def refund_payment(
    payment_id: UUID,
    user: OwnerUser,
    services: CoreRequestsService = Depends(get_services),
) -> AdminPaymentListItem:
    """Refund a Telegram Stars payment and take back the period it paid for; audited. (OwnerUser)"""
    try:
        return await services.admin.refund_payment(user, payment_id)
    except PaymentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RefundNotAllowedException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ProviderRefundError as e:
        # Raised (never returned) so the request's transaction rolls back: nothing changed here. If
        # the provider did refund (the call timed out after it), its refund notice finishes the job.
        raise HTTPException(
            status_code=502,
            detail=f"The refund call failed: {e}. If the Stars did go back, the payment is marked "
            "refunded when Telegram confirms it.",
        ) from e


# ── Broadcasts ────────────────────────────────────────────────────────────────
# Own module (routers/admin_broadcasts.py, no prefix/tags of its own); included here so
# apps keep one core admin mount and the routes get this router's /admin prefix + tag.

router.include_router(admin_broadcasts.router)


# ── Marketing links ───────────────────────────────────────────────────────────
# Own module (routers/admin_marketing_links.py, no prefix/tags of its own), included the same way.

router.include_router(admin_marketing_links.router)


# ── Overview and analytics ────────────────────────────────────────────────────
# Own module (routers/admin_statistics.py, no prefix/tags of its own), included the same way.

router.include_router(admin_statistics.router)

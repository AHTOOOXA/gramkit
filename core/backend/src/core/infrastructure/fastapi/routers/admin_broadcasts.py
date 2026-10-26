"""Core admin routes: broadcasts (``/admin/broadcasts*``).

NOT mounted on its own: ``routers/admin.py`` includes this router, so the routes get the
``/admin`` prefix and the ``admin`` tag from there and every app keeps exactly one
``core_admin.router`` mount. Mounting this router directly as well would serve every
endpoint twice and duplicate the operations in OpenAPI. That's why it declares no prefix
and no tags.

Handler names, explicit ``operation_id``s, paths and docstrings are frozen: the
generated frontend clients and hooks are named after them.

ROUTE ORDERING IS LOAD-BEARING: every STATIC /broadcasts/... path (media, format,
preview, send-now) is declared BEFORE the dynamic /broadcasts/{broadcast_id} (and its
sub-paths), or FastAPI would match the dynamic route first and parse "media"/"format"/…
as a broadcast_id (422).

Gating: send-now (immediate all-users blast) = OwnerUser; everything else = AdminUser.
Every mutating endpoint records an audit row (``target_type='broadcast'``, via the
service). Delivery tracking is sent/success/fail/cycles only — read receipts / CTR are
impossible on Telegram. ``target_filter`` audience targeting is NOT enforced by the send
pipeline.

ERROR MAPPING MUST RAISE: the service raises ``BroadcastNotFoundException`` /
``InvalidBroadcastException``; handlers translate them by RAISING ``HTTPException``
(never by returning a response). The request transaction commits only when no exception
leaves the request, so a returned error would commit whatever the service wrote.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from core.auth.rbac import AdminUser, OwnerUser
from core.exceptions import BroadcastNotFoundException, InvalidBroadcastException
from core.infrastructure.fastapi.dependencies import get_services
from core.schemas.broadcasts import (
    BroadcastCreateRequest,
    BroadcastCreateResponse,
    BroadcastDeliveryStats,
    BroadcastDetail,
    BroadcastFormatRequest,
    BroadcastFormatResponse,
    BroadcastListResponse,
    BroadcastMediaUploadResponse,
    BroadcastPreviewRequest,
    BroadcastPreviewResponse,
    BroadcastSendNowRequest,
    BroadcastSendNowResponse,
    BroadcastUpdateRequest,
)
from core.services.requests import CoreRequestsService

router = APIRouter()


@router.get("/broadcasts", response_model=BroadcastListResponse, operation_id="list_broadcasts")
async def list_broadcasts(
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastListResponse:
    """Active + completed broadcasts, plus active-count-per-slot for the warning banner."""
    return await services.broadcasts.list_broadcasts()


@router.post("/broadcasts", response_model=BroadcastCreateResponse, operation_id="create_broadcast")
async def create_broadcast(
    body: BroadcastCreateRequest,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastCreateResponse:
    """Create broadcast(s); records an audit row. ``time_slot='both'`` creates TWO rows."""
    try:
        return await services.broadcasts.create(user, body)
    except InvalidBroadcastException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── STATIC sub-paths (declared BEFORE the dynamic /broadcasts/{id}) ──────────


@router.post("/broadcasts/media", response_model=BroadcastMediaUploadResponse, operation_id="upload_broadcast_media")
async def upload_broadcast_media(
    user: AdminUser,
    file: UploadFile = File(..., description="Media file to mint a Telegram file_id for."),
    message_type: str = Form(..., description="One of: photo, video, animation, document."),
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastMediaUploadResponse:
    """Upload media via multipart; the bot sends it to mint a reusable Telegram file_id."""
    try:
        # Telegram's size limit is checked before the body is read into memory.
        services.broadcasts.check_upload_size(message_type, file.size)
        content = await file.read()
        return await services.broadcasts.upload_media(
            user,
            message_type=message_type,
            filename=file.filename or "upload",
            content=content,
        )
    except InvalidBroadcastException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/broadcasts/format", response_model=BroadcastFormatResponse, operation_id="format_broadcast")
async def format_broadcast(
    body: BroadcastFormatRequest,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastFormatResponse:
    """Convert text + Telegram entities to the HTML the send pipeline ships."""
    html = services.broadcasts.format_text(body.text, body.entities)
    return BroadcastFormatResponse(html=html)


@router.post("/broadcasts/preview", response_model=BroadcastPreviewResponse, operation_id="preview_broadcast")
async def preview_broadcast(
    body: BroadcastPreviewRequest,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastPreviewResponse:
    """Send the composed message to the acting admin's OWN Telegram chat (no DB write)."""
    try:
        sent = await services.broadcasts.preview(user, body)
    except InvalidBroadcastException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return BroadcastPreviewResponse(sent=sent)


@router.post("/broadcasts/send-now", response_model=BroadcastSendNowResponse, operation_id="send_broadcast_now")
async def send_broadcast_now(
    body: BroadcastSendNowRequest,
    user: OwnerUser,
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastSendNowResponse:
    """Trigger an immediate all-users blast (OwnerUser); reuses the arq job; records audit."""
    try:
        queued = await services.broadcasts.send_now(user, body)
    except BroadcastNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidBroadcastException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return BroadcastSendNowResponse(queued=queued)


# ── DYNAMIC /broadcasts/{broadcast_id} routes (declared LAST) ────────────────


@router.get(
    "/broadcasts/{broadcast_id}/stats", response_model=BroadcastDeliveryStats, operation_id="get_broadcast_stats"
)
async def get_broadcast_stats(
    broadcast_id: int,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastDeliveryStats:
    """Delivery counters (sent / success / fail / cycles + last_sent_at)."""
    try:
        return await services.broadcasts.get_stats(broadcast_id)
    except BroadcastNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/broadcasts/{broadcast_id}", response_model=BroadcastDetail, operation_id="get_broadcast")
async def get_broadcast(
    broadcast_id: int,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastDetail:
    """Full broadcast for the detail view / edit form (404 if missing)."""
    detail = await services.broadcasts.get_broadcast(broadcast_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return detail


@router.patch("/broadcasts/{broadcast_id}", response_model=BroadcastDetail, operation_id="edit_broadcast")
async def edit_broadcast(
    broadcast_id: int,
    body: BroadcastUpdateRequest,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastDetail:
    """Edit a single broadcast row; records an audit row. (A 'both' pair is two rows.)"""
    try:
        return await services.broadcasts.edit(user, broadcast_id, body)
    except BroadcastNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidBroadcastException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/broadcasts/{broadcast_id}/cancel", response_model=BroadcastDetail, operation_id="cancel_broadcast")
async def cancel_broadcast(
    broadcast_id: int,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> BroadcastDetail:
    """Soft-cancel a broadcast (is_active=False); records an audit row."""
    try:
        return await services.broadcasts.cancel(user, broadcast_id)
    except BroadcastNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

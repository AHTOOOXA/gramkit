"""Core admin routes: marketing links (``/admin/marketing-links*``).

Marketing links: one acquisition code per external placement, its Mini App / bot links and
what it brought (users, activated, payers, revenue). Admin-gated; mutations are audit-logged
(``target_type='marketing_link'``, via the service).

NOT mounted on its own: ``routers/admin.py`` includes this router, so the routes get the
``/admin`` prefix and the ``admin`` tag from there and every app keeps exactly one
``core_admin.router`` mount. Mounting this router directly as well would serve every
endpoint twice and duplicate the operations in OpenAPI. That's why it declares no prefix
and no tags.

Handler names, explicit ``operation_id``s, paths and docstrings are frozen: the generated
frontend clients and hooks are named after them.

ERROR MAPPING MUST RAISE: the service raises ``MarketingCodeNotAllowedException`` /
``MarketingLinkNotFoundException``; handlers translate them by RAISING ``HTTPException``
(never by returning a response). The request transaction commits only when no exception
leaves the request, so a returned error would commit whatever the service wrote.
"""

from fastapi import APIRouter, Depends, HTTPException

from core.auth.rbac import AdminUser
from core.exceptions import MarketingCodeNotAllowedException, MarketingLinkNotFoundException
from core.infrastructure.fastapi.dependencies import get_services
from core.schemas.marketing_links import (
    MarketingLinkCreateRequest,
    MarketingLinkItem,
    MarketingLinkListResponse,
    MarketingLinkUpdateRequest,
)
from core.services.requests import CoreRequestsService

router = APIRouter()


@router.get("/marketing-links", response_model=MarketingLinkListResponse, operation_id="list_marketing_links")
async def list_marketing_links(
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> MarketingLinkListResponse:
    """Registered codes first (newest first), then codes seen in users but never registered."""
    return await services.marketing_links.list_links()


@router.post("/marketing-links", response_model=MarketingLinkItem, operation_id="create_marketing_link")
async def create_marketing_link(
    body: MarketingLinkCreateRequest,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> MarketingLinkItem:
    try:
        return await services.marketing_links.create(user, body)
    except MarketingCodeNotAllowedException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/marketing-links/{link_id}", response_model=MarketingLinkItem, operation_id="update_marketing_link")
async def update_marketing_link(
    link_id: int,
    body: MarketingLinkUpdateRequest,
    user: AdminUser,
    services: CoreRequestsService = Depends(get_services),
) -> MarketingLinkItem:
    try:
        return await services.marketing_links.update(user, link_id, body)
    except MarketingLinkNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

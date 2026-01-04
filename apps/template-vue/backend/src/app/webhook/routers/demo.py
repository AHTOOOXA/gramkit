"""Demo endpoints for TanStack Query showcase.

These endpoints demonstrate data fetching patterns:
- Loading states (artificial delays)
- Error handling (controlled failures)
- Cache behavior (stateful counter)
- Optimistic updates (increment with rollback)
- Background jobs (delayed notifications)
- Infinite scroll (paginated data)
- Polling (live server time)
- Parallel queries (multiple data sources)
- Prefetching (item details)
"""

import asyncio
import random
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.requests import RequestsService
from app.webhook.dependencies.service import get_services
from core.infrastructure.fastapi.dependencies import get_user
from core.schemas.users import UserSchema

router = APIRouter(prefix="/demo", tags=["demo"])

# In-memory counters per ID for demo (resets on restart)
_counters: dict[str, int] = {}


# Mock data for demos
class MockItem:
    __slots__ = ("id", "title", "description")

    def __init__(self, id: int, title: str, description: str):
        self.id = id
        self.title = title
        self.description = description


_MOCK_ITEMS = [MockItem(id=i, title=f"Item {i}", description=f"Description for item {i}") for i in range(1, 101)]


class SlowResponse(BaseModel):
    message: str
    timestamp: str
    delay_ms: int


class UnreliableResponse(BaseModel):
    message: str
    timestamp: str
    attempt_succeeded: bool


class CounterResponse(BaseModel):
    value: int
    counter_id: str
    timestamp: str


@router.get("/slow", response_model=SlowResponse)
async def slow_endpoint(delay_ms: int = Query(default=2000, ge=100, le=10000)):
    """
    Endpoint with artificial delay for loading state demo.

    Args:
        delay_ms: Delay in milliseconds (100-10000, default 2000)
    """
    await asyncio.sleep(delay_ms / 1000)
    return SlowResponse(
        message=f"Loaded after {delay_ms}ms",
        timestamp=datetime.now(UTC).isoformat(),
        delay_ms=delay_ms,
    )


@router.get("/unreliable", response_model=UnreliableResponse)
async def unreliable_endpoint(fail_rate: float = Query(default=0.5, ge=0, le=1)):
    """
    Endpoint that randomly fails for error handling demo.

    Args:
        fail_rate: Probability of failure (0-1, default 0.5)
    """
    if random.random() < fail_rate:
        raise HTTPException(status_code=500, detail=f"Random failure (fail_rate={fail_rate})")
    return UnreliableResponse(
        message="Request succeeded!",
        timestamp=datetime.now(UTC).isoformat(),
        attempt_succeeded=True,
    )


@router.get("/counter", response_model=CounterResponse)
async def get_counter(counter_id: str = Query(default="default")):
    """Get current counter value for cache demo.

    Args:
        counter_id: Unique counter ID (default: "default"). Use different IDs
                   to avoid conflicts between users/sessions.
    """
    value = _counters.get(counter_id, 0)
    return CounterResponse(
        value=value,
        counter_id=counter_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.post("/counter/increment", response_model=CounterResponse)
async def increment_counter(
    counter_id: str = Query(default="default"),
    amount: int = Query(default=1, ge=1, le=100),
    should_fail: bool = Query(default=False),
):
    """
    Increment counter for optimistic update demo.

    Args:
        counter_id: Unique counter ID (default: "default")
        amount: Amount to increment (1-100, default 1)
        should_fail: If true, fails after delay (for rollback demo)
    """
    if should_fail:
        # Simulate server processing time before failure
        await asyncio.sleep(0.5)
        raise HTTPException(status_code=500, detail="Intentional failure for rollback demo")

    current = _counters.get(counter_id, 0)
    _counters[counter_id] = current + amount
    return CounterResponse(
        value=_counters[counter_id],
        counter_id=counter_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.post("/counter/reset", response_model=CounterResponse)
async def reset_counter(counter_id: str = Query(default="default")):
    """Reset counter to 0.

    Args:
        counter_id: Unique counter ID (default: "default")
    """
    _counters[counter_id] = 0
    return CounterResponse(
        value=0,
        counter_id=counter_id,
        timestamp=datetime.now(UTC).isoformat(),
    )


# =============================================================================
# Notification Demo (Worker/Background Jobs)
# =============================================================================


class NotifyRequest(BaseModel):
    delay_seconds: int = 5


class NotifyResponse(BaseModel):
    message: str
    delay_seconds: int
    scheduled_at: str


@router.post("/notify", response_model=NotifyResponse)
async def schedule_notification(
    request: NotifyRequest,
    services: RequestsService = Depends(get_services),
    user: UserSchema = Depends(get_user),
):
    """
    Schedule a delayed Telegram notification for demo.

    Requires Telegram authentication (guest users not supported).

    Args:
        delay_seconds: Delay before sending (1-60 seconds)
    """
    # Require Telegram authentication (guest users have no telegram_id)
    if not user.telegram_id:
        raise HTTPException(
            status_code=401,
            detail="Telegram authentication required for notifications",
        )

    delay = max(1, min(60, request.delay_seconds))  # Clamp 1-60

    # Schedule worker task with delay
    await services.worker.enqueue_job(
        "send_delayed_notification",
        user_id=user.telegram_id,
        delay_seconds=delay,
        _defer_by=delay,  # ARQ defer parameter
    )

    return NotifyResponse(
        message=f"Notification scheduled! Check Telegram in {delay} seconds.",
        delay_seconds=delay,
        scheduled_at=datetime.now(UTC).isoformat(),
    )


# =============================================================================
# Infinite Scroll Demo (Paginated Data)
# =============================================================================


class PaginatedItem(BaseModel):
    id: int
    title: str
    description: str


class PaginatedResponse(BaseModel):
    items: list[PaginatedItem]
    next_cursor: int | None
    has_more: bool
    total: int


@router.get("/items", response_model=PaginatedResponse)
async def get_paginated_items(
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=50),
    delay_ms: int = Query(default=500, ge=0, le=3000),
):
    """
    Paginated items endpoint for infinite scroll demo.

    Args:
        cursor: Starting index (default 0)
        limit: Items per page (1-50, default 10)
        delay_ms: Artificial delay in milliseconds (0-3000, default 500)
    """
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    start = cursor
    end = min(cursor + limit, len(_MOCK_ITEMS))
    items = _MOCK_ITEMS[start:end]

    next_cursor = end if end < len(_MOCK_ITEMS) else None
    has_more = next_cursor is not None

    return PaginatedResponse(
        items=[PaginatedItem(id=item.id, title=item.title, description=item.description) for item in items],
        next_cursor=next_cursor,
        has_more=has_more,
        total=len(_MOCK_ITEMS),
    )


# =============================================================================
# Item Detail Demo (Prefetching)
# =============================================================================


class ItemDetailResponse(BaseModel):
    id: int
    title: str
    description: str
    details: str
    fetched_at: str


@router.get("/items/{item_id}", response_model=ItemDetailResponse)
async def get_item_detail(
    item_id: int,
    delay_ms: int = Query(default=300, ge=0, le=3000),
):
    """
    Item detail endpoint for prefetch demo.

    Args:
        item_id: Item ID (1-100)
        delay_ms: Artificial delay in milliseconds (0-3000, default 300)
    """
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    if item_id < 1 or item_id > 100:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    item = _MOCK_ITEMS[item_id - 1]
    return ItemDetailResponse(
        id=item.id,
        title=item.title,
        description=item.description,
        details=f"Extended details for {item.title}. This could include more info, metadata, etc.",
        fetched_at=datetime.now(UTC).isoformat(),
    )


# =============================================================================
# Polling Demo (Server Time)
# =============================================================================


class ServerTimeResponse(BaseModel):
    timestamp: str
    unix_ms: int
    formatted: str


@router.get("/time", response_model=ServerTimeResponse)
async def get_server_time():
    """
    Server time endpoint for polling demo.
    Returns current server timestamp.
    """
    now = datetime.now(UTC)
    return ServerTimeResponse(
        timestamp=now.isoformat(),
        unix_ms=int(now.timestamp() * 1000),
        formatted=now.strftime("%H:%M:%S"),
    )


# =============================================================================
# AI Streaming Demo (Server-Sent Events)
# =============================================================================

# Mock streaming text (visible character-by-character to user)
_MOCK_STREAM_TEXT = """
Streaming is the art of sending data incrementally,
character by character, to create a real-time experience.

This endpoint demonstrates:
- Server-Sent Events (SSE) protocol
- Non-blocking async generators
- Proper HTTP headers for streaming
- [DONE] sentinel to signal completion

The frontend parses `data: ` prefixed lines from the response.
"""


@router.get("/stream")
async def stream_demo():
    """
    SSE streaming endpoint for AI demo.

    Returns Server-Sent Events (SSE) with character-by-character text.
    Frontend parses lines starting with 'data: ' and stops at '[DONE]'.

    Example client:
    ```typescript
    const res = await apiFetch('/demo/stream');
    const reader = res.body?.getReader();
    const decoder = new TextDecoder();

    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      for (const line of chunk.split('\\n')) {
        if (line.startsWith('data: ') && !line.includes('[DONE]')) {
          console.log(line.slice(6)); // Extract content after "data: "
        }
      }
    }
    ```
    """

    async def generate():
        # Yield each character with delay for demo
        for char in _MOCK_STREAM_TEXT.strip():
            yield f"data: {char}\n\n"
            await asyncio.sleep(0.03)  # 30ms per character (~1000 chars/min)

        # Signal completion
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Transfer-Encoding": "chunked",
        },
    )


# =============================================================================
# Parallel Queries Demo (Multiple Data Sources)
# =============================================================================


class WeatherResponse(BaseModel):
    city: str
    temperature: int
    condition: str
    fetched_at: str


class StockResponse(BaseModel):
    symbol: str
    price: float
    change: float
    fetched_at: str


class NewsResponse(BaseModel):
    headline: str
    source: str
    fetched_at: str


@router.get("/weather", response_model=WeatherResponse)
async def get_weather(
    city: str = Query(default="Moscow"),
    delay_ms: int = Query(default=800, ge=0, le=3000),
):
    """Mock weather data for parallel queries demo."""
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    conditions = ["Sunny", "Cloudy", "Rainy", "Snowy", "Windy"]
    return WeatherResponse(
        city=city,
        temperature=random.randint(-10, 35),
        condition=random.choice(conditions),
        fetched_at=datetime.now(UTC).isoformat(),
    )


@router.get("/stock", response_model=StockResponse)
async def get_stock(
    symbol: str = Query(default="DEMO"),
    delay_ms: int = Query(default=600, ge=0, le=3000),
):
    """Mock stock data for parallel queries demo."""
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    return StockResponse(
        symbol=symbol,
        price=round(100 + random.uniform(-20, 20), 2),
        change=round(random.uniform(-5, 5), 2),
        fetched_at=datetime.now(UTC).isoformat(),
    )


@router.get("/news", response_model=NewsResponse)
async def get_news(delay_ms: int = Query(default=700, ge=0, le=3000)):
    """Mock news data for parallel queries demo."""
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    headlines = [
        "Tech stocks surge on AI optimism",
        "New climate report released",
        "Central bank holds rates steady",
        "Startup raises record funding",
        "Market volatility expected",
    ]
    sources = ["Reuters", "Bloomberg", "AP", "BBC", "TechCrunch"]

    return NewsResponse(
        headline=random.choice(headlines),
        source=random.choice(sources),
        fetched_at=datetime.now(UTC).isoformat(),
    )


# =============================================================================
# Error Handling Demo (HTTP Status Codes)
# =============================================================================


class ErrorResponse(BaseModel):
    status_code: int
    detail: str
    triggered_at: str


@router.get("/error/{status_code}")
async def trigger_error(
    status_code: int,
    delay_ms: int = Query(default=0, ge=0, le=3000),
):
    """
    Trigger specific HTTP error for error handling demo.

    Args:
        status_code: HTTP status code to return (400-599)
        delay_ms: Optional delay before returning error
    """
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    messages = {
        400: "Bad request - invalid parameters provided",
        401: "Unauthorized - authentication required",
        403: "Forbidden - you don't have permission",
        404: "Not found - resource doesn't exist",
        409: "Conflict - resource already exists",
        422: "Validation error - check your input",
        429: "Rate limited - too many requests",
        500: "Internal server error - something went wrong",
        502: "Bad gateway - upstream server error",
        503: "Service unavailable - try again later",
        504: "Gateway timeout - upstream server timeout",
    }

    if status_code < 400 or status_code > 599:
        raise HTTPException(status_code=400, detail="Status code must be 400-599")

    raise HTTPException(
        status_code=status_code,
        detail=messages.get(status_code, f"Error with status {status_code}"),
    )


# =============================================================================
# RBAC Demo Endpoints
# =============================================================================


class RbacMeResponse(BaseModel):
    """Your current role and permissions."""

    role: str
    permissions: list[str]


class SetRoleRequest(BaseModel):
    """Request to change your role (demo only)."""

    role: str  # "user", "admin", "owner"


class SetRoleResponse(BaseModel):
    """Response after changing role."""

    success: bool
    old_role: str
    new_role: str
    message: str


class ProtectedActionResponse(BaseModel):
    """Response from protected action."""

    success: bool
    message: str
    your_role: str


# Role -> permissions mapping for demo
ROLE_PERMISSIONS = {
    "user": ["read_own_data", "update_own_profile"],
    "admin": ["read_own_data", "update_own_profile", "read_all_users", "view_stats"],
    "owner": [
        "read_own_data",
        "update_own_profile",
        "read_all_users",
        "view_stats",
        "protected_actions",
        "manage_roles",
    ],
}


@router.get("/rbac/me", response_model=RbacMeResponse)
async def get_rbac_me(user: UserSchema = Depends(get_user)):
    """Get your current role and permissions for RBAC demo."""
    role = user.role or "user"
    permissions = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["user"])
    return RbacMeResponse(role=role, permissions=permissions)


@router.post("/rbac/set-role", response_model=SetRoleResponse)
async def set_demo_role(
    request: SetRoleRequest,
    user: UserSchema = Depends(get_user),
    services: RequestsService = Depends(get_services),
):
    """
    Change your role for demo purposes (debug mode only).

    This allows testing different permission levels without
    needing actual admin access.
    """
    from core.infrastructure.config import settings

    if not settings.debug:
        raise HTTPException(status_code=403, detail="Role switching only available in debug mode")

    valid_roles = ["user", "admin", "owner"]
    if request.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    old_role = user.role or "user"

    # Update role in database
    await services.repo.users.update_user(user.id, {"role": request.role})

    return SetRoleResponse(
        success=True,
        old_role=old_role,
        new_role=request.role,
        message=f"Role changed from {old_role} to {request.role}. Refresh to see changes.",
    )


@router.post("/rbac/protected-action", response_model=ProtectedActionResponse)
async def demo_protected_action(user: UserSchema = Depends(get_user)):
    """
    Demo endpoint that requires owner role.

    Use this to test permission checks - only owners can execute this action.
    """
    role = user.role or "user"
    permissions = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["user"])

    if "protected_actions" not in permissions:
        raise HTTPException(
            status_code=403,
            detail=f"This action requires owner role. Your role: {role}",
        )

    return ProtectedActionResponse(
        success=True,
        message="Protected action executed successfully!",
        your_role=role,
    )

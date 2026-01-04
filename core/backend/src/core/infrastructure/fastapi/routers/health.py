"""Health check endpoints for monitoring and uptime checks."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Liveness probe endpoint.

    Always returns 200 if the process is alive. This endpoint should be used
    for Kubernetes liveness probes to detect if the application is responsive.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
async def readiness_check(request: Request):
    """
    Readiness probe endpoint for load balancers and Kubernetes.

    Returns 200 during normal operation and 503 during shutdown.
    During shutdown, this signals to load balancers and K8s to stop
    sending new traffic to this instance.
    """
    # Import RequestTracker here to avoid circular imports
    from core.infrastructure.fastapi.middleware.tracker import RequestTracker

    tracker: RequestTracker = request.app.state.request_tracker

    if tracker.is_shutting_down:
        return Response(
            status_code=503,
            content='{"status": "shutting_down"}',
            media_type="application/json",
        )

    return {
        "status": "ready",
        "active_requests": tracker.active_count,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint to verify API is responding.
    Returns immediately with pong response.
    """
    return {"pong": True}

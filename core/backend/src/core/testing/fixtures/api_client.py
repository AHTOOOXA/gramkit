"""API client utilities for testing FastAPI endpoints.

Provides utilities for AsyncClient testing with session management.
"""

import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request, Response


class MockSessionManager:
    """Mock session manager for testing (in-memory sessions)."""

    def __init__(self):
        self.sessions = {}  # In-memory session storage

    async def create_session(self, user_id: UUID, user_type: str, metadata: dict | None = None) -> str:
        """Create session in memory."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "user_id": user_id,
            "user_type": user_type,
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        }
        return session_id

    async def validate_session(self, session_id: str) -> dict | None:
        """Validate session from memory."""
        return self.sessions.get(session_id)

    async def destroy_session(self, session_id: str) -> bool:
        """Destroy session from memory."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def set_session_cookie(self, response: Response, session_id: str) -> None:
        """Set session cookie in response."""
        response.set_cookie(key="session_id", value=session_id)

    def clear_session_cookie(self, response: Response) -> None:
        """Clear session cookie from response."""
        response.delete_cookie(key="session_id")

    def get_session_from_request(self, request: Request) -> str | None:
        """Extract session ID from request cookies."""
        return request.cookies.get("session_id")

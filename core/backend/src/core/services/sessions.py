"""Session management service.

This service provides a consistent interface for session management across
the application (bot handlers, webhooks, etc.). It wraps Redis session
storage with unified configuration from settings.

Session lifecycle:
- CREATE: Generate UUID session ID, store data in Redis with TTL
- VALIDATE: Retrieve session, update last_accessed, extend TTL
- DESTROY: Remove session from Redis
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from core.infrastructure.config import settings
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RedisProtocol(Protocol):
    """Redis client protocol for type checking."""

    async def set(self, key: str, value: str, ex: int) -> None: ...
    async def get(self, key: str) -> bytes | None: ...
    async def delete(self, key: str) -> int: ...


class SessionService:
    """Service for managing user sessions in Redis.

    This service provides a consistent session management interface that
    can be used by both bot handlers and webhooks. Configuration is
    read from unified settings.session.

    Example usage:
        ```python
        # In service aggregator
        @cached_property
        def sessions(self) -> SessionService:
            return SessionService(
                redis=self.redis,
                key_prefix="template-react:session:",
                expire_days=30,
            )

        # In bot handler
        session_id = await services.sessions.create_session(
            user_id=user.id,
            user_type="REGISTERED",
            metadata={"auth_method": "telegram_web", "telegram_id": 12345}
        )

        # In webhook
        session_data = await services.sessions.validate_session(session_id)
        ```
    """

    def __init__(self, redis: RedisProtocol):
        """Initialize session service.

        Uses settings.session for configuration.

        Args:
            redis: Redis client instance (must support async set/get/delete)
        """
        self.redis = redis

    async def create_session(
        self,
        user_id: UUID,
        user_type: str,
        metadata: dict | None = None,
    ) -> str:
        """Create new session in Redis.

        Generates a UUID session ID and stores session data in Redis with TTL.

        Args:
            user_id: Internal user ID from database
            user_type: User type (e.g., 'REGISTERED', 'GUEST')
            metadata: Optional metadata to store with session (e.g., auth_method, telegram_id)

        Returns:
            Session ID (UUID string)
        """
        session_id = str(uuid.uuid4())
        session_key = f"{settings.session.key_prefix}{session_id}"

        session_data = {
            "user_id": str(user_id),
            "user_type": user_type,
            "created_at": datetime.now(UTC).isoformat(),
            "last_accessed": datetime.now(UTC).isoformat(),
        }

        if metadata:
            session_data.update(metadata)

        expire_seconds = settings.session.expire_days * 24 * 60 * 60
        await self.redis.set(session_key, json.dumps(session_data), ex=expire_seconds)

        logger.info(f"Created session {session_id} for user {user_id} with prefix {settings.session.key_prefix}")
        return session_id

    async def validate_session(self, session_id: str) -> dict | None:
        """Validate session and return session data.

        Retrieves session data from Redis, updates last_accessed time,
        and extends TTL.

        Args:
            session_id: Session identifier

        Returns:
            Session data if valid, None if invalid/expired
        """
        if not session_id:
            return None

        session_key = f"{settings.session.key_prefix}{session_id}"

        try:
            session_data_raw = await self.redis.get(session_key)
            if not session_data_raw:
                return None

            # Handle bytes from Redis
            if isinstance(session_data_raw, bytes):
                session_data_raw = session_data_raw.decode("utf-8")

            session_data = json.loads(session_data_raw)

            # Update last accessed time and extend TTL
            session_data["last_accessed"] = datetime.now(UTC).isoformat()
            expire_seconds = settings.session.expire_days * 24 * 60 * 60

            await self.redis.set(session_key, json.dumps(session_data), ex=expire_seconds)

            return session_data

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid session data for {session_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating session {session_id}: {e}")
            return None

    async def destroy_session(self, session_id: str) -> bool:
        """Destroy session by removing from Redis.

        Args:
            session_id: Session identifier

        Returns:
            True if session was destroyed, False if not found
        """
        if not session_id:
            return False

        session_key = f"{settings.session.key_prefix}{session_id}"

        try:
            result = await self.redis.delete(session_key)
            logger.info(f"Destroyed session {session_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error destroying session {session_id}: {e}")
            return False

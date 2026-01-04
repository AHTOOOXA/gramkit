"""In-memory Redis mock for testing."""

from datetime import UTC, datetime, timedelta

import pytest


class InMemoryRedis:
    """
    In-memory Redis replacement for testing.

    Supports the operations we actually use:
    - get/set with TTL
    - delete
    - exists
    - incr with expire
    """

    def __init__(self):
        self._data: dict[str, tuple[bytes, datetime | None]] = {}

    async def get(self, key: str) -> bytes | None:
        """Get value, respecting TTL."""
        if key not in self._data:
            return None
        value, expires_at = self._data[key]
        if expires_at and datetime.now(UTC) > expires_at:
            del self._data[key]
            return None
        return value

    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> bool:
        """Set value with optional TTL in seconds."""
        if isinstance(value, str):
            value = value.encode()
        expires_at = datetime.now(UTC) + timedelta(seconds=ex) if ex else None
        self._data[key] = (value, expires_at)
        return True

    async def delete(self, key: str) -> int:
        """Delete key, return 1 if existed, 0 if not."""
        if key in self._data:
            del self._data[key]
            return 1
        return 0

    async def exists(self, key: str) -> int:
        """Check if key exists (respecting TTL)."""
        result = await self.get(key)
        return 1 if result is not None else 0

    async def incr(self, key: str) -> int:
        """Increment counter, create with value 1 if not exists."""
        current = await self.get(key)
        if current is None:
            value = 1
        else:
            value = int(current.decode()) + 1
        await self.set(key, str(value))
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        """Set TTL on existing key."""
        if key not in self._data:
            return False
        value, _ = self._data[key]
        expires_at = datetime.now(UTC) + timedelta(seconds=seconds)
        self._data[key] = (value, expires_at)
        return True

    def clear(self):
        """Clear all data (for test isolation)."""
        self._data.clear()


@pytest.fixture
def mock_redis():
    """In-memory Redis for testing."""
    redis = InMemoryRedis()
    yield redis
    redis.clear()

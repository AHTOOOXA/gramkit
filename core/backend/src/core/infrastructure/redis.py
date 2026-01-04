from redis.asyncio import Redis

from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    _client: Redis | None = None
    _config = None

    def __init__(self, config):
        if RedisClient._config is None:
            RedisClient._config = config

    @classmethod
    async def get_client(cls) -> Redis:
        if cls._client is None:
            try:
                cls._client = Redis.from_url(cls._config.url)
                await cls._client.ping()
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            try:
                await cls._client.close()
                cls._client = None
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

    async def get(self, key: str) -> bytes | None:
        client = await self.get_client()
        return await client.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        client = await self.get_client()
        return await client.set(key, value, ex=ex)

    async def delete(self, key: str) -> bool:
        client = await self.get_client()
        return await client.delete(key)

    async def exists(self, key: str) -> int:
        """Check if a key exists in Redis."""
        client = await self.get_client()
        return await client.exists(key)

    async def incr(self, key: str) -> int:
        """Increment a key's value by 1."""
        client = await self.get_client()
        return await client.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set a TTL on a key in seconds."""
        client = await self.get_client()
        return await client.expire(key, seconds)

    async def flushdb(self) -> bool:
        """Delete all keys in the current database."""
        client = await self.get_client()
        return await client.flushdb()

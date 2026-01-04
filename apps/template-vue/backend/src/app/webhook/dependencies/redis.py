from core.infrastructure.config import settings
from core.infrastructure.redis import RedisClient

redis_client = RedisClient(settings.redis)


async def get_redis_client():
    yield redis_client

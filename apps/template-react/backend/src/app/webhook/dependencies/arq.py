from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from core.infrastructure.config import settings


async def get_arq_pool():
    arq: ArqRedis = await create_pool(
        RedisSettings(
            host=settings.redis.host,
            port=settings.redis.port,
            password=settings.redis.password,
        )
    )
    try:
        yield arq
    finally:
        await arq.close()

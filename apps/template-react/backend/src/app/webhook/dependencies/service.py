from aiogram import Bot
from arq import ArqRedis
from fastapi import Depends

from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService
from app.webhook.dependencies.arq import get_arq_pool
from app.webhook.dependencies.bot import get_bot
from app.webhook.dependencies.database import get_repo
from app.webhook.dependencies.rabbit import get_rabbit_producer
from app.webhook.dependencies.redis import get_redis_client
from core.infrastructure.rabbit.producer import RabbitMQProducer
from core.infrastructure.redis import RedisClient

# Both return (no ``yield``): FastAPI refuses a ``yield`` dependency (request scope) that depends
# on a function-scoped one. See ``get_repo`` for what the two scopes mean.


async def get_services(
    repo: RequestsRepo = Depends(get_repo, scope="function"),
    producer: RabbitMQProducer = Depends(get_rabbit_producer),
    bot: Bot = Depends(get_bot),
    redis: RedisClient = Depends(get_redis_client),
    arq: ArqRedis = Depends(get_arq_pool),
) -> RequestsService:
    """The services for a request. The transaction commits before the response is sent."""
    return RequestsService(repo, producer, bot, redis, arq)


async def get_services_streaming(
    repo: RequestsRepo = Depends(get_repo, scope="request"),
    producer: RabbitMQProducer = Depends(get_rabbit_producer),
    bot: Bot = Depends(get_bot),
    redis: RedisClient = Depends(get_redis_client),
    arq: ArqRedis = Depends(get_arq_pool),
) -> RequestsService:
    """The services for a streaming endpoint: the session stays open while the body streams and
    commits after it.

    Only for endpoints that return a ``StreamingResponse`` whose generator uses the services
    after the endpoint returned. Pair it with ``get_user_streaming`` (``app.webhook.auth``):
    ``get_user`` goes through ``get_services`` and would open a second session.
    """
    return RequestsService(repo, producer, bot, redis, arq)

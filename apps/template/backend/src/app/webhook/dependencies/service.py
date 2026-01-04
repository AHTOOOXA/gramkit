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


async def get_services(
    repo: RequestsRepo = Depends(get_repo),
    producer: RabbitMQProducer = Depends(get_rabbit_producer),
    bot: Bot = Depends(get_bot),
    redis: RedisClient = Depends(get_redis_client),
    arq: ArqRedis = Depends(get_arq_pool),
):
    yield RequestsService(repo, producer, bot, redis, arq)

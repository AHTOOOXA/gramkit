from core.infrastructure.config import settings
from core.infrastructure.rabbit.producer import RabbitMQProducer


async def get_rabbit_producer():
    return RabbitMQProducer(settings.rabbit)

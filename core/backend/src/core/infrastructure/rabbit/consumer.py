import asyncio
from collections.abc import Callable
from typing import Any

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from aiogram import Bot

from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RabbitMQConsumer:
    def __init__(self, config):
        self.config = config
        self.connection = None
        self.channel = None
        self.queue = None
        self.bot = None

    async def connect(self):
        logger.info(f"Connecting to RabbitMQ at {self.config.url}")
        self.connection = await aio_pika.connect_robust(self.config.url)
        self.channel = await self.connection.channel()
        self.queue = await self.channel.declare_queue(self.config.queue_name, durable=True)
        logger.info(f"Successfully connected to RabbitMQ and declared queue {self.config.queue_name}")

    async def consume(self, callback: Callable[[Bot, dict], Any]):
        async def process_message(message: AbstractIncomingMessage):
            async with message.process():
                body = message.body.decode()
                logger.debug(f"Received message: {body}")
                try:
                    data = eval(body)  # Be cautious with eval, consider using json.loads instead
                    await callback(self.bot, data)
                    logger.info(f"Successfully processed message: {data}")
                except Exception as e:
                    logger.error(f"Error processing message {body}: {e}")

        logger.info(f"Starting to consume messages from queue {self.config.queue_name}")
        await self.queue.consume(process_message)
        await asyncio.Future()  # This will keep the consumer running

    async def start_consuming(self, callback: Callable[[Bot, dict], Any], bot: Bot):
        self.bot = bot
        await self.connect()
        await self.consume(callback)

    async def close(self):
        if self.connection:
            logger.info("Closing RabbitMQ connection")
            await self.connection.close()
            logger.info("RabbitMQ connection closed successfully")

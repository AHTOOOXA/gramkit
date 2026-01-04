import json
from typing import Any

import aio_pika

from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RabbitMQProducer:
    def __init__(self, config):
        self.config = config
        self.connection = None
        self.channel = None

    async def connect(self):
        logger.info(f"Connecting to RabbitMQ at {self.config.url}")
        try:
            self.connection = await aio_pika.connect_robust(self.config.url)
            self.channel = await self.connection.channel()
            logger.info("Successfully connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def publish(self, message: dict[str, Any]):
        if not self.connection or self.connection.is_closed:
            logger.info("Connection closed or not established. Reconnecting...")
            await self.connect()

        try:
            await self.channel.default_exchange.publish(
                aio_pika.Message(body=json.dumps(message).encode()), routing_key=self.config.queue_name
            )
            logger.info(f"Message published to queue {self.config.queue_name}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    async def close(self):
        if self.connection:
            logger.info("Closing RabbitMQ connection")
            try:
                await self.connection.close()
                logger.info("RabbitMQ connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}")

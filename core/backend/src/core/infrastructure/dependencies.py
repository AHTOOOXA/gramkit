"""Smart dependency container for application factories.

Provides lazy initialization of infrastructure dependencies (ARQ, Redis, RabbitMQ)
to minimize boilerplate in application entry points.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from arq.connections import ArqRedis

    from core.infrastructure.rabbit.producer import RabbitMQProducer
    from core.infrastructure.redis import RedisClient


class RabbitConfig(Protocol):
    """Protocol for RabbitMQ configuration."""

    url: str
    queue_name: str


class RedisConfig(Protocol):
    """Protocol for Redis configuration."""

    host: str
    port: int
    password: str


@dataclass
class Dependencies:
    """
    Lazy dependency container that creates infrastructure on demand.

    Simplifies application entry points by auto-creating standard dependencies
    (arq, redis, producer) from configs. Supports overriding for advanced use cases.

    Usage (Simple - 95% of cases):
        deps = Dependencies(
            redis_config=redis_config,
            rabbit_config=rabbit_config,
        )

        # Dependencies created on first access
        arq = await deps.get_arq()
        redis = deps.get_redis()

    Usage (Advanced - custom dependencies):
        custom_arq = await create_pool(custom_settings)

        deps = Dependencies(
            redis_config=redis_config,
            rabbit_config=rabbit_config,
            arq=custom_arq,  # Override with custom
        )

    Args:
        redis_config: Configuration for Redis connections (optional if arq/redis provided)
        rabbit_config: Configuration for RabbitMQ (optional if producer provided)
        arq: Pre-created ARQ pool (optional, created lazily if not provided)
        redis: Pre-created Redis client (optional, created lazily if not provided)
        producer: Pre-created RabbitMQ producer (optional, created lazily if not provided)
    """

    redis_config: RedisConfig | None = None
    rabbit_config: RabbitConfig | None = None

    arq: ArqRedis | None = None
    redis: RedisClient | None = None
    producer: RabbitMQProducer | None = None

    _created: dict[str, ArqRedis | RedisClient | RabbitMQProducer] = field(default_factory=dict, init=False, repr=False)

    async def get_arq(self) -> ArqRedis:
        """Get or create ARQ pool."""
        if self.arq is not None:
            return self.arq

        if "arq" not in self._created:
            if self.redis_config is None:
                raise ValueError("redis_config required to create arq pool")

            from arq import create_pool
            from arq.connections import RedisSettings

            self._created["arq"] = await create_pool(
                RedisSettings(
                    host=self.redis_config.host,
                    port=self.redis_config.port,
                    password=self.redis_config.password or None,
                )
            )

        return self._created["arq"]  # type: ignore[return-value]

    def get_redis(self) -> RedisClient:
        """Get or create Redis client."""
        if self.redis is not None:
            return self.redis

        if "redis" not in self._created:
            if self.redis_config is None:
                raise ValueError("redis_config required to create redis client")

            from core.infrastructure.redis import RedisClient

            self._created["redis"] = RedisClient(self.redis_config)

        return self._created["redis"]  # type: ignore[return-value]

    def get_producer(self) -> RabbitMQProducer:
        """Get or create RabbitMQ producer."""
        if self.producer is not None:
            return self.producer

        if "producer" not in self._created:
            if self.rabbit_config is None:
                raise ValueError("rabbit_config required to create producer")

            from core.infrastructure.rabbit.producer import RabbitMQProducer

            self._created["producer"] = RabbitMQProducer(self.rabbit_config)

        return self._created["producer"]  # type: ignore[return-value]

    def get_dependency(self, name: str) -> ArqRedis | RedisClient | RabbitMQProducer | None:
        """
        Get dependency by name (pre-created or lazily created).

        Provides clean API for accessing dependencies without exposing internal _created dict.
        Automatically creates dependencies if config is available.

        Args:
            name: Dependency name ("arq", "redis", or "producer")

        Returns:
            Dependency instance if available, None otherwise

        Usage:
            arq = dependencies.get_dependency("arq")
            redis = dependencies.get_dependency("redis")
            producer = dependencies.get_dependency("producer")
        """
        # Return pre-created dependency first
        pre_created = getattr(self, name, None)
        if pre_created is not None:
            return pre_created

        # Check lazy-created cache
        if name in self._created:
            return self._created[name]

        # Auto-create if config is available (sync dependencies only)
        if name == "redis" and self.redis_config is not None:
            return self.get_redis()
        if name == "producer" and self.rabbit_config is not None:
            return self.get_producer()

        return None

    async def close(self):
        """Cleanup all created dependencies."""
        if "arq" in self._created:
            await self._created["arq"].close()
        if "redis" in self._created and hasattr(self._created["redis"], "close"):
            await self._created["redis"].close()
        if "producer" in self._created and hasattr(self._created["producer"], "close"):
            await self._created["producer"].close()


# Removed: create_service_factory with signature inspection
# Services should be instantiated explicitly for type safety

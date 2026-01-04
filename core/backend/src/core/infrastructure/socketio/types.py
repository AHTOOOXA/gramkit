"""Socket.IO configuration types."""

from dataclasses import dataclass


@dataclass
class SocketIOConfig:
    """Socket.IO server configuration."""

    cors_origins: str | list[str] = "*"
    async_mode: str = "asgi"
    logger: bool = False
    ping_timeout: int = 20
    ping_interval: int = 25

"""Socket.IO server instance."""

from core.infrastructure.socketio import SocketIOConfig, create_socketio

config = SocketIOConfig(
    cors_origins="*",  # Restrict in production
)

sio, socket_app = create_socketio(config)

# Import events to register handlers
from . import events  # noqa: F401, E402

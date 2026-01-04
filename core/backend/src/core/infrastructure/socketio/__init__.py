"""Socket.IO infrastructure."""

from .factory import create_socketio
from .types import SocketIOConfig

__all__ = ["create_socketio", "SocketIOConfig"]

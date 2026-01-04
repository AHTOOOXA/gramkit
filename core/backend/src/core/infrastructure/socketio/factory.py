"""Socket.IO server factory."""

import socketio

from .types import SocketIOConfig


def create_socketio(
    config: SocketIOConfig | None = None,
) -> tuple[socketio.AsyncServer, socketio.ASGIApp]:
    """
    Create configured Socket.IO server and ASGI app.

    Returns (server, asgi_app) tuple. Mount asgi_app at /socket.io in FastAPI.

    Example:
        from core.infrastructure.socketio import create_socketio

        sio, socket_app = create_socketio()

        @sio.event
        async def connect(sid, environ, auth=None):
            pass

        # In app.py:
        app.mount("/socket.io", socket_app)
    """
    cfg = config or SocketIOConfig()

    sio = socketio.AsyncServer(
        async_mode=cfg.async_mode,
        cors_allowed_origins=cfg.cors_origins,
        logger=cfg.logger,
        engineio_logger=cfg.logger,
        ping_timeout=cfg.ping_timeout,
        ping_interval=cfg.ping_interval,
    )

    # socketio_path="" because caller mounts at /socket.io
    asgi_app = socketio.ASGIApp(sio, socketio_path="")

    return sio, asgi_app

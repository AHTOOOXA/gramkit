"""Root path middleware for reverse proxy compatibility.

Strips a configured root_path prefix from incoming request paths so that
Starlette's static file Mounts work correctly regardless of whether the
reverse proxy passes the full path or strips the prefix.

Without this middleware, Starlette's Mount creates child scopes with
root_path = app_root_path + mount_path. When a proxy strips the prefix,
the request path no longer starts with this combined root_path, and
StaticFiles returns 404.
"""

from starlette.types import ASGIApp, Receive, Scope, Send


class RootPathMiddleware:
    """
    ASGI middleware that normalizes request paths for root_path compatibility.

    Strips the configured root_path prefix from scope["path"] if present,
    so routing and static file serving work identically whether the proxy
    passes the full path or strips the prefix.
    """

    def __init__(self, app: ASGIApp, root_path: str = ""):
        self.app = app
        self.root_path = root_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and self.root_path:
            path = scope.get("path", "/")
            if path.startswith(self.root_path):
                scope = dict(scope)
                scope["path"] = path[len(self.root_path) :] or "/"
                scope.setdefault("app_root_path", self.root_path)
        await self.app(scope, receive, send)

"""Static files middleware with caching support."""

from fastapi.staticfiles import StaticFiles


class CachedStaticFiles(StaticFiles):
    """
    Custom StaticFiles class that adds caching headers to static file responses.

    This helps reduce server load by instructing browsers to cache static assets.
    Different cache durations can be set for different types of static content.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize cached static files handler.

        Args:
            *args: Passed to StaticFiles
            **kwargs: Passed to StaticFiles, plus:
                cache_max_age (int): Cache duration in seconds (default: 3600)
                no_cache_paths (list[str]): Path prefixes that should not be cached
        """
        self.cache_max_age = kwargs.pop("cache_max_age", 3600)  # Default 1 hour
        self.no_cache_paths = kwargs.pop("no_cache_paths", [])  # Paths that should not be cached
        super().__init__(*args, **kwargs)

    async def __call__(self, scope, receive, send):
        """Handle static file request with caching headers."""
        original_path = scope["path"]
        if original_path.startswith("/static"):
            # Don't modify the original scope to avoid side effects
            scope_copy = dict(scope)

            # Check if this path should be cached
            should_cache = not any(original_path.startswith(f"/static/{path}") for path in self.no_cache_paths)

            # Add response headers for caching
            async def wrapped_send(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))

                    if should_cache:
                        # Set caching headers
                        headers.append((b"Cache-Control", f"public, max-age={self.cache_max_age}".encode()))
                        headers.append((b"Pragma", b"cache"))
                    else:
                        # Set no-cache headers
                        headers.append((b"Cache-Control", b"no-store, no-cache, must-revalidate, max-age=0"))
                        headers.append((b"Pragma", b"no-cache"))
                        headers.append((b"Expires", b"0"))

                    # Update headers in the message
                    message["headers"] = headers

                await send(message)

            await super().__call__(scope_copy, receive, wrapped_send)
        else:
            await super().__call__(scope, receive, send)

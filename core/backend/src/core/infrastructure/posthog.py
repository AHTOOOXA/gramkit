import threading
from functools import lru_cache
from typing import Any

import posthog as _posthog

from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


class PostHogWrapper:
    """
    Drop-in replacement for PostHog that provides the same API with enhanced error handling.
    All existing posthog.capture() calls will work without modification.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._initialized = False
        self._enabled = False
        self._api_key = None
        self._host = None
        # Don't setup client immediately - do it lazily on first use

    def _setup_client(self, api_key: str = None, host: str = None) -> None:
        """Initialize PostHog client with proper configuration."""
        with self._lock:
            if self._initialized:
                return

            # Store config if provided
            if api_key is not None:
                self._api_key = api_key
            if host is not None:
                self._host = host

            try:
                logger.debug(f"PostHog setup - API key present: {bool(self._api_key)}")
                logger.debug(f"PostHog setup - Host present: {bool(self._host)}")
                logger.debug(
                    f"PostHog setup - API key value: {self._api_key[:10] + '...' if self._api_key else 'None'}"
                )
                logger.debug(f"PostHog setup - Host value: {self._host}")

                if self._api_key and self._host:
                    _posthog.project_api_key = self._api_key
                    _posthog.host = self._host
                    self._enabled = True
                    logger.info("PostHog initialized successfully")
                else:
                    self._enabled = False
                    logger.warning("PostHog API key or host not configured - analytics disabled")
            except Exception as e:
                self._enabled = False
                logger.error(f"Failed to initialize PostHog: {e}")
            finally:
                self._initialized = True

    def capture(self, distinct_id: str, event: str, properties: dict[str, Any] | None = None, **kwargs) -> bool:
        """
        Drop-in replacement for posthog.capture() with error handling.
        Maintains exact same API signature.
        """
        # Ensure client is initialized before use
        if not self._initialized:
            self._setup_client()

        if not self._enabled:
            logger.debug(f"PostHog disabled - skipping event: {event}")
            return False

        try:
            return _posthog.capture(distinct_id=distinct_id, event=event, properties=properties, **kwargs)
        except Exception as e:
            logger.error(f"PostHog capture failed for event '{event}': {e}")
            return False

    def identify(self, distinct_id: str, properties: dict[str, Any] | None = None, **kwargs) -> bool:
        """Drop-in replacement for posthog.identify() with error handling."""
        # Ensure client is initialized before use
        if not self._initialized:
            self._setup_client()

        if not self._enabled:
            logger.debug(f"PostHog disabled - skipping identify: {distinct_id}")
            return False

        try:
            return _posthog.identify(distinct_id=distinct_id, properties=properties, **kwargs)
        except Exception as e:
            logger.error(f"PostHog identify failed for user '{distinct_id}': {e}")
            return False

    def __getattr__(self, name):
        """Proxy any other PostHog methods to maintain full API compatibility."""
        # Ensure client is initialized before use
        if not self._initialized:
            self._setup_client()

        if not self._enabled:
            logger.debug(f"PostHog disabled - skipping method: {name}")
            return lambda *args, **kwargs: False

        try:
            return getattr(_posthog, name)
        except AttributeError:
            logger.warning(f"PostHog method '{name}' not found")
            return lambda *args, **kwargs: False


# Create the singleton instance
posthog = PostHogWrapper()


# For backward compatibility
@lru_cache
def setup_posthog(api_key: str, host: str) -> None:
    """Initialize PostHog client with configuration."""
    # Force initialization now instead of waiting for first use
    posthog._setup_client(api_key=api_key, host=host)

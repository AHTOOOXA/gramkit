"""Sentry user context helpers."""

import sentry_sdk

from core.infrastructure.request_context import set_user_context


def set_sentry_user(
    user_id: str,
    username: str | None = None,
    email: str | None = None,
    tg_username: str | None = None,
) -> None:
    """Set user context for both Sentry and request logging.

    Args:
        user_id: User ID (required)
        username: User's display name (optional)
        email: User's email address (optional)
        tg_username: Telegram username (optional, custom field)
    """
    # Set in request context (for logs)
    set_user_context(user_id)

    # Set in Sentry
    sentry_sdk.set_user(
        {
            "id": user_id,
            "username": username,
            "email": email,
            "tg_username": tg_username,  # custom field
        }
    )

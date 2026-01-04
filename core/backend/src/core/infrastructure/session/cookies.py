"""Session cookie operations.

Plain functions for HTTP cookie operations using unified settings.

Usage:
    from core.infrastructure.session import set_session_cookie, clear_session_cookie

    set_session_cookie(response, session_id)
    clear_session_cookie(response)
    session_id = get_session_from_request(request)
"""

from fastapi import Request, Response

from core.infrastructure.config import settings


def set_session_cookie(response: Response, session_id: str) -> None:
    """Set session cookie on response.

    Uses settings.session for configuration.

    Args:
        response: FastAPI response object
        session_id: Session identifier to set in cookie
    """
    response.set_cookie(
        key=settings.session.cookie_name,
        value=session_id,
        max_age=settings.session.expire_days * 24 * 60 * 60,
        httponly=settings.session.cookie_httponly,
        secure=settings.session.cookie_secure,
        samesite=settings.session.cookie_samesite,
        path="/",
        domain=settings.session.cookie_domain,
    )


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie from response.

    Uses settings.session for configuration.

    Args:
        response: FastAPI response object
    """
    response.delete_cookie(
        key=settings.session.cookie_name,
        httponly=settings.session.cookie_httponly,
        secure=settings.session.cookie_secure,
        samesite=settings.session.cookie_samesite,
        path="/",
        domain=settings.session.cookie_domain,
    )


def get_session_from_request(request: Request) -> str | None:
    """Extract session ID from request cookies.

    Uses settings.session for configuration.

    Args:
        request: FastAPI request object

    Returns:
        Session identifier if present in cookies, None otherwise
    """
    return request.cookies.get(settings.session.cookie_name)

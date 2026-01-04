"""Session cookie operations.

Usage:
    from core.infrastructure.session import set_session_cookie, clear_session_cookie

    set_session_cookie(response, session_id)
    clear_session_cookie(response)
    session_id = get_session_from_request(request)
"""

from core.infrastructure.session.cookies import (
    clear_session_cookie,
    get_session_from_request,
    set_session_cookie,
)

__all__ = ["set_session_cookie", "clear_session_cookie", "get_session_from_request"]

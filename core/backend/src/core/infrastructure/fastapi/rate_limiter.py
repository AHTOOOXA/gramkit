from fastapi import Request
from slowapi import Limiter

from core.schemas.users import UserSchema


def get_user_id(request: Request) -> str | None:
    user: UserSchema | None = getattr(request.state, "user", None)
    return str(user.id) if user else None


limiter = Limiter(key_func=get_user_id)

SOFT_LIMIT = "100/minute"  # 100 requests per minute
HARD_LIMIT = "10/minute"  # 10 requests per minute
READING_LIMIT = "100/day"  # 100 requests per day

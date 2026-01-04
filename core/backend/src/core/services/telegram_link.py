"""Telegram account linking service.

Allows web users (authenticated via email) to link their Telegram accounts.
"""

import json
import secrets
from datetime import UTC, datetime
from uuid import UUID

from core.infrastructure.database.repo.users import UserRepo
from core.infrastructure.logging import get_logger
from core.infrastructure.redis import RedisClient

logger = get_logger(__name__)


class RedisKeys:
    """Redis key patterns for Telegram linking."""

    LINK_TOKEN = "telegram_link:{token}"
    RATE_LIMIT = "telegram_link:rate:{user_id}"


# Constants
LINK_TOKEN_TTL = 300  # 5 minutes
RATE_LIMIT_WINDOW = 900  # 15 minutes
RATE_LIMIT_MAX = 5  # Max link attempts per user


class TelegramLinkService:
    """Service for linking Telegram accounts to existing users.

    Flow:
    1. Web user (email auth) calls start_link() to get a link token
    2. User opens Telegram bot with deep link: t.me/bot?start=link_{token}
    3. Bot calls complete_link() with token and Telegram user info
    4. Web frontend polls get_status() to detect completion
    """

    def __init__(
        self,
        redis: RedisClient,
        user_repo: UserRepo,
        bot_url: str,
    ):
        """Initialize Telegram link service.

        Args:
            redis: Redis client for token storage
            user_repo: User repository
            bot_url: Telegram bot URL (e.g., "https://t.me/mybot")
        """
        self.redis = redis
        self.user_repo = user_repo
        self.bot_url = bot_url

    async def start_link(self, user_id: UUID) -> dict:
        """Start Telegram linking flow.

        Generates a link token and returns bot URL with deep link.

        Args:
            user_id: ID of the user to link Telegram to

        Returns:
            dict with link_token, bot_url, expires_in

        Raises:
            ValueError: If user already has Telegram linked or rate limited
        """
        # Check rate limit
        if not await self._check_rate_limit(user_id):
            raise ValueError("rate_limited")

        # Get user and check if already linked
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("user_not_found")

        if user.telegram_id is not None:
            raise ValueError("already_linked")

        # Generate secure link token
        link_token = secrets.token_urlsafe(32)

        # Store token in Redis
        token_data = {
            "user_id": str(user_id),
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }

        redis_key = RedisKeys.LINK_TOKEN.format(token=link_token)
        await self.redis.set(redis_key, json.dumps(token_data), ex=LINK_TOKEN_TTL)

        # Increment rate limit
        await self._increment_rate_limit(user_id)

        # Build bot URL with deep link
        bot_deep_link = f"{self.bot_url}?start=link_{link_token}"

        logger.info(f"Telegram link started for user_id={user_id}")

        return {
            "link_token": link_token,
            "bot_url": bot_deep_link,
            "expires_in": LINK_TOKEN_TTL,
        }

    async def complete_link(
        self,
        token: str,
        telegram_id: int,
        telegram_user_data: dict,
    ) -> dict:
        """Complete Telegram linking (called by bot).

        Args:
            token: Link token from deep link
            telegram_id: Telegram user ID
            telegram_user_data: Full Telegram user data (first_name, username, etc.)

        Returns:
            dict with user_id and success status

        Raises:
            ValueError: If token invalid/expired or Telegram already used
        """
        # Get token data
        redis_key = RedisKeys.LINK_TOKEN.format(token=token)
        data_raw = await self.redis.get(redis_key)

        if not data_raw:
            raise ValueError("token_invalid")

        token_data = json.loads(data_raw if isinstance(data_raw, str) else data_raw.decode())

        if token_data.get("status") != "pending":
            raise ValueError("token_invalid")

        user_id = token_data["user_id"]

        # Check if Telegram ID already linked to another user
        existing_user = await self.user_repo.get_by_telegram_id(telegram_id)
        if existing_user and existing_user.id != user_id:
            # Update token status so frontend stops polling
            await self._set_error_status(token, redis_key, "telegram_already_used")
            raise ValueError("telegram_already_used")

        # Get user and update with Telegram data
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            await self.redis.delete(redis_key)
            raise ValueError("user_not_found")

        # Update user with Telegram data (using tg_ prefixed fields)
        user.telegram_id = telegram_id
        user.tg_first_name = telegram_user_data.get("tg_first_name", user.tg_first_name)
        user.tg_last_name = telegram_user_data.get("tg_last_name")
        user.tg_username = telegram_user_data.get("tg_username")
        user.tg_language_code = telegram_user_data.get("tg_language_code")
        user.tg_is_premium = telegram_user_data.get("tg_is_premium")
        user.tg_is_bot = telegram_user_data.get("tg_is_bot")
        # Also update app profile language if not set
        if not user.language_code:
            user.language_code = telegram_user_data.get("tg_language_code")
        # Set display_name if not already set
        if not user.display_name:
            tg_first = telegram_user_data.get("tg_first_name", "")
            tg_last = telegram_user_data.get("tg_last_name", "")
            user.display_name = f"{tg_first} {tg_last}".strip() or telegram_user_data.get("tg_username") or "User"

        # Update token status
        token_data["status"] = "completed"
        token_data["telegram_id"] = telegram_id
        token_data["telegram_username"] = telegram_user_data.get("tg_username")
        token_data["completed_at"] = datetime.now(UTC).isoformat()

        # Keep token for a short time so frontend can poll for completion
        await self.redis.set(redis_key, json.dumps(token_data), ex=60)

        logger.info(f"Telegram linked for user_id={user_id}, telegram_id={telegram_id}")

        return {
            "user_id": user_id,
            "success": True,
        }

    async def get_status(self, token: str) -> dict | None:
        """Get link token status (for frontend polling).

        Args:
            token: Link token

        Returns:
            dict with status, telegram_id, telegram_username
            None if token not found/expired
        """
        redis_key = RedisKeys.LINK_TOKEN.format(token=token)
        data_raw = await self.redis.get(redis_key)

        if not data_raw:
            return None

        token_data = json.loads(data_raw if isinstance(data_raw, str) else data_raw.decode())

        return {
            "status": token_data.get("status", "pending"),
            "telegram_id": token_data.get("telegram_id"),
            "telegram_username": token_data.get("telegram_username"),
            "error": token_data.get("error"),
        }

    async def _check_rate_limit(self, user_id: UUID) -> bool:
        """Check if user is rate limited."""
        rate_key = RedisKeys.RATE_LIMIT.format(user_id=user_id)
        data = await self.redis.get(rate_key)

        if data:
            count = int(data if isinstance(data, (int, str)) else data.decode())
            if count >= RATE_LIMIT_MAX:
                return False

        return True

    async def _increment_rate_limit(self, user_id: UUID) -> None:
        """Increment rate limit counter."""
        rate_key = RedisKeys.RATE_LIMIT.format(user_id=user_id)
        count = await self.redis.incr(rate_key)
        if count == 1:
            await self.redis.expire(rate_key, RATE_LIMIT_WINDOW)

    async def _set_error_status(self, token: str, redis_key: str, error_code: str) -> None:
        """Set token status to error so frontend stops polling."""
        data_raw = await self.redis.get(redis_key)
        if data_raw:
            token_data = json.loads(data_raw if isinstance(data_raw, str) else data_raw.decode())
            token_data["status"] = "error"
            token_data["error"] = error_code
            # Keep for 60 seconds so frontend can read the error
            await self.redis.set(redis_key, json.dumps(token_data), ex=60)
            logger.info(f"Link token status set to error: {token[:8]}..., error={error_code}")

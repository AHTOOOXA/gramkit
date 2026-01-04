"""Unified authentication service.

This service consolidates all authentication methods:
1. Code-based auth: 6-digit verification codes sent via Telegram
2. Deep link auth: Telegram bot link authentication
3. Email auth: Email signup, login, linking, and password reset
"""

import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from aiogram import Bot

from core.infrastructure.config import settings
from core.infrastructure.database.repo.requests import CoreRequestsRepo
from core.infrastructure.logging import get_logger
from core.infrastructure.rabbit.producer import RabbitMQProducer
from core.infrastructure.redis import RedisClient
from core.infrastructure.utils import normalize_email
from core.schemas.users import UserSchema
from core.services.base import BaseService
from core.services.password import PasswordService

if TYPE_CHECKING:
    from core.services.requests import CoreRequestsService

logger = get_logger(__name__)

# =============================================================================
# Code-based auth configuration
# =============================================================================

AUTH_CODE_LENGTH = 6
AUTH_CODE_EXPIRY_MINUTES = 5
AUTH_CODE_PREFIX = "auth_code:"
RATE_LIMIT_PREFIX = "auth_rate:"

MAX_CODE_REQUESTS_PER_HOUR = 5
MAX_VERIFICATION_ATTEMPTS_PER_HOUR = 10

# =============================================================================
# Deep link auth configuration
# =============================================================================

LINK_TOKEN_PREFIX = "web_auth:"
LINK_TOKEN_TTL = 300  # 5 minutes

# =============================================================================
# Email auth configuration
# =============================================================================


class EmailRedisKeys:
    """Redis key patterns for email auth."""

    # Flow data (10 min TTL)
    SIGNUP = "email:signup:{token}"
    LINK = "email:link:{user_id}"
    RESET = "email:reset:{token}"

    # Rate limiting
    RATE_EMAIL = "email:rate:{email}"  # Per-email operations (15 min window)
    LOCKOUT_LOGIN = "email:lockout:login:{email}"  # Login lockout (15 min)
    LOCKOUT_VERIFY = "email:lockout:verify:{email}"  # Post-invalidation cooldown (5 min)


# Email auth TTL constants
EMAIL_SIGNUP_TTL = 600  # 10 minutes
EMAIL_LINK_TTL = 600  # 10 minutes
EMAIL_RESET_TTL = 600  # 10 minutes
EMAIL_RATE_LIMIT_WINDOW = 900  # 15 minutes
EMAIL_RATE_LIMIT_MAX = 15  # Max failed attempts per email (protects against brute force, allows typos)
EMAIL_LOGIN_LOCKOUT_TTL = 900  # 15 minutes
EMAIL_VERIFY_COOLDOWN_TTL = 300  # 5 minutes after token invalidation
EMAIL_MAX_CODE_ATTEMPTS = 5

# Dummy password hash for constant-time comparison when user doesn't exist.
# This prevents timing attacks that could enumerate valid usernames/emails.
# Generated with: argon2.using(memory_cost=65536, time_cost=3, parallelism=4).hash("dummy")
DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$Y0zJ2VvrPee8lzImpDSGcA$NkffK9GiF7nuARNbl/Lx+ykhHeNuOutzqbi+JdJRjT0"
)

# Resend onboarding domain for unverified domains
RESEND_ONBOARDING_ADDRESS = "onboarding@resend.dev"


class AuthService(BaseService):
    """Unified authentication service.

    Provides three authentication methods:
    1. Code-based auth (Telegram)
    2. Deep link auth (Telegram bot)
    3. Email auth (signup, login, linking, password reset)

    Code-based auth flow:
    1. User enters username on web
    2. send_verification_code() generates 6-digit code
    3. Code sent to user via Telegram bot
    4. User enters code on web
    5. verify_code() validates and returns user

    Deep link auth flow:
    1. Frontend calls create_link_token() to get token
    2. User is redirected to Telegram bot with token
    3. Bot calls verify_link_token() with user session
    4. Frontend polls get_link_status() until verified
    5. Frontend calls consume_link_token() to finalize

    Email auth flow:
    - Signup: email_start_signup() → email_complete_signup()
    - Login: email_login()
    - Link: email_start_link() → email_complete_link()
    - Reset: email_start_reset() → email_complete_reset()
    """

    def __init__(
        self,
        repo: CoreRequestsRepo,
        producer: RabbitMQProducer,
        services: CoreRequestsService,
        bot: Bot,
    ):
        """
        Initialize authentication service.

        Uses settings.email for email configuration.

        Args:
            repo: Core repository aggregator
            producer: RabbitMQ producer
            services: Core service aggregator
            bot: Telegram bot instance
        """
        super().__init__(repo, producer, services, bot)
        self.redis: RedisClient = services.redis
        self._password_service = PasswordService()

    # =========================================================================
    # Code-based auth methods
    # =========================================================================

    def _generate_auth_code(self) -> str:
        """Generate a secure 6-digit numeric code."""
        return "".join([str(secrets.randbelow(10)) for _ in range(AUTH_CODE_LENGTH)])

    async def _check_rate_limit(self, key: str, max_attempts: int) -> bool:
        """Check if rate limit is exceeded for the given key."""
        try:
            current_count_bytes = await self.redis.get(key)
            current_count = int(current_count_bytes.decode("utf-8")) if current_count_bytes else 0

            if current_count >= max_attempts:
                return False

            new_count = current_count + 1
            await self.redis.set(key, str(new_count), ex=3600)  # 1 hour
            return True
        except Exception as e:
            logger.error(f"Rate limit check failed for {key}: {e}")
            return True  # Allow on error to avoid blocking users

    async def send_verification_code(self, username: str) -> dict:
        """
        Generate and store verification code for username.

        Args:
            username: Telegram username (with or without @)

        Returns:
            dict with success status, message, code, and telegram_id
        """
        try:
            clean_username = username.lstrip("@").lower()

            rate_limit_key = f"{RATE_LIMIT_PREFIX}send:{clean_username}"
            if not await self._check_rate_limit(rate_limit_key, MAX_CODE_REQUESTS_PER_HOUR):
                return {
                    "success": False,
                    "error": "Too many code requests. Please wait before requesting another code.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                }

            user = await self.repo.users.get_by_tg_username(clean_username)
            if not user:
                return {
                    "success": False,
                    "error": "Username not found. Please make sure you've used our Telegram bot before.",
                    "error_code": "USER_NOT_FOUND",
                }

            code = self._generate_auth_code()

            code_key = f"{AUTH_CODE_PREFIX}{clean_username}"
            code_data = {
                "code": code,
                "user_id": user.id,
                "created_at": datetime.now(UTC).isoformat(),
                "expires_at": (datetime.now(UTC) + timedelta(minutes=AUTH_CODE_EXPIRY_MINUTES)).isoformat(),
            }

            await self.redis.set(code_key, json.dumps(code_data), ex=AUTH_CODE_EXPIRY_MINUTES * 60)

            logger.info(f"Verification code generated for username {clean_username}")

            return {
                "success": True,
                "message": "Verification code sent to your Telegram",
                "expires_in": AUTH_CODE_EXPIRY_MINUTES * 60,
                "code": code,
                "telegram_id": user.telegram_id,
            }

        except Exception as e:
            logger.error(f"Error sending verification code for {username}: {e}")
            return {
                "success": False,
                "error": "Failed to send verification code. Please try again.",
                "error_code": "INTERNAL_ERROR",
            }

    async def verify_code(self, username: str, code: str) -> dict:
        """
        Verify the provided code for username.

        Args:
            username: Telegram username (with or without @)
            code: 6-digit verification code

        Returns:
            dict with success status and user data if successful
        """
        try:
            clean_username = username.lstrip("@").lower()

            rate_limit_key = f"{RATE_LIMIT_PREFIX}verify:{clean_username}"
            if not await self._check_rate_limit(rate_limit_key, MAX_VERIFICATION_ATTEMPTS_PER_HOUR):
                return {
                    "success": False,
                    "error": "Too many verification attempts. Please wait before trying again.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                }

            if not code or len(code) != AUTH_CODE_LENGTH or not code.isdigit():
                return {
                    "success": False,
                    "error": "Invalid code format. Please enter a 6-digit code.",
                    "error_code": "INVALID_CODE_FORMAT",
                }

            code_key = f"{AUTH_CODE_PREFIX}{clean_username}"
            stored_data_bytes = await self.redis.get(code_key)

            if not stored_data_bytes:
                return {
                    "success": False,
                    "error": "Verification code expired or not found. Please request a new code.",
                    "error_code": "CODE_EXPIRED",
                }

            try:
                stored_data = json.loads(stored_data_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {
                    "success": False,
                    "error": "Invalid verification data. Please request a new code.",
                    "error_code": "INVALID_DATA",
                }

            if stored_data.get("code") != code:
                return {
                    "success": False,
                    "error": "Invalid verification code. Please check and try again.",
                    "error_code": "CODE_MISMATCH",
                }

            expires_at = datetime.fromisoformat(stored_data.get("expires_at"))
            if datetime.now(UTC) > expires_at:
                await self.redis.delete(code_key)
                return {
                    "success": False,
                    "error": "Verification code expired. Please request a new code.",
                    "error_code": "CODE_EXPIRED",
                }

            user_id = stored_data.get("user_id")
            user = await self.repo.users.get_user_by_id(user_id)

            if not user:
                return {
                    "success": False,
                    "error": "User account not found. Please contact support.",
                    "error_code": "USER_NOT_FOUND",
                }

            await self.redis.delete(code_key)

            logger.info(f"Verification successful for username {clean_username}, user_id {user_id}")

            # Create session (like email_login does)
            session_id = await self.services.sessions.create_session(
                user_id=user.id,
                user_type=user.user_type.value,
                metadata={"auth_method": "telegram_code"},
            )

            return {
                "success": True,
                "message": "Verification successful",
                "user": UserSchema.model_validate(user),
                "session_id": session_id,
            }

        except Exception as e:
            logger.error(f"Error verifying code for {username}: {e}")
            return {"success": False, "error": "Verification failed. Please try again.", "error_code": "INTERNAL_ERROR"}

    # =========================================================================
    # Deep link auth methods
    # =========================================================================

    async def create_link_token(self, ip: str | None = None) -> str:
        """Create new deep link auth token.

        Args:
            ip: Client IP address for tracking

        Returns:
            Generated token string (URL-safe, 43 characters)
        """
        token = secrets.token_urlsafe(32)
        redis_key = f"{LINK_TOKEN_PREFIX}{token}"

        token_data = {
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
            "ip": ip or "unknown",
        }

        await self.redis.set(redis_key, json.dumps(token_data), ex=LINK_TOKEN_TTL)

        logger.info(f"Link auth token created: {token[:8]}...")
        return token

    async def get_link_status(self, token: str) -> dict | None:
        """Get token data, returns None if expired/not found.

        Args:
            token: Auth token to check

        Returns:
            Token data dict or None if not found/expired
        """
        redis_key = f"{LINK_TOKEN_PREFIX}{token}"
        data = await self.redis.get(redis_key)

        if not data:
            return None

        if isinstance(data, bytes):
            data = data.decode("utf-8")

        return json.loads(data)

    async def verify_link_token(self, token: str, user_id: UUID, session_id: str) -> bool:
        """Mark token as verified (called by bot after auth).

        This is called by the Telegram bot after the user authenticates.
        Updates the token with user_id and session_id so the web can
        retrieve them when polling the check endpoint.

        Args:
            token: Auth token to verify
            user_id: Authenticated user's ID
            session_id: Created session ID

        Returns:
            True if token was pending and is now verified, False otherwise
        """
        redis_key = f"{LINK_TOKEN_PREFIX}{token}"
        data = await self.redis.get(redis_key)

        if not data:
            logger.warning(f"Token not found for verification: {token[:8]}...")
            return False

        if isinstance(data, bytes):
            data = data.decode("utf-8")

        token_data = json.loads(data)

        if token_data.get("status") != "pending":
            logger.warning(f"Token not pending: {token[:8]}..., status={token_data.get('status')}")
            return False

        token_data.update(
            {
                "status": "verified",
                "user_id": str(user_id),
                "session_id": session_id,
                "verified_at": datetime.now(UTC).isoformat(),
            }
        )

        await self.redis.set(redis_key, json.dumps(token_data), ex=60)

        logger.info(f"Link auth token verified: {token[:8]}..., user_id={user_id}")
        return True

    async def consume_link_token(self, token: str) -> dict | None:
        """Get and delete token (single use).

        Used by the web API when token is verified to get session info
        and delete the token (preventing reuse).

        Args:
            token: Auth token to consume

        Returns:
            Token data if verified, None otherwise
        """
        redis_key = f"{LINK_TOKEN_PREFIX}{token}"
        data = await self.redis.get(redis_key)

        if not data:
            return None

        if isinstance(data, bytes):
            data = data.decode("utf-8")

        token_data = json.loads(data)

        if token_data.get("status") == "verified":
            await self.redis.delete(redis_key)
            return token_data

        return None

    # =========================================================================
    # Email auth private helpers
    # =========================================================================

    async def _send_email(self, to_email: str, code: str, first_name: str | None = None) -> bool:
        """Send verification email via Resend.

        Args:
            to_email: Recipient email address
            code: 6-digit verification code
            first_name: Optional recipient name for personalization

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.email or not settings.email.api_key:
            logger.error("Email not configured - cannot send verification email")
            return False

        import resend

        resend.api_key = settings.email.api_key

        # Build email content
        subject = "Your verification code"
        html_content = self._build_email_html(code, first_name)

        # Try with configured address first, fall back to onboarding if domain not verified
        from_addresses = [settings.email.from_address]
        if settings.email.from_address != RESEND_ONBOARDING_ADDRESS:
            from_addresses.append(RESEND_ONBOARDING_ADDRESS)

        for from_addr in from_addresses:
            try:
                result = resend.Emails.send(
                    {
                        "from": f"{settings.email.from_name} <{from_addr}>",
                        "to": [to_email],
                        "subject": subject,
                        "html": html_content,
                    }
                )

                logger.info(
                    f"Verification email sent to {to_email[:3]}***@***, id={result.get('id')}, from={from_addr}"
                )
                return True

            except Exception as e:
                error_str = str(e)
                # If domain not verified, try fallback
                if "domain is not verified" in error_str.lower() and from_addr != RESEND_ONBOARDING_ADDRESS:
                    logger.warning(f"Domain not verified for {from_addr}, falling back to {RESEND_ONBOARDING_ADDRESS}")
                    continue
                logger.error(f"Failed to send verification email to {to_email[:3]}***@***: {e}")
                return False

        return False

    def _build_email_html(self, code: str, first_name: str | None = None) -> str:
        """Build HTML content for verification email."""
        greeting = f"Hi {first_name}," if first_name else "Hi,"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #333; margin-bottom: 24px;">Verify your email</h2>

            <p style="color: #666; font-size: 16px;">{greeting}</p>

            <p style="color: #666; font-size: 16px;">Your verification code is:</p>

            <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; padding: 24px; background: #f5f5f5; text-align: center; border-radius: 8px; margin: 24px 0;">
                {code}
            </div>

            <p style="color: #999; font-size: 14px;">This code expires in 10 minutes.</p>

            <p style="color: #999; font-size: 14px;">If you didn't request this code, you can safely ignore this email.</p>
        </body>
        </html>
        """

    async def _check_email_rate_limit(self, email: str) -> bool:
        """Check if email operations are rate limited."""
        rate_key = EmailRedisKeys.RATE_EMAIL.format(email=email)
        data = await self.redis.get(rate_key)

        if data:
            count = int(data if isinstance(data, (int, str)) else data.decode())
            if count >= EMAIL_RATE_LIMIT_MAX:
                return False

        return True

    async def _increment_email_rate_limit(self, email: str) -> None:
        """Increment rate limit counter for email."""
        rate_key = EmailRedisKeys.RATE_EMAIL.format(email=email)
        count = await self.redis.incr(rate_key)
        if count == 1:
            await self.redis.expire(rate_key, EMAIL_RATE_LIMIT_WINDOW)

    async def _is_in_cooldown(self, email: str) -> bool:
        """Check if email is in cooldown after failed attempts."""
        cooldown_key = EmailRedisKeys.LOCKOUT_VERIFY.format(email=email)
        return await self.redis.exists(cooldown_key) > 0

    async def _set_cooldown(self, email: str) -> None:
        """Set cooldown after too many failed verification attempts."""
        cooldown_key = EmailRedisKeys.LOCKOUT_VERIFY.format(email=email)
        await self.redis.set(cooldown_key, "1", ex=EMAIL_VERIFY_COOLDOWN_TTL)

    async def _handle_login_failure(self, email: str) -> None:
        """Handle failed login attempt (rate limiting)."""
        rate_key = EmailRedisKeys.RATE_EMAIL.format(email=email)

        count = await self.redis.incr(rate_key)
        if count == 1:
            await self.redis.expire(rate_key, EMAIL_RATE_LIMIT_WINDOW)

        if count >= EMAIL_RATE_LIMIT_MAX:
            # Lock account
            lockout_key = EmailRedisKeys.LOCKOUT_LOGIN.format(email=email)
            await self.redis.set(lockout_key, "1", ex=EMAIL_LOGIN_LOCKOUT_TTL)
            await self.redis.delete(rate_key)
            logger.warning(f"Account locked due to failed attempts: {email[:3]}***")

    # =========================================================================
    # Email auth: Check email existence
    # =========================================================================

    async def email_check_exists(self, email: str) -> bool:
        """
        Check if email is already registered.

        Args:
            email: User's email address

        Returns:
            bool: True if email exists (registered), False otherwise
        """
        normalized = normalize_email(email)
        exists = await self.repo.users.is_email_verified_by_any_user(normalized)
        return exists

    # =========================================================================
    # Email auth: Signup flow
    # =========================================================================

    async def email_start_signup(self, email: str) -> dict[str, Any]:
        """
        Start email signup flow.

        Creates pending signup in Redis and sends verification code.

        Args:
            email: User's email address

        Returns:
            dict with signup_token and expires_in

        Raises:
            ValueError: If email already verified or rate limited
        """
        normalized = normalize_email(email)

        # Check rate limit
        if not await self._check_email_rate_limit(normalized):
            raise ValueError("rate_limited")

        # Check cooldown (after failed verification attempts)
        if await self._is_in_cooldown(normalized):
            raise ValueError("rate_limited")

        # Check if email already verified
        if await self.repo.users.is_email_verified_by_any_user(normalized):
            raise ValueError("email_already_in_use")

        # Generate token and code
        signup_token = secrets.token_urlsafe(32)
        code = self._password_service.generate_verification_code()

        # Store in Redis
        signup_data = {
            "email": normalized,
            "code": code,
            "created_at": datetime.now(UTC).isoformat(),
            "attempts": 0,
        }

        redis_key = EmailRedisKeys.SIGNUP.format(token=signup_token)
        await self.redis.set(redis_key, json.dumps(signup_data), ex=EMAIL_SIGNUP_TTL)

        # Send verification email
        sent = await self._send_email(normalized, code)
        if not sent:
            await self.redis.delete(redis_key)
            raise ValueError("email_send_failed")

        # Increment rate limit counter
        await self._increment_email_rate_limit(normalized)

        logger.info(f"Email signup started for {normalized[:3]}***")

        return {
            "signup_token": signup_token,
            "expires_in": EMAIL_SIGNUP_TTL,
        }

    async def email_complete_signup(
        self,
        signup_token: str,
        code: str,
        password: str,
        username: str,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Complete email signup flow.

        Verifies code, creates user, and starts session.

        Args:
            signup_token: Token from email_start_signup
            code: 6-digit verification code
            password: User's chosen password
            username: User's chosen username
            language_code: Optional language code (defaults to "en")

        Returns:
            dict with user data and session info

        Raises:
            ValueError: If token/code invalid, password weak, or email taken
        """
        # Get signup data from Redis
        redis_key = EmailRedisKeys.SIGNUP.format(token=signup_token)
        data_raw = await self.redis.get(redis_key)

        if not data_raw:
            raise ValueError("signup_token_invalid")

        signup_data = json.loads(data_raw if isinstance(data_raw, str) else data_raw.decode())
        email = signup_data["email"]

        # Check attempts
        attempts = signup_data.get("attempts", 0)
        if attempts >= EMAIL_MAX_CODE_ATTEMPTS:
            await self.redis.delete(redis_key)
            await self._set_cooldown(email)
            raise ValueError("code_invalid")  # Token invalidated

        # Verify code
        if not secrets.compare_digest(signup_data["code"], code):
            # Increment attempts
            signup_data["attempts"] = attempts + 1
            await self.redis.set(redis_key, json.dumps(signup_data), ex=EMAIL_SIGNUP_TTL)

            if signup_data["attempts"] >= EMAIL_MAX_CODE_ATTEMPTS:
                await self.redis.delete(redis_key)
                await self._set_cooldown(email)

            raise ValueError("code_invalid")

        # Validate password
        is_valid, error_msg = self._password_service.validate_strength(password)
        if not is_valid:
            raise ValueError("password_too_weak")

        # Check email still available (race condition protection)
        if await self.repo.users.is_email_verified_by_any_user(email):
            await self.redis.delete(redis_key)
            raise ValueError("email_already_in_use")

        # Create user
        password_hash = self._password_service.hash_password(password)
        now = datetime.now(UTC)

        user = await self.repo.users.create(
            {
                "username": username,
                "display_name": username,  # Initial display name from username
                "tg_first_name": None,  # No Telegram data for email users
                "email": email,
                "email_verified": True,
                "email_verified_at": now,
                "password_hash": password_hash,
                "last_login_at": now,
                "language_code": language_code or "en",
            }
        )

        # Delete signup token
        await self.redis.delete(redis_key)

        # Create session
        session_id = await self.services.sessions.create_session(user.id, user.user_type.value)

        logger.info(f"Email signup completed for user_id={user.id}")

        return {
            "user": user,
            "session_id": session_id,
        }

    # =========================================================================
    # Email auth: Login flow
    # =========================================================================

    async def email_login(self, email_or_username: str, password: str) -> dict[str, Any]:
        """
        Login with email/username and password.

        Args:
            email_or_username: User's email address or username
            password: User's password

        Returns:
            dict with user data and session info

        Raises:
            ValueError: If credentials invalid or account locked
        """
        # Detect if input is email or username
        is_email = "@" in email_or_username

        if is_email:
            normalized = normalize_email(email_or_username)
            lockout_identifier = normalized
        else:
            normalized = email_or_username.lower().strip()
            lockout_identifier = f"username:{normalized}"

        # Check lockout
        lockout_key = EmailRedisKeys.LOCKOUT_LOGIN.format(email=lockout_identifier)
        if await self.redis.exists(lockout_key):
            raise ValueError("account_locked")

        # Get user by email or username
        if is_email:
            user = await self.repo.users.get_by_verified_email(normalized)
        else:
            user = await self.repo.users.get_by_username(normalized)
            # Must have verified email to login via username
            if user and not user.email_verified_at:
                user = None

        # Always perform password verification to prevent timing attacks.
        # Use dummy hash if user doesn't exist to make timing consistent.
        password_hash = user.password_hash if (user and user.password_hash) else DUMMY_PASSWORD_HASH
        password_valid = self._password_service.verify_password(password, password_hash)

        # Check if login should fail (user not found or password invalid)
        if not user or not user.password_hash or not password_valid:
            await self._handle_login_failure(lockout_identifier)
            raise ValueError("invalid_credentials")

        # Clear any failed attempt counters
        rate_key = EmailRedisKeys.RATE_EMAIL.format(email=lockout_identifier)
        await self.redis.delete(rate_key)

        # Update last login
        user.last_login_at = datetime.now(UTC)
        await self.repo.users.session.flush()

        # Create session
        session_id = await self.services.sessions.create_session(user.id, user.user_type.value)

        logger.info(f"Email login successful for user_id={user.id}")

        return {
            "user": user,
            "session_id": session_id,
        }

    # =========================================================================
    # Email auth: Link flow (for Telegram users)
    # =========================================================================

    async def email_start_link(self, user_id: UUID, email: str) -> dict[str, Any]:
        """
        Start email linking flow for existing user.

        Args:
            user_id: Current user's ID
            email: Email to link

        Returns:
            dict with expires_in

        Raises:
            ValueError: If email already in use or rate limited
        """
        normalized = normalize_email(email)

        # Check rate limit
        if not await self._check_email_rate_limit(normalized):
            raise ValueError("rate_limited")

        # Check cooldown
        if await self._is_in_cooldown(normalized):
            raise ValueError("rate_limited")

        # Get current user
        user = await self.repo.users.get_by_id(user_id)
        if not user:
            raise ValueError("user_not_found")

        # Check if user already has verified email
        if user.email_verified:
            raise ValueError("email_already_verified")

        # Check if email already verified by another user
        if await self.repo.users.is_email_verified_by_any_user(normalized):
            raise ValueError("email_already_in_use")

        # Generate code
        code = self._password_service.generate_verification_code()

        # Store in Redis
        link_data = {
            "email": normalized,
            "code": code,
            "created_at": datetime.now(UTC).isoformat(),
            "attempts": 0,
        }

        redis_key = EmailRedisKeys.LINK.format(user_id=user_id)
        await self.redis.set(redis_key, json.dumps(link_data), ex=EMAIL_LINK_TTL)

        # Send verification email (use user's display_name if available)
        sent = await self._send_email(normalized, code, first_name=getattr(user, "display_name", None))
        if not sent:
            await self.redis.delete(redis_key)
            raise ValueError("email_send_failed")

        # Increment rate limit
        await self._increment_email_rate_limit(normalized)

        logger.info(f"Email link started for user_id={user_id}")

        return {
            "expires_in": EMAIL_LINK_TTL,
        }

    async def email_complete_link(
        self,
        user_id: UUID,
        code: str,
        password: str,
    ) -> dict[str, Any]:
        """
        Complete email linking flow.

        Args:
            user_id: Current user's ID
            code: 6-digit verification code
            password: Password to set for email login

        Returns:
            dict with success status

        Raises:
            ValueError: If code invalid or password weak
        """
        # Get link data from Redis
        redis_key = EmailRedisKeys.LINK.format(user_id=user_id)
        data_raw = await self.redis.get(redis_key)

        if not data_raw:
            raise ValueError("code_expired")

        link_data = json.loads(data_raw if isinstance(data_raw, str) else data_raw.decode())
        email = link_data["email"]

        # Check attempts
        attempts = link_data.get("attempts", 0)
        if attempts >= EMAIL_MAX_CODE_ATTEMPTS:
            await self.redis.delete(redis_key)
            await self._set_cooldown(email)
            raise ValueError("code_invalid")

        # Verify code
        if not secrets.compare_digest(link_data["code"], code):
            link_data["attempts"] = attempts + 1
            await self.redis.set(redis_key, json.dumps(link_data), ex=EMAIL_LINK_TTL)

            if link_data["attempts"] >= EMAIL_MAX_CODE_ATTEMPTS:
                await self.redis.delete(redis_key)
                await self._set_cooldown(email)

            raise ValueError("code_invalid")

        # Validate password
        is_valid, error_msg = self._password_service.validate_strength(password)
        if not is_valid:
            raise ValueError("password_too_weak")

        # Check email still available
        if await self.repo.users.is_email_verified_by_any_user(email):
            await self.redis.delete(redis_key)
            raise ValueError("email_already_in_use")

        # Get and update user
        user = await self.repo.users.get_by_id(user_id)
        if not user:
            raise ValueError("user_not_found")

        user.email = email
        user.email_verified = True
        user.email_verified_at = datetime.now(UTC)
        user.password_hash = self._password_service.hash_password(password)

        # Flush changes to database (commit happens at dependency layer)
        await self.repo.users.session.flush()

        # Delete link token
        await self.redis.delete(redis_key)

        logger.info(f"Email linked for user_id={user_id}")

        return {
            "success": True,
        }

    # =========================================================================
    # Email auth: Password reset flow
    # =========================================================================

    async def email_start_reset(self, email: str) -> dict[str, Any]:
        """
        Start password reset flow.

        Creates pending reset in Redis and sends verification code.

        Args:
            email: User's email address

        Returns:
            dict with reset_token and expires_in

        Raises:
            ValueError: If email not found or rate limited
        """
        normalized = normalize_email(email)

        # Check rate limit
        if not await self._check_email_rate_limit(normalized):
            raise ValueError("rate_limited")

        # Check cooldown
        if await self._is_in_cooldown(normalized):
            raise ValueError("rate_limited")

        # Check if user exists with verified email
        user = await self.repo.users.get_by_verified_email(normalized)
        if not user:
            # Security: Don't reveal if email exists
            # Return fake success with dummy token (user won't receive email)
            await self._increment_email_rate_limit(normalized)
            dummy_token = secrets.token_urlsafe(32)
            logger.info(f"Password reset attempted for non-existent email {normalized[:3]}***")
            return {
                "reset_token": dummy_token,
                "expires_in": EMAIL_RESET_TTL,
            }

        # Generate token and code
        reset_token = secrets.token_urlsafe(32)
        code = self._password_service.generate_verification_code()

        # Store in Redis
        reset_data = {
            "email": normalized,
            "code": code,
            "user_id": user.id,
            "created_at": datetime.now(UTC).isoformat(),
            "attempts": 0,
        }

        redis_key = EmailRedisKeys.RESET.format(token=reset_token)
        await self.redis.set(redis_key, json.dumps(reset_data), ex=EMAIL_RESET_TTL)

        # Send reset email
        sent = await self._send_email(normalized, code, first_name=getattr(user, "display_name", None))
        if not sent:
            await self.redis.delete(redis_key)
            raise ValueError("email_send_failed")

        # Increment rate limit counter
        await self._increment_email_rate_limit(normalized)

        logger.info(f"Password reset started for {normalized[:3]}***")

        return {
            "reset_token": reset_token,
            "expires_in": EMAIL_RESET_TTL,
        }

    async def email_complete_reset(
        self,
        reset_token: str,
        code: str,
        new_password: str,
    ) -> dict[str, Any]:
        """
        Complete password reset flow.

        Verifies code and updates user password.

        Args:
            reset_token: Token from email_start_reset
            code: 6-digit verification code
            new_password: New password to set

        Returns:
            dict with success status

        Raises:
            ValueError: If token/code invalid or password weak
        """
        # Get reset data from Redis
        redis_key = EmailRedisKeys.RESET.format(token=reset_token)
        data_raw = await self.redis.get(redis_key)

        if not data_raw:
            raise ValueError("reset_token_invalid")

        reset_data = json.loads(data_raw if isinstance(data_raw, str) else data_raw.decode())
        email = reset_data["email"]
        user_id = reset_data["user_id"]

        # Check attempts
        attempts = reset_data.get("attempts", 0)
        if attempts >= EMAIL_MAX_CODE_ATTEMPTS:
            await self.redis.delete(redis_key)
            await self._set_cooldown(email)
            raise ValueError("code_invalid")

        # Verify code
        if not secrets.compare_digest(reset_data["code"], code):
            # Increment attempts
            reset_data["attempts"] = attempts + 1
            await self.redis.set(redis_key, json.dumps(reset_data), ex=EMAIL_RESET_TTL)

            if reset_data["attempts"] >= EMAIL_MAX_CODE_ATTEMPTS:
                await self.redis.delete(redis_key)
                await self._set_cooldown(email)

            raise ValueError("code_invalid")

        # Validate password
        is_valid, error_msg = self._password_service.validate_strength(new_password)
        if not is_valid:
            raise ValueError("password_too_weak")

        # Get and update user
        user = await self.repo.users.get_by_id(user_id)
        if not user:
            raise ValueError("user_not_found")

        user.password_hash = self._password_service.hash_password(new_password)

        # Flush changes to database (commit happens at dependency layer)
        await self.repo.users.session.flush()

        # Delete reset token
        await self.redis.delete(redis_key)

        # Clear login lockout so user can login immediately
        lockout_key = EmailRedisKeys.LOCKOUT_LOGIN.format(email=email)
        await self.redis.delete(lockout_key)

        # Clear rate limit counter
        rate_key = EmailRedisKeys.RATE_EMAIL.format(email=email)
        await self.redis.delete(rate_key)

        logger.info(f"Password reset completed for user_id={user_id}")

        return {
            "success": True,
        }

    # =========================================================================
    # Email auth: Resend flow
    # =========================================================================

    async def email_resend_code(
        self,
        signup_token: str | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Resend verification code.

        Args:
            signup_token: Token from signup flow (mutually exclusive with user_id)
            user_id: User ID for link flow (mutually exclusive with signup_token)

        Returns:
            dict with expires_in

        Raises:
            ValueError: If no active flow or rate limited
        """
        if signup_token:
            return await self._resend_signup_code(signup_token)
        elif user_id:
            return await self._resend_link_code(user_id)
        else:
            raise ValueError("signup_token_invalid")

    async def _resend_signup_code(self, signup_token: str) -> dict[str, Any]:
        """Resend code for signup flow."""
        redis_key = EmailRedisKeys.SIGNUP.format(token=signup_token)
        data_raw = await self.redis.get(redis_key)

        if not data_raw:
            raise ValueError("signup_token_invalid")

        signup_data = json.loads(data_raw if isinstance(data_raw, str) else data_raw.decode())
        email = signup_data["email"]

        # Check rate limit
        if not await self._check_email_rate_limit(email):
            raise ValueError("rate_limited")

        # Generate new code
        new_code = self._password_service.generate_verification_code()
        signup_data["code"] = new_code
        signup_data["attempts"] = 0  # Reset attempts on resend

        await self.redis.set(redis_key, json.dumps(signup_data), ex=EMAIL_SIGNUP_TTL)

        # Send email
        sent = await self._send_email(email, new_code)
        if not sent:
            raise ValueError("email_send_failed")

        await self._increment_email_rate_limit(email)

        return {"expires_in": EMAIL_SIGNUP_TTL}

    async def _resend_link_code(self, user_id: UUID) -> dict[str, Any]:
        """Resend code for link flow."""
        redis_key = EmailRedisKeys.LINK.format(user_id=user_id)
        data_raw = await self.redis.get(redis_key)

        if not data_raw:
            raise ValueError("code_expired")

        link_data = json.loads(data_raw if isinstance(data_raw, str) else data_raw.decode())
        email = link_data["email"]

        # Check rate limit
        if not await self._check_email_rate_limit(email):
            raise ValueError("rate_limited")

        # Get user for display_name
        user = await self.repo.users.get_by_id(user_id)

        # Generate new code
        new_code = self._password_service.generate_verification_code()
        link_data["code"] = new_code
        link_data["attempts"] = 0

        await self.redis.set(redis_key, json.dumps(link_data), ex=EMAIL_LINK_TTL)

        # Send email
        sent = await self._send_email(email, new_code, first_name=getattr(user, "display_name", None) if user else None)
        if not sent:
            raise ValueError("email_send_failed")

        await self._increment_email_rate_limit(email)

        return {"expires_in": EMAIL_LINK_TTL}

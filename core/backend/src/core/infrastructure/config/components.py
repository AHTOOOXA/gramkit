# core/backend/src/core/infrastructure/config/components.py
"""Reusable Pydantic config components.

Apps import these to build their own Settings class.
These are BaseModel (NOT BaseSettings) - the parent Settings class handles
env var loading. Components just define the shape of nested config objects.
"""

from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    """Database connection settings.

    Env vars: DB__HOST, DB__PORT, DB__USER, DB__PASSWORD, DB__NAME
    """

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    name: str = "app"

    @property
    def url(self) -> str:
        """Async database URL for SQLAlchemy."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        """Sync database URL for migrations."""
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseModel):
    """Redis connection settings.

    Env vars: REDIS__HOST, REDIS__PORT, REDIS__PASSWORD
    """

    host: str = "localhost"
    port: int = 6379
    password: str = ""

    @property
    def url(self) -> str:
        """Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/0"
        return f"redis://{self.host}:{self.port}/0"


class RabbitSettings(BaseModel):
    """RabbitMQ connection settings.

    Env vars: RABBIT__URL, RABBIT__QUEUE_NAME
    """

    url: str = "amqp://guest:guest@localhost:5672/"
    queue_name: str = "default"


class SessionSettings(BaseModel):
    """Session and cookie settings.

    Env vars: SESSION__EXPIRE_DAYS, SESSION__COOKIE_SECURE, etc.

    Note: cookie_name and key_prefix are derived from app_name
    and should be set in model_post_init of the root Settings.
    """

    expire_days: int = 7
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None  # e.g., ".example.com" for cross-subdomain cookies
    # Derived fields - set by root Settings
    cookie_name: str = ""
    key_prefix: str = ""


class BotSettings(BaseModel):
    """Telegram bot settings.

    Env vars: BOT__TOKEN, BOT__URL
    """

    token: str = ""
    url: str = ""  # t.me/BotName


class WebSettings(BaseModel):
    """Web application settings.

    Env vars: WEB__APP_URL, WEB__FRONTEND_URL, WEB__API_URL, WEB__API_ROOT_PATH, WEB__CORS_ORIGINS, WEB__SHUTDOWN_DRAIN_TIMEOUT
    """

    app_url: str = ""  # Mini app URL
    frontend_url: str = ""  # Frontend domain
    api_url: str = ""  # API domain
    api_root_path: str = ""  # FastAPI root path for reverse proxy
    cors_origins: list[str] = []  # Extra CORS origins (for local dev localhost access)
    shutdown_drain_timeout: int = 30  # Seconds to wait for active requests to complete during shutdown


class PaymentSettings(BaseModel):
    """Payment provider settings (YooKassa).

    Env vars: PAYMENT__SHOP_ID, PAYMENT__SECRET_KEY, PAYMENT__RECEIPT_EMAIL
    """

    shop_id: str = ""
    secret_key: str = ""
    receipt_email: str = ""

    @property
    def enabled(self) -> bool:
        """Check if payment is configured."""
        return bool(self.shop_id and self.secret_key)


class EmailSettings(BaseModel):
    """Email provider settings (Resend).

    Env vars: EMAIL__API_KEY, EMAIL__FROM_ADDRESS, EMAIL__FROM_NAME
    """

    api_key: str = ""
    from_address: str = ""
    from_name: str = ""

    @property
    def enabled(self) -> bool:
        """Check if email is configured."""
        return bool(self.api_key and self.from_address)


class OpenAISettings(BaseModel):
    """OpenAI API settings.

    Env vars: OPENAI__API_KEY
    """

    api_key: str = ""

    @property
    def enabled(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.api_key)


class ObservabilitySettings(BaseModel):
    """Observability services settings (Sentry, PostHog, Logfire).

    Env vars: OBSERVABILITY__SENTRY_DSN, OBSERVABILITY__POSTHOG_API_KEY, OBSERVABILITY__POSTHOG_HOST,
              OBSERVABILITY__LOGFIRE_TOKEN, OBSERVABILITY__LOGFIRE_ENVIRONMENT
    """

    sentry_dsn: str = ""
    posthog_api_key: str = ""
    posthog_host: str = "https://app.posthog.com"
    logfire_token: str = ""
    logfire_environment: str = "development"

    @property
    def sentry_enabled(self) -> bool:
        return bool(self.sentry_dsn)

    @property
    def posthog_enabled(self) -> bool:
        return bool(self.posthog_api_key)

    @property
    def logfire_enabled(self) -> bool:
        return bool(self.logfire_token)


class RBACSettings(BaseModel):
    """Role-based access control settings.

    Env vars: RBAC__OWNER_IDS
    """

    owner_ids: list[int] = []  # Telegram IDs that are always treated as owner

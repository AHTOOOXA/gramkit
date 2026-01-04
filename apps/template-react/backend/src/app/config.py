"""Template Vue app configuration.

Usage:
    from core.infrastructure.config import settings

    settings.db.url
    settings.session.cookie_name
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from core.infrastructure.config import (
    BotSettings,
    DatabaseSettings,
    EmailSettings,
    ObservabilitySettings,
    OpenAISettings,
    PaymentSettings,
    RabbitSettings,
    RBACSettings,
    RedisSettings,
    SessionSettings,
    WebSettings,
)

# Determine .env file to use (support ENV_FILE for tests)
_ENV_FILE = os.getenv("ENV_FILE", ".env")
_ENV_PATH = (Path(__file__).parent.parent.parent / _ENV_FILE).resolve()


class Settings(BaseSettings):
    """Template Vue application settings."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",  # DB__HOST -> db.host (double underscore)
    )

    # App identity
    app_name: str = "template"
    debug: bool = False
    debug_username: str = ""

    # Infrastructure (using nested delimiter: DB_HOST, REDIS_HOST, etc.)
    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    rabbit: RabbitSettings = RabbitSettings()

    # Auth & sessions (BOT_TOKEN, SESSION_EXPIRE_DAYS, etc.)
    session: SessionSettings = SessionSettings()
    bot: BotSettings = BotSettings()

    # Web (WEB_APP_URL, etc.)
    web: WebSettings = WebSettings()

    # Services (PAYMENT_SHOP_ID, EMAIL_API_KEY, etc.)
    payment: PaymentSettings = PaymentSettings()
    email: EmailSettings = EmailSettings()
    openai: OpenAISettings = OpenAISettings()

    # Observability
    observability: ObservabilitySettings = ObservabilitySettings()

    # RBAC
    rbac: RBACSettings = RBACSettings()

    def model_post_init(self, __context) -> None:
        """Derive app-specific values."""
        # Session cookie and Redis key use app name
        object.__setattr__(self.session, "cookie_name", f"{self.app_name}_session")
        object.__setattr__(self.session, "key_prefix", f"{self.app_name}:session:")


# Singleton instance
settings = Settings()

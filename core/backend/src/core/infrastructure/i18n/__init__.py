import json
from collections.abc import Callable
from contextvars import ContextVar
from pathlib import Path

from core.schemas.users import UserSchema

# Core locales directory
CORE_LOCALES_DIR = Path(__file__).parent / "locales"

_translations: dict[str, dict[str, str]] = {}
_app_locales_dir: Path | None = None

current_i18n = ContextVar("current_i18n", default=None)


class I18nManager:
    def __init__(self):
        self._t: Callable | None = None

    def set_translation(self, t: Callable):
        self._t = t
        current_i18n.set(self)

    def reset_translation(self):
        current_i18n.set(None)
        self._t = None

    def update_locale(self, locale: str):
        self.set_translation(lambda key, *args, **kwargs: get_translation(key, locale))

    def __call__(self, key: str, *args, **kwargs) -> str:
        if self._t is None:
            if kwargs.get("locale"):
                return get_translation(key, kwargs["locale"])
            raise RuntimeError("Translation function not set")
        return self._t(key, *args, **kwargs)

    def set_user_locale(self, user: UserSchema | None):
        lang = "en"
        if user:
            lang = user.language_code or user.tg_language_code or "en"
        self.update_locale(lang)


i18n = I18nManager()


def deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge two dictionaries. Overlay values take precedence."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def init_i18n(app_locales_dir: Path | None = None):
    """
    Initialize i18n system with core translations and optional app translations.

    Args:
        app_locales_dir: Path to app-specific locales directory.
                        App translations are merged with core translations.
                        App translations take precedence for duplicate keys.

    Example:
        # In app initialization
        from pathlib import Path
        from core.infrastructure.i18n import init_i18n

        init_i18n(Path(__file__).parent / "i18n" / "locales")
    """
    global _app_locales_dir
    _app_locales_dir = app_locales_dir
    _translations.clear()  # Clear cache to force reload
    load_translations()


def load_translations():
    """Load translations from core and app directories."""
    # Load core translations
    for file in CORE_LOCALES_DIR.glob("*.json"):
        locale = file.stem
        with open(file, encoding="utf-8") as f:
            _translations[locale] = json.load(f)

    # Load and merge app translations if configured
    if _app_locales_dir and _app_locales_dir.exists():
        for file in _app_locales_dir.glob("*.json"):
            locale = file.stem
            with open(file, encoding="utf-8") as f:
                app_translations = json.load(f)
                if locale in _translations:
                    _translations[locale] = deep_merge(_translations[locale], app_translations)
                else:
                    _translations[locale] = app_translations


def get_translation(key: str, locale: str = "en") -> str:
    """
    Get translation by namespaced key.

    Examples:
        get_translation("core.user.welcome", "en")  # → "Welcome!"
        get_translation("tarot.cards.00.name", "en")  # → "The Fool"
    """
    if not _translations:
        load_translations()

    # Handle nested keys like "core.user.welcome" or "tarot.spreads.daily.request"
    keys = key.split(".")
    value = _translations.get(locale, {})
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k, key)
        else:
            return key
    return value if value is not None else key


def t(key: str, locale: str | None = None, **kwargs) -> str:
    """
    Get translation by namespaced key with optional variable interpolation.

    Args:
        key: Namespaced translation key (e.g., "core.user.welcome", "tarot.welcome")
        locale: Target locale (defaults to "en")
        **kwargs: Variables for string formatting

    Examples:
        t("core.user.welcome")  # → "Welcome!"
        t("tarot.welcome_extra_friendly", user_count=1000)  # → "✨ You are our 1000 user..."
    """
    translation = get_translation(key, locale or "en")

    # Apply string formatting if kwargs provided
    if kwargs:
        try:
            return translation.format(**kwargs)
        except (KeyError, ValueError):
            # Return raw translation if formatting fails
            return translation

    return translation

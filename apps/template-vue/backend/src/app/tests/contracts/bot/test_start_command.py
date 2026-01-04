"""
Contract tests for /start command handler.

Tests cover:
- Start command invocation
- Referral handling via deep links
- User creation through bot
"""

import pytest


@pytest.mark.contract
class TestStartCommandHandler:
    """Tests for /start command handler."""

    def test_start_handler_is_configured(self):
        """Start handler is registered in router."""
        from app.tgbot.handlers.start import router

        # Router should have registered handlers
        assert len(router.message.handlers) > 0

    def test_ref_handler_is_configured(self):
        """Ref handler is registered in router."""
        from app.tgbot.handlers.start import router

        # Should have at least 2 handlers (start + ref)
        assert len(router.message.handlers) >= 2


@pytest.mark.contract
class TestStartHandlerPartial:
    """Tests for start handler partial configuration."""

    def test_start_handler_has_menu_key(self):
        """Start handler is configured with menu i18n key."""
        from app.tgbot.handlers.start import tarot_start_handler

        # The partial function should have keywords set
        assert tarot_start_handler.keywords.get("menu_i18n_key") is not None

    def test_start_handler_has_keyboard_factory(self):
        """Start handler is configured with keyboard factory."""
        from app.tgbot.handlers.start import tarot_start_handler

        assert tarot_start_handler.keywords.get("keyboard_factory") is not None

    def test_start_handler_has_posthog_event(self):
        """Start handler is configured with PostHog event."""
        from app.tgbot.handlers.start import tarot_start_handler

        assert tarot_start_handler.keywords.get("posthog_event") is not None


@pytest.mark.contract
class TestRefHandlerPartial:
    """Tests for ref handler partial configuration."""

    def test_ref_handler_has_bot_url(self):
        """Ref handler is configured with bot URL."""
        from app.tgbot.handlers.start import tarot_ref_handler

        assert tarot_ref_handler.keywords.get("bot_url") is not None

    def test_ref_handler_has_web_app_path(self):
        """Ref handler is configured with web app path."""
        from app.tgbot.handlers.start import tarot_ref_handler

        assert tarot_ref_handler.keywords.get("web_app_path") is not None

    def test_ref_handler_has_referral_prefix(self):
        """Ref handler is configured with referral prefix."""
        from app.tgbot.handlers.start import tarot_ref_handler

        prefix = tarot_ref_handler.keywords.get("referral_prefix")
        assert prefix is not None
        assert prefix.startswith("r-")

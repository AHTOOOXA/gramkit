"""
Script runner entry point for template app.

Usage:
    python -m app.scripts <script_name> [args...]
    make script name=demo_user_stats APP=template

Example:
    python -m app.scripts demo_user_stats
"""

if __name__ == "__main__":
    from core.infrastructure.config import settings
    from core.infrastructure.database.setup import create_engine, create_session_pool
    from core.scripts.runner import ScriptRunner

    runner = ScriptRunner(
        db_config=settings.db,
        redis_config=settings.redis,
        rabbit_config=settings.rabbit,
        tgbot_config=settings.bot,
        sentry_config=settings.observability.sentry,
        posthog_config=settings.observability.posthog,
        create_engine_fn=create_engine,
        create_session_pool_fn=create_session_pool,
        scripts_module_prefix="app.scripts",
        app_name="template",
    )

    runner.main()

#!/usr/bin/env python3
"""
Generic script runner with full infrastructure setup.
Provides complete access to database, redis, rabbitmq, bot, and all services.

This is a generic implementation that can be configured for different apps.
Apps should create their own runner that uses this class with app-specific configuration.

Usage:
    python -m app.scripts.runner <script_name> [args...]

Example:
    python -m app.scripts.runner migrate_questions
    python -m app.scripts.runner cleanup_old_data --days 30
"""

import argparse
import asyncio
import importlib
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import sentry_sdk
import uvloop
from aiogram import Bot
from arq import create_pool
from arq.connections import RedisSettings
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from core.infrastructure.logging import get_logger, setup_logging
from core.infrastructure.posthog import setup_posthog
from core.infrastructure.rabbit.producer import RabbitMQProducer
from core.infrastructure.redis import RedisClient
from core.scripts.base import BaseScript

# Note: setup_logging() and setup_posthog() are now called in ScriptRunner.__init__
# This allows each app to pass its own configuration

logger = get_logger(__name__)


class ScriptRunner:
    """Generic script runner that can be configured for different apps"""

    def __init__(
        self,
        *,
        db_config: Any,
        redis_config: Any,
        rabbit_config: Any,
        tgbot_config: Any,
        sentry_config: Any,
        posthog_config: Any,
        create_engine_fn: Callable,
        create_session_pool_fn: Callable,
        scripts_module_prefix: str = "app.scripts",
        app_name: str = "App",
    ):
        """Initialize script runner with app-specific configuration

        Args:
            db_config: Database configuration object
            redis_config: Redis configuration object
            rabbit_config: RabbitMQ configuration object
            tgbot_config: Telegram bot configuration object
            sentry_config: Sentry configuration object
            posthog_config: PostHog analytics configuration object
            create_engine_fn: Function to create database engine
            create_session_pool_fn: Function to create session pool
            scripts_module_prefix: Module prefix for loading scripts (e.g., "app.scripts")
            app_name: Application name for logging
        """
        # Setup logging first
        setup_logging()

        self.db_config = db_config
        self.redis_config = redis_config
        self.rabbit_config = rabbit_config
        self.tgbot_config = tgbot_config
        self.sentry_config = sentry_config
        self.posthog_config = posthog_config
        self.create_engine_fn = create_engine_fn
        self.create_session_pool_fn = create_session_pool_fn
        self.scripts_module_prefix = scripts_module_prefix
        self.app_name = app_name

        self._setup_sentry()
        self._setup_posthog()

    def _setup_sentry(self):
        """Setup Sentry monitoring"""
        try:
            from importlib.metadata import PackageNotFoundError, version

            release_version = version(self.app_name)
        except PackageNotFoundError:
            release_version = "unknown"
            logger.warning("Unable to determine package version")

        if self.sentry_config.dsn:
            sentry_sdk.init(
                dsn=self.sentry_config.dsn,
                send_default_pii=True,
                traces_sample_rate=1.0,
                profiles_sample_rate=1.0,
                integrations=[SqlalchemyIntegration()],
                release=release_version,
            )

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    def _setup_posthog(self):
        """Setup PostHog analytics"""
        if self.posthog_config.api_key and self.posthog_config.host:
            try:
                setup_posthog(self.posthog_config.api_key, self.posthog_config.host)
                logger.info("PostHog analytics initialized")
            except Exception as e:
                logger.warning(f"PostHog setup failed (continuing without analytics): {e}")

    async def setup_infrastructure(self) -> dict[str, Any]:
        """Initialize all infrastructure connections"""
        logger.info("Setting up infrastructure...")

        ctx = {
            "db_config": self.db_config,
            "app_name": self.app_name,
            "logger": logger,
        }

        try:
            ctx["bot"] = Bot(token=self.tgbot_config.token)
            logger.info("Bot initialized")

            ctx["redis"] = RedisClient(self.redis_config)
            logger.info("Redis client initialized")

            # RabbitMQ is optional - don't fail if it can't connect
            try:
                ctx["producer"] = RabbitMQProducer(self.rabbit_config)
                await ctx["producer"].connect()
                logger.info("RabbitMQ producer connected")
            except Exception as e:
                logger.warning(f"RabbitMQ connection failed (will continue without it): {e}")
                ctx["producer"] = None

            ctx["arq"] = await create_pool(
                RedisSettings(
                    host=self.redis_config.host,
                    port=self.redis_config.port,
                    password=self.redis_config.password or None,
                )
            )
            logger.info("ARQ pool created")

            engine = self.create_engine_fn(self.db_config)
            ctx["engine"] = engine
            ctx["session_pool"] = self.create_session_pool_fn(engine)
            logger.info("Database session pool created")

            logger.info("All infrastructure initialized successfully")
            return ctx

        except Exception as e:
            logger.error(f"Failed to setup infrastructure: {e}")
            await self.teardown_infrastructure(ctx)
            raise

    async def teardown_infrastructure(self, ctx: dict[str, Any]):
        """Clean up all infrastructure connections"""
        logger.info("Tearing down infrastructure...")

        if "bot" in ctx:
            await ctx["bot"].session.close()
            logger.info("Bot session closed")

        if "redis" in ctx:
            await ctx["redis"].close()
            logger.info("Redis client closed")

        if "producer" in ctx and ctx["producer"]:
            await ctx["producer"].close()
            logger.info("RabbitMQ producer closed")

        if "arq" in ctx:
            await ctx["arq"].aclose()
            logger.info("ARQ pool closed")

        if "engine" in ctx:
            await ctx["engine"].dispose()
            logger.info("Database engine disposed")

        logger.info("Infrastructure teardown complete")

    def load_script(self, script_name: str):
        """Dynamically load a script class from app or core.scripts.common"""
        # Try app scripts first
        try:
            module_path = f"{self.scripts_module_prefix}.{script_name}"
            module = importlib.import_module(module_path)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr is not BaseScript:
                    # Only consider classes defined in this module (not imported)
                    if attr.__module__ == module.__name__:
                        # Accept any class that looks like a script (has execute method)
                        if hasattr(attr, "execute") or hasattr(attr, "run"):
                            return attr

        except ImportError:
            pass  # Try core scripts next

        # Try core common scripts
        try:
            module_path = f"core.scripts.common.{script_name}"
            module = importlib.import_module(module_path)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type):
                    # Only consider classes defined in this module (not imported)
                    if attr.__module__ == module.__name__:
                        # Accept any class that looks like a script
                        if hasattr(attr, "execute") or hasattr(attr, "run"):
                            return attr

        except ImportError:
            pass

        # Script not found in either location
        logger.error(f"Failed to load script '{script_name}'")

        # Try to find available scripts
        available = []
        try:
            scripts_module = importlib.import_module(self.scripts_module_prefix)
            scripts_dir = Path(scripts_module.__file__).parent
            available.extend(
                [f.stem for f in scripts_dir.glob("*.py") if f.stem not in ["__init__", "base", "runner", "__main__"]]
            )
        except Exception:
            pass

        try:
            common_module = importlib.import_module("core.scripts.common")
            common_dir = Path(common_module.__file__).parent
            available.extend([f.stem for f in common_dir.glob("*.py") if f.stem not in ["__init__"]])
        except Exception:
            pass

        if available:
            logger.info(f"Available scripts: {', '.join(sorted(set(available)))}")
        else:
            logger.info("No scripts found")

        raise ImportError(f"Script '{script_name}' not found")

    async def run_script(self, script_name: str, args: list):
        """Execute a script with full infrastructure"""
        ctx = None

        try:
            ctx = await self.setup_infrastructure()

            script_class = self.load_script(script_name)
            script = script_class(ctx)

            logger.info(f"Executing script: {script_name}")
            result = await script.execute(*args)

            if result is not None:
                logger.info(f"Script result: {result}")

            return result

        except Exception as e:
            logger.error(f"Script execution failed: {e}", exc_info=True)
            sys.exit(1)

        finally:
            if ctx:
                await self.teardown_infrastructure(ctx)

    def main(self):
        """Main entry point for script runner"""
        parser = argparse.ArgumentParser(description="Run scripts with full infrastructure access")
        parser.add_argument("script", help="Name of the script to run (without .py extension)")
        parser.add_argument("args", nargs="*", help="Additional arguments to pass to the script")

        args = parser.parse_args()

        asyncio.run(self.run_script(args.script, args.args))

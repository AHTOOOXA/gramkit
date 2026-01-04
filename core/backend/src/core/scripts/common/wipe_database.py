"""
Wipe all data from database tables and Redis cache (reset to fresh state).

Common script available to all apps.

⚠️  WARNING: This deletes ALL data from ALL tables and Redis!
⚠️  Always create a backup first with: make script name=backup_database

Usage:
    make script name=wipe_database APP=template
    make script name=wipe_database APP=tarot
    make script name=wipe_database APP=template-react
"""

from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.infrastructure.redis import RedisClient


class WipeDatabaseScript:
    """Wipe all data from database tables and Redis cache"""

    def __init__(self, ctx):
        self.ctx = ctx
        self.logger = ctx.get("logger")
        self.session_pool: async_sessionmaker[AsyncSession] = ctx["session_pool"]
        self.redis: RedisClient = ctx["redis"]

        # Fallback logger if not in context
        if not self.logger:
            from core.infrastructure.logging import get_logger

            self.logger = get_logger(self.__class__.__name__)

    @asynccontextmanager
    async def with_session(self):
        """Context manager for database session"""
        async with self.session_pool() as session:
            yield session

    async def execute(self, *args, **kwargs):
        """Execute wrapper for runner compatibility"""
        return await self.run(*args, **kwargs)

    async def run(self):
        """Delete all data from all tables"""

        self.logger.warning("=" * 60)
        self.logger.warning("⚠️  WARNING: This will DELETE ALL DATA!")
        self.logger.warning("⚠️  Make sure you have a backup!")
        self.logger.warning("=" * 60)

        async with self.with_session() as session:
            # Get list of all tables (excluding alembic_version)
            result = await session.execute(
                text("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename != 'alembic_version'
                ORDER BY tablename
            """)
            )
            tables = [row[0] for row in result.fetchall()]

            if not tables:
                self.logger.warning("⚠️  No database tables found to wipe")
            else:
                self.logger.info(f"📋 Found {len(tables)} tables to wipe:")
                for table in tables:
                    self.logger.info(f"   - {table}")

                self.logger.info("")
                self.logger.info("🔄 Starting data deletion...")

                # Disable foreign key checks temporarily and truncate all tables
                await session.execute(text("SET CONSTRAINTS ALL DEFERRED"))

                for table in tables:
                    try:
                        # TRUNCATE is faster than DELETE and resets sequences
                        await session.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))
                        self.logger.info(f"✅ Wiped: {table}")
                    except Exception as e:
                        self.logger.error(f"❌ Failed to wipe {table}: {e}")
                        raise

                # Commit the transaction
                await session.commit()

                self.logger.info("")
                self.logger.info("✅ Database tables wiped successfully!")
                self.logger.info(f"📊 Tables affected: {len(tables)}")

        # Wipe Redis cache
        self.logger.info("")
        self.logger.info("🔄 Wiping Redis cache...")
        await self.redis.flushdb()
        self.logger.info("✅ Redis cache wiped successfully!")

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("✅ Full wipe completed!")
        self.logger.info(f"📊 Database tables: {len(tables)}")
        self.logger.info("📊 Redis: flushed")
        self.logger.info("🆕 System is now in fresh state")
        self.logger.info("=" * 60)

        return {
            "success": True,
            "tables_wiped": len(tables),
            "tables": tables,
            "redis_flushed": True,
        }

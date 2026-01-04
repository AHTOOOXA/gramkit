"""
Create a database backup using pg_dump.

Common script available to all apps.

Usage:
    make script name=backup_database APP=tarot
    make script name=backup_database args='--no-compress' APP=tarot
    make script name=backup_database args='--name=before_migration' APP=tarot
"""

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BackupResult:
    """Result of a database backup operation."""

    success: bool
    file_path: str
    size_bytes: int
    duration_seconds: float
    tables_count: int
    timestamp: datetime
    compressed: bool
    app_name: str
    error: str | None = None

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024

    @property
    def size_display(self) -> str:
        """Human-readable size (KB for small files, MB for larger)."""
        if self.size_bytes < 1024 * 100:  # < 100 KB
            return f"{self.size_kb:.1f} KB"
        else:
            return f"{self.size_mb:.2f} MB"

    @property
    def filename(self) -> str:
        return Path(self.file_path).name


async def create_backup(
    db_config,
    app_name: str,
    compress: bool = True,
    backup_name: str | None = None,
    output_dir: str = "/tmp",
) -> BackupResult:
    """
    Create database backup using pg_dump.

    This is the core backup function used by both CLI scripts and worker jobs.

    Args:
        db_config: Database configuration with host, port, user, password, name
        app_name: Application name (used for container name: {app_name}-pg)
        compress: Whether to gzip the output (default True)
        backup_name: Optional custom backup name (default: auto-generated timestamp)
        output_dir: Directory to store backup (default: /tmp)

    Returns:
        BackupResult with success status and metadata
    """
    start_time = time.time()
    timestamp = datetime.now(UTC)
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

    # Generate filename
    if not backup_name:
        backup_name = f"{app_name}_{timestamp_str}"

    ext = ".sql.gz" if compress else ".sql"
    backup_file = str(Path(output_dir) / f"{backup_name}{ext}")

    # Build pg_dump command using network connection
    # PGPASSWORD env var is used for authentication
    env_prefix = f"PGPASSWORD={db_config.password}"
    pg_dump_cmd = (
        f"{env_prefix} pg_dump "
        f"-h {db_config.host} -p {db_config.port} "
        f"-U {db_config.user} -d {db_config.name} "
        f"--clean --if-exists"
    )

    if compress:
        # Pipe through gzip
        cmd = f"{pg_dump_cmd} | gzip > {backup_file}"
    else:
        cmd = f"{pg_dump_cmd} > {backup_file}"

    # Execute backup
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    duration = time.time() - start_time

    # Check for errors
    if proc.returncode != 0:
        error_msg = stderr.decode().strip() if stderr else "Unknown error"
        return BackupResult(
            success=False,
            file_path=backup_file,
            size_bytes=0,
            duration_seconds=duration,
            tables_count=0,
            timestamp=timestamp,
            compressed=compress,
            app_name=app_name,
            error=error_msg,
        )

    # Get file size
    file_size = os.path.getsize(backup_file) if os.path.exists(backup_file) else 0

    # Count tables (rough estimate from backup)
    tables_count = await _count_tables_in_backup(backup_file, compress)

    return BackupResult(
        success=True,
        file_path=backup_file,
        size_bytes=file_size,
        duration_seconds=duration,
        tables_count=tables_count,
        timestamp=timestamp,
        compressed=compress,
        app_name=app_name,
    )


async def _count_tables_in_backup(backup_file: str, compressed: bool) -> int:
    """Count CREATE TABLE statements in backup to estimate table count."""
    try:
        if compressed:
            cmd = f"zcat {backup_file} | grep -c 'CREATE TABLE' || true"
        else:
            cmd = f"grep -c 'CREATE TABLE' {backup_file} || true"

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return int(stdout.decode().strip() or 0)
    except Exception:
        return 0


class BackupDatabaseScript:
    """Create database backup and optionally send to Telegram."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.logger = ctx.get("logger")
        self.db_config = ctx["db_config"]
        self.app_name = ctx.get("app_name", "app")
        self.bot = ctx.get("bot")

        # Fallback logger if not in context
        if not self.logger:
            from core.infrastructure.logging import get_logger

            self.logger = get_logger(self.__class__.__name__)

    async def execute(self, *args, **kwargs):
        """Execute wrapper for runner compatibility."""
        return await self.run(*args, **kwargs)

    async def run(
        self,
        backup_name: str | None = None,
        compress: str = "true",
        send_telegram: str = "false",
    ):
        """
        Create database backup.

        Args:
            backup_name: Optional custom name for backup file
            compress: "true" or "false" - whether to gzip (default: true)
            send_telegram: "true" or "false" - send to bot owners (default: false)
        """
        # Parse string args to bool (CLI passes strings)
        do_compress = compress.lower() != "false" and compress.lower() != "no"
        do_send_telegram = send_telegram.lower() in ("true", "yes", "1")

        self.logger.info("=" * 60)
        self.logger.info(f"Creating database backup for {self.app_name}...")
        self.logger.info("=" * 60)

        result = await create_backup(
            db_config=self.db_config,
            app_name=self.app_name,
            compress=do_compress,
            backup_name=backup_name,
        )

        if not result.success:
            self.logger.error(f"Backup failed: {result.error}")
            return {"success": False, "error": result.error}

        self.logger.info("")
        self.logger.info("Backup created successfully!")
        self.logger.info(f"  File: {result.file_path}")
        self.logger.info(f"  Size: {result.size_mb:.2f} MB")
        self.logger.info(f"  Tables: {result.tables_count}")
        self.logger.info(f"  Duration: {result.duration_seconds:.1f}s")
        self.logger.info(f"  Compressed: {result.compressed}")

        # Optional: send to Telegram
        if do_send_telegram and self.bot:
            await self._send_to_telegram(result)

        self.logger.info("")
        self.logger.info("=" * 60)

        return {
            "success": True,
            "file_path": result.file_path,
            "size_mb": result.size_mb,
            "tables_count": result.tables_count,
            "duration_seconds": result.duration_seconds,
        }

    async def _send_to_telegram(self, result: BackupResult):
        """Send backup file to bot owners via Telegram."""
        try:
            from aiogram.types import FSInputFile

            from core.infrastructure.config import settings

            owner_ids = getattr(settings.rbac, "owner_ids", [])
            if not owner_ids:
                self.logger.warning("No owner_ids configured, skipping Telegram send")
                return

            caption = (
                f"Database Backup\n"
                f"App: {result.app_name}\n"
                f"Size: {result.size_mb:.2f} MB\n"
                f"Tables: {result.tables_count}\n"
                f"Time: {result.duration_seconds:.1f}s"
            )

            document = FSInputFile(result.file_path)

            for owner_id in owner_ids:
                try:
                    await self.bot.send_document(
                        chat_id=owner_id,
                        document=document,
                        caption=caption,
                    )
                    self.logger.info(f"Backup sent to Telegram user {owner_id}")
                except Exception as e:
                    self.logger.error(f"Failed to send to {owner_id}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to send backup to Telegram: {e}")

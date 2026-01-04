"""
Restore database from a backup file.

Common script available to all apps.

Usage:
    make script name=restore_database args='/tmp/tarot_20231124.sql.gz' APP=tarot
    make script name=restore_database args='/tmp/backup.sql --confirm' APP=tarot
"""

import asyncio
import os
import time
from dataclasses import dataclass


@dataclass
class RestoreResult:
    """Result of a database restore operation."""

    success: bool
    backup_file: str
    duration_seconds: float
    app_name: str
    error: str | None = None


async def restore_backup(
    db_config,
    app_name: str,
    backup_file: str,
) -> RestoreResult:
    """
    Restore database from backup file.

    This is the core restore function used by both CLI scripts and worker jobs.

    Args:
        db_config: Database configuration with host, port, user, password, name
        app_name: Application name (used for container name: {app_name}-pg)
        backup_file: Path to backup file (.sql, .sql.gz, or .dump)

    Returns:
        RestoreResult with success status
    """
    start_time = time.time()

    if not os.path.exists(backup_file):
        return RestoreResult(
            success=False,
            backup_file=backup_file,
            duration_seconds=0,
            app_name=app_name,
            error=f"Backup file not found: {backup_file}",
        )

    # Build restore command using network connection
    # PGPASSWORD env var is used for authentication
    env_prefix = f"PGPASSWORD={db_config.password}"
    psql_base = f"{env_prefix} psql -h {db_config.host} -p {db_config.port} -U {db_config.user} -d {db_config.name}"
    pg_restore_base = (
        f"{env_prefix} pg_restore -h {db_config.host} -p {db_config.port} -U {db_config.user} -d {db_config.name}"
    )

    # Build restore command based on file extension
    if backup_file.endswith(".sql.gz"):
        # Compressed SQL: gunzip and pipe to psql
        cmd = f"gunzip -c {backup_file} | {psql_base}"
    elif backup_file.endswith(".sql"):
        # Plain SQL: pipe to psql
        cmd = f"cat {backup_file} | {psql_base}"
    elif backup_file.endswith(".dump"):
        # Custom format: use pg_restore
        cmd = f"cat {backup_file} | {pg_restore_base} --clean --if-exists"
    else:
        return RestoreResult(
            success=False,
            backup_file=backup_file,
            duration_seconds=0,
            app_name=app_name,
            error="Unknown backup format. Supported: .sql, .sql.gz, .dump",
        )

    # Execute restore
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    duration = time.time() - start_time

    # Note: psql returns 0 even with some errors (like "relation already exists")
    # We check stderr for actual errors
    stderr_text = stderr.decode().strip() if stderr else ""

    # Filter out common non-error messages
    error_lines = [
        line
        for line in stderr_text.split("\n")
        if line
        and not any(
            x in line.lower()
            for x in [
                "notice:",
                "dropping",
                "does not exist, skipping",
            ]
        )
    ]

    if proc.returncode != 0 and error_lines:
        return RestoreResult(
            success=False,
            backup_file=backup_file,
            duration_seconds=duration,
            app_name=app_name,
            error="\n".join(error_lines[:5]),  # First 5 error lines
        )

    return RestoreResult(
        success=True,
        backup_file=backup_file,
        duration_seconds=duration,
        app_name=app_name,
    )


class RestoreDatabaseScript:
    """Restore database from backup file."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.logger = ctx.get("logger")
        self.db_config = ctx["db_config"]
        self.app_name = ctx.get("app_name", "app")

        # Fallback logger if not in context
        if not self.logger:
            from core.infrastructure.logging import get_logger

            self.logger = get_logger(self.__class__.__name__)

    async def execute(self, *args, **kwargs):
        """Execute wrapper for runner compatibility."""
        return await self.run(*args, **kwargs)

    async def run(
        self,
        backup_file: str = "",
        confirm: str = "false",
    ):
        """
        Restore database from backup.

        Args:
            backup_file: Path to backup file (.sql, .sql.gz, or .dump)
            confirm: "true" or "--confirm" to actually execute (safety check)
        """
        if not backup_file:
            self.logger.error("Usage: make script name=restore_database args='<backup_file> --confirm' APP=tarot")
            self.logger.error("")
            self.logger.error("Examples:")
            self.logger.error(
                "  make script name=restore_database args='/tmp/tarot_20231124.sql.gz --confirm' APP=tarot"
            )
            self.logger.error("  make script name=restore_database args='/tmp/backup.sql --confirm' APP=tarot")
            return {"success": False, "error": "backup_file is required"}

        # Parse confirm flag
        do_confirm = confirm.lower() in ("true", "yes", "1", "--confirm")

        # Check if file exists first
        if not os.path.exists(backup_file):
            self.logger.error(f"Backup file not found: {backup_file}")
            return {"success": False, "error": f"File not found: {backup_file}"}

        # Get file size for display
        file_size_mb = os.path.getsize(backup_file) / (1024 * 1024)

        self.logger.info("=" * 60)
        self.logger.warning("DATABASE RESTORE")
        self.logger.info("=" * 60)
        self.logger.info("")
        self.logger.info(f"  App: {self.app_name}")
        self.logger.info(f"  File: {backup_file}")
        self.logger.info(f"  Size: {file_size_mb:.2f} MB")
        self.logger.info("")

        if not do_confirm:
            self.logger.warning("This will REPLACE ALL DATA in the database!")
            self.logger.warning("")
            self.logger.warning("To proceed, run with --confirm:")
            self.logger.warning(
                f"  make script name=restore_database args='{backup_file} --confirm' APP={self.app_name}"
            )
            self.logger.info("")
            self.logger.info("=" * 60)
            return {"success": False, "reason": "confirmation_required"}

        self.logger.warning("RESTORING DATABASE - THIS WILL OVERWRITE ALL DATA!")
        self.logger.info("")
        self.logger.info("Restoring...")

        result = await restore_backup(
            db_config=self.db_config,
            app_name=self.app_name,
            backup_file=backup_file,
        )

        if not result.success:
            self.logger.error(f"Restore failed: {result.error}")
            return {"success": False, "error": result.error}

        self.logger.info("")
        self.logger.info("Restore completed successfully!")
        self.logger.info(f"  Duration: {result.duration_seconds:.1f}s")
        self.logger.info("")
        self.logger.info("=" * 60)

        return {
            "success": True,
            "backup_file": backup_file,
            "duration_seconds": result.duration_seconds,
        }

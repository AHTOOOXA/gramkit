"""
Restore database from a backup file.

Common script available to all apps.

Robust restore for the common "older dump -> more-migrated local DB" case
(e.g. installing a prod backup onto a dev box whose code has newer migrations):

  1. Pre-create any roles the dump references via OWNER TO / GRANT that are
     missing on the local cluster. Prod dumps carry an owner role (e.g.
     "magician-scam-flower") that a fresh local cluster doesn't have, and the
     load aborts on the first ownership statement otherwise.
  2. Recreate the target database from scratch (terminate connections +
     DROP DATABASE WITH FORCE + CREATE DATABASE). This is what makes the
     migration mismatch SAFE: a plain `pg_dump --clean` reload only drops the
     objects the dump knows about, so tables created by migrations newer than
     the dump survive, while `alembic_version` is reset backwards -- then the
     next `alembic upgrade head` tries to re-create those tables and fails with
     "relation already exists". Wiping first guarantees the DB lands EXACTLY at
     the dump's revision with nothing newer left behind.
  3. Strip psql directives that newer pg_dump (>=17) emits but older servers
     reject (\\restrict / \\unrestrict, SET transaction_timeout), so a pg17 dump
     loads into a pg13 server.
  4. Load with ON_ERROR_STOP=1 so a real failure actually fails. (The old
     behaviour swallowed errors because psql returns 0 on a --clean reload.)

After a successful restore the DB is at the DUMP's alembic revision. Run
`alembic upgrade head` to fast-forward to your local head -- the `make restore-db`
target does this for you, and it also runs on the next container start.

Usage:
    make restore-db file=/path/to/dump.sql.gz APP=<app>          # recommended (copies in + upgrades)
    make script name=restore_database args='/tmp/dump.sql.gz --confirm' APP=<app>
    make script name=restore_database args='/tmp/dump.sql.gz --confirm --no-recreate' APP=<app>
"""

import asyncio
import os
import re
import shlex
import time
from dataclasses import dataclass, field

# psql directives emitted by newer pg_dump (>=17) that older PostgreSQL servers
# don't understand. Stripping these lets a newer dump load into an older server
# (e.g. a pg17 prod dump into a local pg13). Extend the alternation as needed.
INCOMPATIBLE_LINE_RE = r"^(\\(un)?restrict |SET transaction_timeout)"

# Roles referenced by ownership/grant statements:  OWNER TO "name"  /
# GRANT ... TO "name"  /  REVOKE ... FROM "name". We pre-create any missing ones.
_ROLE_RE = re.compile(
    r"(?:OWNER TO|GRANT\b[^;]*?\bTO\b|REVOKE\b[^;]*?\bFROM\b)\s+"
    r"((?:\"[^\"]+\"|[A-Za-z_][A-Za-z0-9_$]*)"
    r"(?:\s*,\s*(?:\"[^\"]+\"|[A-Za-z_][A-Za-z0-9_$]*))*)"
)
_IDENT_RE = re.compile(r"\"[^\"]+\"|[A-Za-z_][A-Za-z0-9_$]*")
# Pseudo-roles / keywords that are never real roles to create.
_ROLE_SKIP = {"PUBLIC", "CURRENT_USER", "SESSION_USER", "CURRENT_ROLE"}


@dataclass
class RestoreResult:
    """Result of a database restore operation."""

    success: bool
    backup_file: str
    duration_seconds: float
    app_name: str
    recreated: bool = False
    roles_created: list[str] = field(default_factory=list)
    restored_revision: str | None = None
    error: str | None = None


def _sql_lit(value: str) -> str:
    """Quote a string as a SQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def _sql_ident(value: str) -> str:
    """Quote an identifier (role/db name) as a SQL identifier."""
    return '"' + value.replace('"', '""') + '"'


def _maintenance_db(db_config) -> str:
    """A database to connect to while (re)creating the target one."""
    return "template1" if db_config.name == "postgres" else "postgres"


def _psql_conn(db_config, dbname: str) -> str:
    """PGPASSWORD-prefixed psql connection string for `dbname`."""
    return (
        f"PGPASSWORD={shlex.quote(db_config.password)} "
        f"psql -h {shlex.quote(db_config.host)} -p {db_config.port} "
        f"-U {shlex.quote(db_config.user)} -d {shlex.quote(dbname)} "
        f"-v ON_ERROR_STOP=1 -X -q"
    )


async def _run(cmd: str, stdin: bytes | None = None) -> tuple[int, str, str]:
    """Run a shell command, optionally feeding stdin; return (rc, stdout, stderr)."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(stdin)
    rc = proc.returncode if proc.returncode is not None else 1
    return rc, out.decode(errors="replace").strip(), err.decode(errors="replace").strip()


async def _extract_roles(backup_file: str) -> list[str]:
    """Find roles referenced by OWNER TO / GRANT / REVOKE in a plain-SQL dump."""
    if backup_file.endswith(".dump"):
        return []  # custom-format dumps are restored with --no-owner; no pre-create needed
    reader = "gunzip -c" if backup_file.endswith(".gz") else "cat"
    cmd = f"{reader} {shlex.quote(backup_file)} | grep -aE '(OWNER TO|GRANT|REVOKE)' || true"
    _, out, _ = await _run(cmd)
    roles: set[str] = set()
    for line in out.splitlines():
        for match in _ROLE_RE.finditer(line):
            for ident in _IDENT_RE.findall(match.group(1)):
                name = ident[1:-1] if ident.startswith('"') else ident
                if name.upper() not in _ROLE_SKIP:
                    roles.add(name)
    return sorted(roles)


def _build_admin_sql(db_config, roles: list[str], recreate: bool) -> str:
    """SQL run against the maintenance DB: create missing roles, optionally recreate the DB."""
    parts: list[str] = []
    for role in roles:
        parts.append(
            f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = {_sql_lit(role)}) "
            f"THEN CREATE ROLE {_sql_ident(role)}; END IF; END $$;"
        )
    if recreate:
        name = db_config.name
        parts.append(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = {_sql_lit(name)} AND pid <> pg_backend_pid();"
        )
        parts.append(f"DROP DATABASE IF EXISTS {_sql_ident(name)} WITH (FORCE);")
        parts.append(f"CREATE DATABASE {_sql_ident(name)} OWNER {_sql_ident(db_config.user)};")
    return "\n".join(parts)


def _filter_errors(stderr: str) -> str:
    """Keep only meaningful error lines from psql/pg_restore stderr."""
    lines = [
        line
        for line in stderr.split("\n")
        if line and not any(x in line.lower() for x in ("notice:", "dropping", "does not exist, skipping"))
    ]
    return "\n".join(lines[:5])


async def restore_backup(
    db_config,
    app_name: str,
    backup_file: str,
    recreate: bool = True,
) -> RestoreResult:
    """
    Restore database from backup file.

    Core restore function used by CLI scripts. When `recreate` is True (default)
    the target database is wiped and recreated before loading, so an older dump
    can be safely installed onto a database whose schema is more migrated.

    Args:
        db_config: Database config with host, port, user, password, name
        app_name: Application name (for messaging)
        backup_file: Path to backup file (.sql, .sql.gz, or .dump)
        recreate: Drop & recreate the database before loading (default True)
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

    # 1. Pre-create roles the dump references, and 2. optionally recreate the DB,
    #    all over a connection to the maintenance DB (the target may be dropped).
    roles = await _extract_roles(backup_file)
    admin_sql = _build_admin_sql(db_config, roles, recreate)
    if admin_sql:
        rc, _, err = await _run(_psql_conn(db_config, _maintenance_db(db_config)), stdin=admin_sql.encode())
        if rc != 0:
            return RestoreResult(
                success=False,
                backup_file=backup_file,
                duration_seconds=time.time() - start_time,
                app_name=app_name,
                roles_created=roles,
                error=f"pre-restore setup failed: {_filter_errors(err) or err}",
            )

    # 3 + 4. Load the dump, stripping cross-version directives, with ON_ERROR_STOP.
    qf = shlex.quote(backup_file)
    if backup_file.endswith(".dump"):
        cmd = (
            f"PGPASSWORD={shlex.quote(db_config.password)} "
            f"pg_restore -h {shlex.quote(db_config.host)} -p {db_config.port} "
            f"-U {shlex.quote(db_config.user)} -d {shlex.quote(db_config.name)} "
            f"--no-owner --clean --if-exists {qf}"
        )
    else:
        reader = "gunzip -c" if backup_file.endswith(".gz") else "cat"
        cmd = f"{reader} {qf} | grep -avE {shlex.quote(INCOMPATIBLE_LINE_RE)} | {_psql_conn(db_config, db_config.name)}"

    rc, _, err = await _run(cmd)
    if rc != 0:
        return RestoreResult(
            success=False,
            backup_file=backup_file,
            duration_seconds=time.time() - start_time,
            app_name=app_name,
            recreated=recreate,
            roles_created=roles,
            error=_filter_errors(err) or err or "psql returned a non-zero exit code",
        )

    # 5. Report the alembic revision the dump landed at (callers fast-forward from here).
    restored_revision = None
    rc2, out2, _ = await _run(
        _psql_conn(db_config, db_config.name) + " -t -A",
        stdin=b"SELECT version_num FROM alembic_version;",
    )
    if rc2 == 0 and out2:
        restored_revision = out2.splitlines()[0].strip()

    return RestoreResult(
        success=True,
        backup_file=backup_file,
        duration_seconds=time.time() - start_time,
        app_name=app_name,
        recreated=recreate,
        roles_created=roles,
        restored_revision=restored_revision,
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

    async def run(self, backup_file: str = "", *flags: str):
        """
        Restore database from backup.

        Args:
            backup_file: Path to backup file (.sql, .sql.gz, or .dump)
            *flags: any of --confirm (required to execute), --no-recreate
                    (load in place instead of wiping the DB first)
        """
        tokens = {flag.lower() for flag in flags}
        do_confirm = bool(tokens & {"--confirm", "confirm", "true", "yes", "1"})
        do_recreate = not bool(tokens & {"--no-recreate", "no-recreate", "--in-place"})

        if not backup_file:
            self.logger.error("Usage: make restore-db file=<backup_file> APP=<app>")
            self.logger.error("   or: make script name=restore_database args='<backup_file> --confirm' APP=<app>")
            return {"success": False, "error": "backup_file is required"}

        if not os.path.exists(backup_file):
            self.logger.error(f"Backup file not found: {backup_file}")
            return {"success": False, "error": f"File not found: {backup_file}"}

        file_size_mb = os.path.getsize(backup_file) / (1024 * 1024)

        self.logger.info("=" * 60)
        self.logger.warning("DATABASE RESTORE")
        self.logger.info("=" * 60)
        self.logger.info("")
        self.logger.info(f"  App:   {self.app_name}")
        self.logger.info(f"  File:  {backup_file}")
        self.logger.info(f"  Size:  {file_size_mb:.2f} MB")
        self.logger.info(
            f"  Mode:  {'recreate database (wipe first)' if do_recreate else 'load in place (--no-recreate)'}"
        )
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
            recreate=do_recreate,
        )

        if not result.success:
            self.logger.error(f"Restore failed: {result.error}")
            return {"success": False, "error": result.error}

        self.logger.info("")
        self.logger.info("Restore completed successfully!")
        self.logger.info(f"  Duration:        {result.duration_seconds:.1f}s")
        if result.roles_created:
            self.logger.info(f"  Roles ensured:   {', '.join(result.roles_created)}")
        self.logger.info(f"  Recreated DB:    {result.recreated}")
        self.logger.info(f"  Restored at rev: {result.restored_revision or 'unknown'}")
        self.logger.info("")
        self.logger.warning(
            f"Database is at the dump's migration ({result.restored_revision or 'unknown'}). "
            f"Run 'make upgrade APP={self.app_name}' to fast-forward to your local head."
        )
        self.logger.info("")
        self.logger.info("=" * 60)

        return {
            "success": True,
            "backup_file": backup_file,
            "duration_seconds": result.duration_seconds,
            "recreated": result.recreated,
            "roles_created": result.roles_created,
            "restored_revision": result.restored_revision,
        }

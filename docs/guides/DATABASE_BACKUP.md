# Database Backup & Restore Guide

This guide covers the database backup and restore system for the TMA platform.

## Quick Start

### Telegram Command (Easiest)
Send `/backup` in your Telegram chat with the bot to instantly receive a database backup file.

### CLI Commands
```bash
make backup-db APP=template-vue                 # dump + copy out to ./backups/
make restore-db file=<path> APP=template-vue    # install a dump onto the local DB
```

`make restore-db` is the recommended way to install a dump: it copies the file
into the container, **wipes & recreates** the database, restores it, then runs
`alembic upgrade head` — so an older dump installs cleanly even when your local
code has newer migrations (see [Migration version handling](#migration-version-handling)).

## Manual Backup

### Basic Backup
```bash
# Create compressed backup (default)
make script name=backup_database APP=template-vue

# Create uncompressed backup
make script name=backup_database args='false' APP=template-vue

# Custom backup name
make script name=backup_database args='before_migration' APP=template-vue
```

### Backup with Telegram Delivery
```bash
make script name=backup_database args='--name=manual_backup true true' APP=template-vue
```

### Output
- Default location: `/tmp/{app}_{timestamp}.sql.gz`
- Compressed with gzip (~5x smaller)
- Includes schema, data, indexes, and constraints

## Restore

### Recommended: `make restore-db`
```bash
make restore-db file=~/Downloads/template-vue_20260619.sql.gz APP=template-vue
```
This copies the file into the container, recreates the database, restores the
dump, and fast-forwards migrations. Pass `recreate=false` to load in place
(only safe when the local schema already matches the dump).

### Low-level: the script directly
The file path must be **inside the container** (the script runs in `<app>-webhook`):
```bash
# Preview (dry run - shows what will happen)
make script name=restore_database args='/tmp/template-vue_20231124.sql.gz' APP=template-vue

# Actually restore (requires --confirm)
make script name=restore_database args='/tmp/template-vue_20231124.sql.gz --confirm' APP=template-vue

# Load in place without wiping the DB first
make script name=restore_database args='/tmp/template-vue_20231124.sql.gz --confirm --no-recreate' APP=template-vue
```
The script does NOT run alembic — run `make upgrade APP=template-vue` afterwards (or let
the next container start do it). `make restore-db` runs it for you.

### Supported Formats
- `.sql` - Plain SQL
- `.sql.gz` - Gzipped SQL (recommended)
- `.dump` - PostgreSQL custom format (restored with `pg_restore --no-owner`)

### Safety
- Restore requires `--confirm` flag
- Always shows preview first
- Creates no automatic backup before restore (do this manually if needed)

### Migration version handling
A dump records its own `alembic_version`. Backups are usually **older** than your
local code, which has newer migrations — so installing one is a version-mismatch.
It's handled like this:

1. **Wipe & recreate (default).** `restore-db` / `restore_database` drops and
   recreates the database before loading. This matters: a plain `pg_dump --clean`
   reload only drops the objects the dump knows about, so tables from migrations
   newer than the dump would survive while `alembic_version` is reset backwards —
   and the next `alembic upgrade head` would fail with *"relation already exists"*.
   Wiping first guarantees the DB lands **exactly** at the dump's revision.
2. **Fast-forward.** After load the DB sits at the dump's revision; `alembic
   upgrade head` then applies your newer local migrations on top of the restored
   data. `make restore-db` does this automatically.

This works as long as the dump's revision is an **ancestor** of your local head
(the normal "older dump" case). If a dump is ever *newer* than your local code,
`alembic upgrade head` will no-op or fail — update/rebase your code first.

The restore also pre-creates any roles the dump references (e.g. a prod owner
role) and strips pg17-only directives (`\restrict`, `SET transaction_timeout`) so
newer dumps load into an older local server.

## Automated Backups

### Configuration
Add to your `.env` file:

```env
# Enable automated daily backups
BACKUP__ENABLED=true

# Hour to run backup (UTC, 0-23)
BACKUP__SCHEDULE_HOUR=3

# Send backups to Telegram (uses RBAC__OWNER_IDS)
BACKUP__TELEGRAM_ENABLED=true

```

### Schedule
- Runs daily at the configured hour (default: 3:00 AM UTC)
- Sends compressed backup to all configured recipients
- Logs success/failure to worker logs

### Monitoring
Check worker logs for backup job status:
```bash
make logs APP=template-vue | grep -i backup
```

## Telegram `/backup` Command

### Usage
1. Open your Telegram chat with the bot
2. Send `/backup`
3. Wait a few seconds
4. Receive the backup file as a document

### Who Can Use It
Only users listed in `RBAC__OWNER_IDS` can use this command.

### Output
```
Database Backup
App: template-vue
Size: 2.34 MB
Tables: 24
Time: 3.2s
```

## Email Delivery (not implemented)

> ⚠️ Planned, never built: no code reads `BACKUP__EMAIL_*` (checked 2026-09-29). Backups go to Telegram only.
> The section below is the intended design.

Backups can be sent via email using Resend.

### Configuration
```env
# Email provider (Resend)
EMAIL__API_KEY=re_xxxxx
EMAIL__FROM_ADDRESS=noreply@yourdomain.com
EMAIL__FROM_NAME=My App

# Backup email settings
BACKUP__EMAIL_ENABLED=true
BACKUP__EMAIL_RECIPIENTS=admin@example.com,backup@example.com
```

### Email Contents
- Subject: `DB Backup: {app} - {timestamp}`
- Body: Backup metadata (size, tables, duration)
- Attachment: Compressed backup file

### Size Limits
- Resend: 40 MB per email
- Telegram: 50 MB per file
- With gzip compression, most databases fit easily

## File Locations

| Type | Location |
|------|----------|
| Scripts | `core/backend/src/core/scripts/common/backup_database.py` |
| Worker Jobs | `core/backend/src/core/infrastructure/arq/jobs/backup.py` |
| Config | `core/backend/src/core/infrastructure/config/components.py` |

## Troubleshooting

### Backup Fails with "container not found"
Ensure the PostgreSQL container is running:
```bash
make status APP=template-vue
docker ps | grep template-vue-pg
```

### Backup Fails with "permission denied"
Check that `pg_dump` is installed and has network access to the PostgreSQL container.

### Email Not Sending
1. Verify `EMAIL__API_KEY` is set
2. Verify `EMAIL__FROM_ADDRESS` domain is verified in Resend
3. Check worker logs for errors

### Telegram Not Sending
1. Verify `RBAC__OWNER_IDS` contains your Telegram ID
2. Verify bot token is correct
3. Ensure you've started a conversation with the bot

### Restore Hangs
Large databases may take several minutes. Check:
```bash
docker logs template-vue-pg --tail 50
```

## Architecture

```
/backup command
     │
     ▼
backup_database_job (ARQ)
     │
     ▼
create_backup() ─────────────► pg_dump via Docker
     │
     ├──► Send to Telegram (FSInputFile)
     │
     └──► Send to Email (Resend API)
```

## Related Commands

| Command | Description |
|---------|-------------|
| `make backup-db APP=<app>` | Create backup + copy to `./backups/` |
| `make restore-db file=<path> APP=<app>` | Install a dump (wipe + restore + migrate) |
| `make script name=backup_database` | Create backup (file stays in container) |
| `make script name=restore_database` | Low-level restore (no auto-migrate) |
| `make script name=wipe_database` | Delete all data (DANGEROUS) |
| `/backup` | Telegram command for instant backup |

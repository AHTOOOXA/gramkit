# Database Backup & Restore Guide

This guide covers the database backup and restore system for the TMA platform.

## Quick Start

### Telegram Command (Easiest)
Send `/backup` in your Telegram chat with the bot to instantly receive a database backup file.

### CLI Command
```bash
make script name=backup_database APP=tarot
```

## Manual Backup

### Basic Backup
```bash
# Create compressed backup (default)
make script name=backup_database APP=tarot

# Create uncompressed backup
make script name=backup_database args='false' APP=tarot

# Custom backup name
make script name=backup_database args='before_migration' APP=tarot
```

### Backup with Telegram Delivery
```bash
make script name=backup_database args='--name=manual_backup true true' APP=tarot
```

### Output
- Default location: `/tmp/{app}_{timestamp}.sql.gz`
- Compressed with gzip (~5x smaller)
- Includes schema, data, indexes, and constraints

## Manual Restore

### Basic Restore
```bash
# Preview (dry run - shows what will happen)
make script name=restore_database args='/tmp/tarot_20231124.sql.gz' APP=tarot

# Actually restore (requires --confirm)
make script name=restore_database args='/tmp/tarot_20231124.sql.gz --confirm' APP=tarot
```

### Supported Formats
- `.sql` - Plain SQL
- `.sql.gz` - Gzipped SQL (recommended)
- `.dump` - PostgreSQL custom format

### Safety
- Restore requires `--confirm` flag
- Always shows preview first
- Creates no automatic backup before restore (do this manually if needed)

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

# Send backups to email
BACKUP__EMAIL_ENABLED=true
BACKUP__EMAIL_RECIPIENTS=admin@example.com,backup@example.com
```

### Schedule
- Runs daily at the configured hour (default: 3:00 AM UTC)
- Sends compressed backup to all configured recipients
- Logs success/failure to worker logs

### Monitoring
Check worker logs for backup job status:
```bash
make logs APP=tarot | grep -i backup
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
App: tarot
Size: 2.34 MB
Tables: 24
Time: 3.2s
```

## Email Delivery

Backups can be sent via email using Resend.

### Configuration
```env
# Email provider (Resend)
EMAIL__API_KEY=re_xxxxx
EMAIL__FROM_ADDRESS=noreply@yourdomain.com
EMAIL__FROM_NAME=Tarot App

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
make status APP=tarot
docker ps | grep tarot-pg
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
docker logs tarot-pg --tail 50
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
| `make script name=backup_database` | Create backup |
| `make script name=restore_database` | Restore backup |
| `make script name=wipe_database` | Delete all data (DANGEROUS) |
| `/backup` | Telegram command for instant backup |

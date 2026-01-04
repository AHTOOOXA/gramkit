# Scripts Directory

Utility scripts for maintaining the monorepo.

## Template Backend Synchronization

Scripts for keeping template and template-react backends in sync.

### check-template-sync.sh

Verifies that template and template-react backends are synchronized.

**Usage:**
```bash
# Quick check (Python files only)
./scripts/check-template-sync.sh --quick

# Full check (includes config, ports, docker-compose)
./scripts/check-template-sync.sh

# Verbose output (show file-by-file comparison)
./scripts/check-template-sync.sh --verbose
```

**What it checks:**
- ✅ All Python source code is identical (50 files)
- ✅ `Dockerfile` differs (allows architectural differences)
- ✅ `pyproject.toml` differs ONLY in package name (strict)
- ✅ Port allocation follows pattern (template + 1)
- ✅ Docker-compose uses hot_reload.py
- ✅ Paths are correct for each app

**Exit codes:**
- `0` - All checks passed
- `1` - Issues found

### sync-template-backends.sh

Synchronizes backend code from template to template-react.

**Usage:**
```bash
# Preview changes (dry run)
./scripts/sync-template-backends.sh --dry-run

# Apply changes (with confirmation)
./scripts/sync-template-backends.sh

# Force sync (skip confirmation)
./scripts/sync-template-backends.sh --force
```

**What it syncs:**
- ✅ All Python files in `src/app/`
- ✅ Worker entry point (`src/worker_entry.py`)

**What it NEVER syncs (app-specific):**
- ❌ `Dockerfile`
- ❌ `pyproject.toml`
- ❌ `docker-compose*.yml`
- ❌ `.env*`
- ❌ `migrations/`
- ❌ `.venv/`

**Workflow:**
1. Make changes to template backend
2. Run sync script: `./scripts/sync-template-backends.sh`
3. Run check script: `./scripts/check-template-sync.sh`
4. Test both apps
5. Commit changes

## Documentation

See [docs/templates/backend-sync-guide.md](../docs/templates/backend-sync-guide.md) for detailed documentation on:
- Architecture overview
- File structure comparison
- Synchronization workflow
- Common issues
- Best practices

## Adding New Scripts

When adding new scripts:
1. Use bash shebang: `#!/bin/bash`
2. Set executable: `chmod +x script.sh`
3. Add error handling: `set -e`
4. Add help text: `--help` flag
5. Document in this README
6. Use colors for output clarity:
   ```bash
   RED='\033[0;31m'
   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   BLUE='\033[0;34m'
   NC='\033[0m' # No Color
   ```

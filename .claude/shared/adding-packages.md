# Adding Packages

How to properly add dependencies to backend and frontend.

---

## Backend (Python/uv)

### 1. Add to pyproject.toml

```bash
# Navigate to app backend
cd apps/{app}/backend

# Edit pyproject.toml - add package to appropriate section:
# - dependencies: always installed
# - [project.optional-dependencies].web: webhook/API only
# - [project.optional-dependencies].bot: bot only
# - [project.optional-dependencies].worker: worker only
```

Example:
```toml
[project.optional-dependencies]
web = [
    "uvicorn",
    "python-socketio",  # NEW: Socket.IO server
    "fastapi==0.118.0",
]
```

### 2. Update lockfile

```bash
# From monorepo root
uv lock
```

This regenerates `uv.lock` with the new dependency.

### 3. Rebuild container

```bash
make up APP={app}
```

The container will rebuild with new dependencies.

### 4. If container still fails

```bash
# Force rebuild without cache
cd apps/{app}
docker-compose build --no-cache webhook
docker-compose up -d webhook
```

Or use make:
```bash
make down APP={app}
make build APP={app}  # if available
make up APP={app}
```

---

## Frontend (Node/pnpm)

### 1. Add package

```bash
cd apps/{app}/frontend
pnpm add {package}           # runtime dependency
pnpm add -D {package}        # dev dependency
```

This automatically updates `package.json` and `pnpm-lock.yaml`.

### 2. Container picks up changes

For local dev with volume mounts, run:
```bash
make fix APP={app}
```

This refreshes the node_modules volumes.

If still failing:
```bash
cd apps/{app}
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

---

## Common Issues

### "ModuleNotFoundError: No module named 'X'"

1. Check package is in `pyproject.toml`
2. Run `uv lock` from monorepo root
3. Rebuild container: `make up APP={app}`
4. If still fails: `docker-compose build --no-cache webhook`

### "Cannot find module 'X'"

1. Check package is in `package.json`
2. Run `make fix APP={app}` to refresh volumes
3. If still fails: `docker-compose build --no-cache frontend`

### Docker using cached layers

The `--no-cache` flag forces a complete rebuild:
```bash
docker-compose build --no-cache {service}
```

---

## Quick Reference

| Task | Backend | Frontend |
|------|---------|----------|
| Add package | Edit `pyproject.toml` | `pnpm add {pkg}` |
| Update lock | `uv lock` | Automatic |
| Rebuild | `make up APP={app}` | `make fix APP={app}` |
| Force rebuild | `docker-compose build --no-cache` | Same |

---

## Lockfile Locations

- **Python**: `/uv.lock` (monorepo root, shared)
- **Node**: `/pnpm-lock.yaml` (monorepo root, shared)

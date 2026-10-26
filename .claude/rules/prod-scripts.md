---
paths:
  - "apps/*/backend/src/app/scripts/**"
  - "core/backend/src/core/scripts/**"
  - "apps/*/backend/src/app/services/admin_tasks.py"
  - "core/backend/src/core/services/admin_tasks.py"
---

# Running backend scripts and admin tasks (local + server)

One-off backend tasks (cleanups, backfills, backups, benchmarks, data
migrations) live as **scripts** with full infrastructure access (DB, Redis, bot, ARQ).
This doc covers writing them, running them locally, and running them on a
deployed server.

## Where scripts live

| Location | Scope | Module path |
|----------|-------|-------------|
| `apps/<app>/backend/src/app/scripts/<name>.py` | app-specific | `app.scripts.<name>` |
| `core/backend/src/core/scripts/common/<name>.py` | shared by all apps | `core.scripts.common.<name>` |

The runner discovers a script **by name** — app scripts take precedence, then
core common scripts (`backup_database`, `restore_database`, `wipe_database`).
List them: `make script-list APP=<app>`.

## Writing a script

Extend `BaseScript` (gives `self.logger`, `self.bot`, `self.redis`, `self.arq`,
and `with_session()` / `with_repo()` / `with_services()`). Implement `run()`:

```python
from app.infrastructure.database.repo.requests import RequestsRepo
from app.services.requests import RequestsService
from core.scripts.base import BaseScript


class MyScript(BaseScript[RequestsRepo, RequestsService]):
    def __init__(self, ctx):
        super().__init__(ctx=ctx, repo_factory=RequestsRepo, service_factory=RequestsService)

    async def run(self, *flags: str):
        async with self.with_session() as session:
            ...
            await session.commit()  # scripts commit explicitly (no request-scoped UoW)
```

Conventions:
- **Destructive scripts are dry-run by default**; require an explicit `--confirm`
  flag to mutate. Print counts + a sample first. (See `restore_database`.)
- Make them **idempotent** and safe to re-run.
- `run()` receives CLI tokens positionally — parse flags from `*flags`.

## Running locally

```bash
make script name=<name> APP=<app>                       # no args
make script name=<name> args='<arg1> <arg2>' APP=<app>  # with args
make script-list APP=<app>                              # discover scripts
```

This `docker exec`s into the local `<app>-webhook` container and runs
`python -m app.scripts <name> <args>`.

## Running on a server

> ⚠️ **For data fixes on a running server, write an admin task, not a script.**
> - **Admin task:** `@admin_task(name, description, destructive=...)` on
>   `async def fn(session, *, dry_run) -> dict` in `app/services/admin_tasks.py`
>   (the framework is `core/backend/src/core/services/admin_tasks.py`; the module is
>   imported at startup by `app/webhook/app.py`, which registers its tasks). It runs
>   inside the live webhook, so there's no second app and no OOM risk. It's owner-only,
>   dry run then apply, and every run is audit-logged as `admin_task:<name>`. Run it
>   from the template-vue admin **Tasks** tab (`/admin/tasks`); on template-react, call
>   `POST /admin/tasks/{name}` (body `{"dry_run": true|false}`, defaults to a dry run)
>   until its screen lands.
> - A task runs in the request's transaction: its writes commit together with the
>   audit row, and an exception rolls both back. The returned dict is stored in the
>   audit row (JSONB), so keep it JSON-serialisable, and keep the task bounded (it
>   holds the request until it finishes).
> - **Why not a script:** `python -m app.scripts …` boots a second full app (bot,
>   Redis, RabbitMQ, ARQ, DB engine) next to the live one in the same container. In a
>   memory-limited container (e.g. a 512 MB webhook) that can run out of memory, and
>   the OOM killer may take down the **live** webhook instead of the script. Use a
>   script on a server only when the container has the headroom, or in a one-off
>   container from the same image.

### Safe sequence (admin task)
1. **Deploy** the release with the task and confirm the version (`GET /health`).
2. **Back up**: the owner-only Telegram **`/backup`** command DMs the `.sql.gz`.
3. **Dry run** (Tasks tab, or `POST /admin/tasks/{name}` with `{"dry_run": true}`)
   and review the output.
4. **Apply** (Tasks tab → Apply → confirm, or `{"dry_run": false}`). The run is
   audit-logged; the task's "Run history" link opens its audit-log rows.

### Scripts on a server — only with memory headroom

Scripts are **baked into the backend image** (the Dockerfile copies
`apps/<app>/backend/`, sets `PYTHONPATH` to the app src, `WORKDIR` to
`/workspace/apps/<app>/backend`, and installs `postgresql-client`). Once a
script is **deployed**, it's available in the running container and reads the
server DB from the container's env.

> ⚠️ Deploy first. The script is compiled into the image at build time —
> deploy the release that contains it, *then* run it. `GET /health` returns
> the running `version`, so check that before you run anything.

Run it in the **`<app>-webhook`** container (it has the DB env + code), from your
host's container terminal or over SSH:

```bash
# one-shot (streams output, non-interactive — the scripts take flags, not prompts)
docker exec <app>-webhook bash -c "cd /workspace/apps/<app>/backend && python -m app.scripts <name> <args>"

# or an interactive shell
docker exec -it <app>-webhook bash
cd /workspace/apps/<app>/backend && python -m app.scripts <name> <args>
```

A safe dry run (no `--confirm`) also tells you whether the script is deployed — if
it prints "Script not found", the deployed build doesn't have it yet.

### Safe sequence for a destructive change (script)
1. **Deploy** and confirm the version (`/health`).
2. **Back up** — `make script name=backup_database …` on the server, or the
   owner-only Telegram **`/backup`** command, which DMs the `.sql.gz`.
3. **Dry run** and review the output.
4. **Apply** with `--confirm`.

## Related
- `.claude/rules/backend.md` — services / repos / models
- `docs/guides/DATABASE_BACKUP.md` — backup/restore scripts (`make backup-db` / `make restore-db`)

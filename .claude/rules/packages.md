---
paths:
  - "**/pyproject.toml"
  - "**/package.json"
  - "uv.lock"
  - "**/pnpm-lock.yaml"
---

# Adding / upgrading dependencies

## Python (uv workspace)
- One lockfile for every backend: the root `uv.lock` (a uv workspace over `core/backend` and `apps/*/backend`).
- Add the package to `apps/<app>/backend/pyproject.toml` (or `core/backend/pyproject.toml` if 2+ apps need it)
  in the right group: `dependencies` (everywhere) or `[project.optional-dependencies]` `web` (webhook/API),
  `bot` or `worker`.
- Run `uv lock` from the repo root, then `make up APP=<app>`. It rebuilds the images (`up -d --build`).
  If a stale layer sticks: `make rebuild APP=<app>` (down + `build --no-cache` + up).
- Commit `pyproject.toml` + `uv.lock` together. Don't commit lockfile drift you didn't cause, and don't
  "repair" a venv with `uv sync --frozen --all-packages`: it once removed `python-multipart` and `uvicorn`.

## JS (pnpm)
- `cd apps/<app>/frontend && pnpm add <pkg>` (`-D` for dev). It's a pnpm workspace (`pnpm-workspace.yaml`:
  `core/frontend`, `core/frontend-react`, `apps/*/frontend`), so the lockfile is the **root** `pnpm-lock.yaml`,
  and the Dockerfiles copy that one. Don't create per-app lockfiles. The pnpm version is pinned by `packageManager` in the root `package.json`.
- The dev server runs on the host, not in Docker. If it doesn't pick the package up:
  `make restart-frontend APP=<app>`.
- Bumping Kubb (or any codegen) → `make schema APP=<app>` and commit the regenerated `src/gen` in the same
  commit, or the next session inherits an unexplained 500-file `gen/` diff.
- Use `pnpm exec <bin>`, not `npx` (npx looks in the root `node_modules` and fails).

## Upgrades
- Check the changelog for breaking changes before a major bump, and run the app's full checks
  (`make test`, `pnpm typecheck && pnpm lint && pnpm build`).
- Leftover upgrades go into a GitHub issue as a checklist rather than a half-done branch.

# `.claude/` — Claude Code config for this monorepo

This directory holds the project's Claude Code setup: path-scoped rules, hooks, an agent and settings. The always-on rules live in the root `CLAUDE.md` — read that first.

## What's here

```
.claude/
├── rules/                  # Layer conventions. A rule with `paths:` frontmatter loads (in full) the
│   │                       # first time Claude reads a matching file — keep each one short and true.
│   ├── backend.md          # core/backend/**, apps/*/backend/**
│   ├── testing.md          # **/tests/**, conftest.py, test_*.py
│   ├── vue.md              # *.vue, template-vue frontend, core/frontend
│   ├── react.md            # template-react frontend, core/frontend-react
│   ├── frontend-api.md     # Kubb codegen, apiFetch, sockets, query invalidation (both stacks)
│   ├── errors.md           # API error shapes → ApiError → UI
│   ├── packages.md         # pyproject.toml / package.json / lockfiles
│   ├── analytics.md        # PostHog capture + keeping an event catalog
│   ├── prod-scripts.md     # backend scripts and admin tasks, locally and on a server
│   └── seen-features.md    # feature reveals / nudges / "what's new"
│
├── hooks/                  # Wired in settings.json
│   ├── guard-bash.sh       # PreToolUse(Bash): blocks git add -A / stash / --no-verify, raw pytest/alembic;
│   │                       # asks before reset --hard / clean -fd and before scripts over ssh
│   ├── guard-edit.sh       # PreToolUse(Edit|Write): blocks hand edits of generated src/gen
│   └── session-start.sh    # SessionStart: branch, ahead/behind, dirty files, shared-checkout warning
│
├── agents/                 # Custom subagents (registered via `name:` frontmatter)
│   └── qa.md               # Change-aware visual QA via the Chrome DevTools MCP
│
├── settings.json           # Plugins (LSPs), hooks, worktree.baseRef = head
└── settings.local.json     # Your local permission allowlist (gitignored, machine-specific)
```

Also at the repo root: `.mcp.json` (Chrome DevTools servers for the `qa` agent) and `.worktreeinclude` (the `.env`
files copied into every `claude -w` worktree).

The hooks need `jq` and `bash` on your `PATH`.

## Working model

The harness ships strong built-ins — prefer them over re-implementing:
`/code-review`, `/security-review`, `/deep-research`, `/verify`, the `Plan` and `Explore` agents, and the `Workflow` tool for multi-agent fan-out.

The custom pieces above earn their place by being **project-specific**. Generic "review/research/design" work leans on the built-ins.

## Maintaining this

- **Where a new instruction goes:** needed in every session → `CLAUDE.md` (keep it under ~200 lines). Needed only
  for one layer → a `rules/` file with `paths:`. A multi-step procedure → a skill in `skills/<name>/SKILL.md`.
  Something that must *always* happen or never happen → a hook. App-only facts → `apps/<app>/CLAUDE.md`.
- When a rule drifts from real code, fix the rule, because agents trust it.
- Custom agents need a `name:` in frontmatter, and skills need a `description:` that states their trigger.

#!/usr/bin/env bash
# PreToolUse(Bash): turn the CLAUDE.md "never" rules into hard stops, with the fix in the message.
# Each shell segment (split on newlines, ;, &&, ||, |) is checked from its start, so text inside
# commit messages or heredocs doesn't trip it. Escape hatch for a deliberate raw run: ALLOW_RAW=1.
set -u
cmd=$(jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0

deny() {
    jq -n --arg r "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}}'
    exit 0
}
ask() {
    jq -n --arg r "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: $r}}'
    exit 0
}

while IFS= read -r seg; do
    seg="${seg#"${seg%%[![:space:]]*}"}"   # ltrim
    seg="${seg#(}"; seg="${seg%)}"          # (subshell)
    raw=0
    # strip leading VAR=value assignments, remembering ALLOW_RAW=1
    while [[ "$seg" =~ ^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+(.*)$ ]]; do
        [[ "$seg" == ALLOW_RAW=1* ]] && raw=1
        seg="${BASH_REMATCH[1]}"
    done

    if [[ "$seg" =~ ^git[[:space:]]+add([[:space:]].*)?[[:space:]](-A|--all|\.)([[:space:]]|$) ]]; then
        deny "Other Claude sessions work in this checkout. Stage only your own files: git add -- <paths> (or git commit -- <paths>), then check git diff --cached --name-only."
    fi
    if [[ "$seg" =~ ^git[[:space:]]+stash([[:space:]]|$) ]] && ! [[ "$seg" =~ ^git[[:space:]]+stash[[:space:]]+(list|show)([[:space:]]|$) ]]; then
        deny "git stash grabs other sessions' uncommitted work in this shared checkout. Commit your own paths, or work in a worktree (claude -w)."
    fi
    if [[ "$seg" =~ ^git[[:space:]]+(commit|push|merge|rebase|cherry-pick|am)([[:space:]].*)?[[:space:]]--no-verify ]] \
        || [[ "$seg" =~ ^git[[:space:]]+commit([[:space:]].*)?[[:space:]]-n([[:space:]]|$) ]]; then
        deny "--no-verify is off-limits: pre-commit hooks must run. Fix what the hook reports (formatting: re-stage and commit again; stale uv.lock: UV_FROZEN=1 git commit …)."
    fi
    if [ "$raw" = 0 ] && [[ "$seg" =~ ^(uv[[:space:]]+run[[:space:]]+)?(python3?[[:space:]]+-m[[:space:]]+)?pytest([[:space:]]|$) ]]; then
        deny "Run tests through make: make test APP=<app> · make test-quick APP=<app> · make test-file file=src/app/tests/… APP=<app>. (Deliberate raw run, e.g. reproducing core CI: prefix ALLOW_RAW=1.)"
    fi
    if [ "$raw" = 0 ] && [[ "$seg" =~ ^(uv[[:space:]]+run[[:space:]]+)?alembic([[:space:]]|$) ]]; then
        deny "Run migrations through make: make migration msg=\"…\" APP=<app> · make upgrade APP=<app> · make downgrade APP=<app>."
    fi
    if [[ "$seg" =~ ^ssh[[:space:]].*app\.scripts ]]; then
        ask "python -m app.scripts boots a second full app next to the live one; in a memory-limited prod container that can OOM-kill the live webhook. Confirm the container has the headroom, or prefer an @admin_task in app/services/admin_tasks.py, run at /admin/tasks (see .claude/rules/prod-scripts.md)."
    fi
    if [[ "$seg" =~ ^git[[:space:]]+reset[[:space:]].*--hard ]] || [[ "$seg" =~ ^git[[:space:]]+clean[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*d?[[:space:]]*$ ]]; then
        ask "This discards uncommitted work, possibly another session's. Confirm it's scoped to your own changes."
    fi
done < <(nl=$'\n'; c="${cmd//&&/$nl}"; c="${c//||/$nl}"; c="${c//;/$nl}"; c="${c//|/$nl}"; printf '%s\n' "$c")
exit 0

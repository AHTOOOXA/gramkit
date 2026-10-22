#!/usr/bin/env bash
# SessionStart: where am I, and is anyone else's work in this checkout? Printed text reaches Claude as context.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
branch=$(git branch --show-current 2>/dev/null) || exit 0
top=$(git rev-parse --show-toplevel 2>/dev/null)
modified=$(git status --porcelain --untracked-files=no 2>/dev/null | wc -l | tr -d ' ')
untracked=$(git status --porcelain 2>/dev/null | grep -c '^??')
counts=$(git rev-list --left-right --count "origin/$branch...HEAD" 2>/dev/null)
echo "Repo: $top · branch: ${branch:-detached} · last: $(git log -1 --format='%h %s' 2>/dev/null | cut -c1-80)"
[ -n "$counts" ] && echo "vs origin/$branch: $(echo "$counts" | awk '{print $2" ahead, "$1" behind"}')"
echo "Working tree: $modified modified, $untracked untracked."
if [ "$modified" -gt 0 ] || [ "$untracked" -gt 0 ]; then
    echo "Those may belong to other Claude sessions or to the user: don't stage, stash, revert or commit them. Commit only your own paths."
fi
[ "$branch" = "main" ] && git show-ref --verify --quiet refs/heads/dev && echo "You're on main: work happens on dev (or a branch off dev); main only receives releases."
exit 0

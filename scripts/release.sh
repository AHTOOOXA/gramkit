#!/usr/bin/env bash
#
# Release an app in two phases, dev first and main second, so the server never builds both at once.
#
#   scripts/release.sh dev  <app> <patch|minor|major|none>   bump the version (optional) and push dev
#   scripts/release.sh main <app>                            merge origin/dev into main, tag, push
#
# Wait for the dev build between the phases.
# Neither phase checks out another branch or stashes in this working tree: main is merged in a
# temporary worktree. Other sessions' uncommitted work in this tree is left alone.
# Called by `make release-dev`, `make release-main` and `make release` (see Makefile).
set -euo pipefail

die() { echo "✗ $*" >&2; exit 1; }

phase=${1:-}
app=${2:-}
bump=${3:-}
[ -n "$phase" ] && [ -n "$app" ] || die "usage: $0 dev <app> <patch|minor|major|none> | $0 main <app>"

root=$(git rev-parse --show-toplevel)
cd "$root"
app_dir="apps/$app"
[ -f "$app_dir/bump_version.py" ] || die "$app_dir/bump_version.py not found"

pkg="$app_dir/frontend/package.json"
read_version() { python3 -c "import json, sys; print(json.load(sys.stdin)['version'])"; }

release_dev() {
    case "$bump" in
        patch | minor | major | none) ;;
        *) die "BUMP must be patch, minor, major or none (got '${bump}')" ;;
    esac
    [ "$(git branch --show-current)" = "dev" ] || die "must be on dev (on $(git branch --show-current))"

    echo "→ Pulling origin/dev..."
    git pull --ff-only origin dev

    if [ "$bump" != "none" ]; then
        local files=("$pkg" "$app_dir/backend/pyproject.toml" "uv.lock")
        git diff --quiet HEAD -- "${files[@]}" || die "uncommitted changes in ${files[*]} — commit or revert them first"
        (cd "$app_dir" && python3 bump_version.py "$bump")
        # The workspace lockfile records each member's version; a stale one makes pre-commit's `uv run` fail.
        uv lock --quiet
        local version
        version=$(read_version <"$pkg")
        git commit -m "chore($app): bump version to $version" -- "${files[@]}"
    fi

    echo "→ Pushing dev..."
    git push origin dev
    echo "✓ dev pushed ($app $(read_version <"$pkg"))."
    echo "  Next: wait for the dev build, then: make release-main APP=$app"
}

release_main() {
    git fetch --quiet origin main dev --tags
    if [ -n "$(git rev-list origin/dev..dev 2>/dev/null)" ]; then
        echo "⚠ local dev has commits that aren't on origin/dev — they won't be released (push dev first)."
    fi

    local version tag tmp
    version=$(git show "origin/dev:$pkg" | read_version)
    tag="$app-v$version"
    tmp=$(mktemp -d)/release
    git worktree add --quiet --detach "$tmp" origin/main
    # shellcheck disable=SC2064  # expand $tmp now: it's local and gone by the time EXIT fires
    trap "git worktree remove --force '$tmp' >/dev/null 2>&1 || true" EXIT

    echo "→ Merging origin/dev into main..."
    git -C "$tmp" merge --no-edit -m "Merge branch 'dev'" origin/dev
    git -C "$tmp" diff --quiet origin/dev || echo "⚠ main's tree differs from dev after the merge (a commit only on main?)."

    if git rev-parse --quiet --verify "refs/tags/$tag" >/dev/null; then
        echo "ℹ tag $tag already exists — not tagging (bump the version to tag a new release)."
        tag=""
    else
        git -C "$tmp" tag -a "$tag" -m "Release $app v$version"
    fi

    echo "→ Pushing main..."
    git -C "$tmp" push origin HEAD:main
    if [ -n "$tag" ]; then
        git push origin "$tag"
    fi
    # Move the local main ref along; fails harmlessly if main is checked out in some worktree.
    git fetch --quiet origin main:main 2>/dev/null || true

    echo "✓ Released $app $version${tag:+ (tag $tag)}."
}

case "$phase" in
    dev) release_dev ;;
    main) release_main ;;
    *) die "phase must be dev or main" ;;
esac

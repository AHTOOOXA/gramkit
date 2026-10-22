#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from typing import Literal, cast

BumpType = Literal["patch", "minor", "major"]

def bump_version_number(version: str, bump_type: BumpType) -> str:
    major, minor, patch = map(int, version.replace("^", "").replace("v", "").split("."))

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"

def bump_frontend_version(bump_type: BumpType) -> str:
    """Bump frontend/package.json and return the new version.

    frontend/package.json is the SINGLE SOURCE OF TRUTH for the app version — it
    is what `make release` reads, commits, and tags. The backend is then set to
    this exact value (see set_backend_version), so the two files can never drift.
    """
    package_json = Path("frontend/package.json")
    if not package_json.exists():
        sys.exit("frontend/package.json not found")

    with open(package_json) as f:
        data = json.load(f)

    current_version = data["version"]
    new_version = bump_version_number(current_version, bump_type)
    data["version"] = new_version

    with open(package_json, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Frontend version bumped: {current_version} -> {new_version}")
    return new_version

def set_backend_version(new_version: str) -> None:
    """Set backend/pyproject.toml to `new_version` — it tracks the frontend exactly.

    This is deliberately NOT an independent bump: writing the frontend's new
    version keeps the two in lockstep and self-heals any pre-existing gap on the
    next release.
    """
    pyproject_toml = Path("backend/pyproject.toml")
    if not pyproject_toml.exists():
        sys.exit("backend/pyproject.toml not found")

    content = pyproject_toml.read_text()
    version_pattern = r'version = "(\d+\.\d+\.\d+)"'
    match = re.search(version_pattern, content)
    if not match:
        sys.exit("Version not found in backend/pyproject.toml")

    current_version = match.group(1)
    new_content = re.sub(version_pattern, f'version = "{new_version}"', content, count=1)

    pyproject_toml.write_text(new_content)
    print(f"Backend version set: {current_version} -> {new_version}")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ["patch", "minor", "major"]:
        print("Usage: python bump_version.py <patch|minor|major>")
        sys.exit(1)

    bump_type = cast(BumpType, sys.argv[1])
    # Frontend is the source of truth; the backend is pinned to the same value.
    new_version = bump_frontend_version(bump_type)
    set_backend_version(new_version)

if __name__ == "__main__":
    main()

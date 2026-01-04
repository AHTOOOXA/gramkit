#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from typing import Literal

BumpType = Literal["patch", "minor", "major"]

def bump_version_number(version: str, bump_type: BumpType) -> str:
    major, minor, patch = map(int, version.replace("^", "").replace("v", "").split("."))

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"

def update_frontend_version(bump_type: BumpType):
    package_json = Path("frontend/package.json")
    if not package_json.exists():
        print("frontend/package.json not found")
        return

    with open(package_json) as f:
        data = json.load(f)

    current_version = data["version"]
    new_version = bump_version_number(current_version, bump_type)
    data["version"] = new_version

    with open(package_json, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Frontend version bumped: {current_version} -> {new_version}")

def update_backend_version(bump_type: BumpType):
    pyproject_toml = Path("backend/pyproject.toml")
    if not pyproject_toml.exists():
        print("backend/pyproject.toml not found")
        return

    content = pyproject_toml.read_text()
    version_pattern = r'version = "(\d+\.\d+\.\d+)"'
    match = re.search(version_pattern, content)

    if not match:
        print("Version not found in pyproject.toml")
        return

    current_version = match.group(1)
    new_version = bump_version_number(current_version, bump_type)
    new_content = re.sub(version_pattern, f'version = "{new_version}"', content)

    pyproject_toml.write_text(new_content)
    print(f"Backend version bumped: {current_version} -> {new_version}")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ["patch", "minor", "major"]:
        print("Usage: python bump_version.py <patch|minor|major>")
        sys.exit(1)

    bump_type = sys.argv[1]
    update_frontend_version(bump_type)
    update_backend_version(bump_type)

if __name__ == "__main__":
    main()

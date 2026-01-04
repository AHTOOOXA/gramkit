"""
Shared hot reload script for all Telegram Mini Apps.

This script provides automatic code reloading for development environments.
It watches specified paths for Python file changes and restarts the target
command automatically.

Usage:
    python hot_reload.py <target> <watch_path1> [watch_path2...] [-- args...]

Examples:
    # Bot service (module mode)
    python hot_reload.py app.tgbot.bot src/ /workspace/core/backend/src/

    # Worker service (script mode with args)
    python hot_reload.py worker_entry src/ /workspace/core/backend/src/ -- app.worker.worker.WorkerSettings

Features:
    - Watches multiple paths simultaneously
    - Filters out __pycache__, .pyc files
    - Fast Rust-based file watcher (via watchfiles)
    - Graceful process restart on changes
    - Clear logging of reload events
    - Supports both module (-m) and script modes

Technical:
    - Uses watchfiles (same library as uvicorn --reload)
    - Runs target via subprocess
    - Handles SIGTERM/SIGINT gracefully
"""

import sys
from pathlib import Path

from watchfiles import run_process


def main():
    """Main entry point for hot reload script."""
    if len(sys.argv) < 3:
        print("❌ Error: Missing arguments")
        print("\nUsage: hot_reload.py <target> <watch_path1> [watch_path2...] [-- args...]")
        print("\nExamples:")
        print("  python hot_reload.py app.tgbot.bot src/ /workspace/core/backend/src/")
        print(
            "  python hot_reload.py worker_entry src/ /workspace/core/backend/src/ -- app.worker.worker.WorkerSettings"
        )
        sys.exit(1)

    # Parse arguments - split on '--' to separate watch paths from target args
    args = sys.argv[1:]
    if "--" in args:
        separator_index = args.index("--")
        target_and_watch = args[:separator_index]
        target_args = args[separator_index + 1 :]
    else:
        target_and_watch = args
        target_args = []

    target = target_and_watch[0]
    watch_paths = target_and_watch[1:]

    # Validate watch paths exist
    for path_str in watch_paths:
        path = Path(path_str)
        if not path.exists():
            print(f"⚠️  Warning: Watch path does not exist: {path_str}")

    # Determine if target is a module or script
    # If target contains dots, treat as module, otherwise as script
    if "." in target and not target.endswith(".py"):
        # Module mode: python -m module.path
        command = f"python -u -m {target}"
        if target_args:
            command += " " + " ".join(target_args)
        mode = "module"
    else:
        # Script mode: python script.py [args]
        command = f"python -u {target}"
        if target_args:
            command += " " + " ".join(target_args)
        mode = "script"

    print("=" * 60)
    print("🔥 Hot Reload Enabled")
    print("=" * 60)
    print(f"📦 Target: {target} ({mode} mode)")
    if target_args:
        print(f"📋 Args: {' '.join(target_args)}")
    print("📁 Watching paths:")
    for path in watch_paths:
        print(f"   - {path}")
    print("=" * 60)
    print("Ready! Waiting for file changes...\n")

    # Run the process with file watching
    run_process(
        *watch_paths,
        target=command,
        watch_filter=lambda change, path: (
            str(path).endswith(".py")
            and "__pycache__" not in str(path)
            and ".pyc" not in str(path)
            and "/.pytest_cache/" not in str(path)
            and "/.ruff_cache/" not in str(path)
        ),
    )


if __name__ == "__main__":
    main()

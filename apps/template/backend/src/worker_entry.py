"""Worker entry point for ARQ worker with proper event loop initialization."""

import asyncio
import importlib
import sys

from arq import run_worker

if __name__ == "__main__":
    # The first argument should be the module path to WorkerSettings
    if len(sys.argv) < 2:
        print("Usage: python worker_entry.py <module.path.to.WorkerSettings>")
        sys.exit(1)

    worker_settings_path = sys.argv[1]

    # Split module path and class name
    module_path, class_name = worker_settings_path.rsplit(".", 1)

    # Dynamically import the module
    module = importlib.import_module(module_path)

    # Get the WorkerSettings class
    worker_settings_cls = getattr(module, class_name)

    # Create event loop explicitly for uvloop compatibility
    # This is required in Python 3.10+ when uvloop is installed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No event loop in current thread, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the worker
    run_worker(worker_settings_cls)

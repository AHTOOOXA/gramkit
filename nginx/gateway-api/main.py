"""
Gateway API - Docker container status and log viewing
"""
import asyncio
import re
from typing import AsyncGenerator

import docker
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Gateway API", docs_url="/docs", redoc_url=None)

# Docker client
client = docker.from_env()

# Known apps and their container prefixes
APPS = {
    "template": {"containers": ["template-webhook", "template-bot", "template-worker"], "compose": "template"},
    "template-react": {"containers": ["template-react-webhook"], "compose": "template-react"},
}


class ContainerStatus(BaseModel):
    name: str
    status: str  # running, exited, restarting, etc.
    health: str | None  # healthy, unhealthy, starting, none
    uptime: str | None
    restart_count: int


class AppStatus(BaseModel):
    app: str
    online: bool  # True if ALL containers are running
    containers: list[ContainerStatus]


class StatusResponse(BaseModel):
    apps: list[AppStatus]
    shared: list[ContainerStatus]


def get_container_info(container) -> ContainerStatus:
    """Extract status info from a container."""
    # Get health status if available
    health = None
    if container.attrs.get("State", {}).get("Health"):
        health = container.attrs["State"]["Health"].get("Status")

    # Get uptime
    uptime = None
    if container.status == "running":
        started_at = container.attrs.get("State", {}).get("StartedAt", "")
        if started_at:
            uptime = started_at[:19].replace("T", " ")

    return ContainerStatus(
        name=container.name,
        status=container.status,
        health=health,
        uptime=uptime,
        restart_count=container.attrs.get("RestartCount", 0),
    )


@app.get("/api/gateway/status", response_model=StatusResponse)
async def get_status():
    """Get status of all containers."""
    containers = client.containers.list(all=True)
    container_map = {c.name: c for c in containers}

    apps_status = []
    for app_name, app_info in APPS.items():
        app_containers = []
        all_running = True

        for container_name in app_info["containers"]:
            if container_name in container_map:
                c = container_map[container_name]
                app_containers.append(get_container_info(c))
                if c.status != "running":
                    all_running = False
            else:
                # Container doesn't exist
                app_containers.append(ContainerStatus(
                    name=container_name,
                    status="not_found",
                    health=None,
                    uptime=None,
                    restart_count=0,
                ))
                all_running = False

        apps_status.append(AppStatus(
            app=app_name,
            online=all_running and len(app_containers) > 0,
            containers=app_containers,
        ))

    # Shared infrastructure containers
    shared_containers = []
    for name in ["nginx", "shared-cloudflared", "shared-playwright", "gateway-api"]:
        if name in container_map:
            shared_containers.append(get_container_info(container_map[name]))

    return StatusResponse(apps=apps_status, shared=shared_containers)


# Regex patterns for error/warning detection
ERROR_PATTERNS = [
    re.compile(r'\b(error|exception|traceback|failed|failure)\b', re.IGNORECASE),
    re.compile(r'\b(critical|fatal|panic)\b', re.IGNORECASE),
    re.compile(r'^\s*File ".*", line \d+', re.MULTILINE),  # Python traceback
]

WARNING_PATTERNS = [
    re.compile(r'\b(warning|warn|deprecated)\b', re.IGNORECASE),
]

# ANSI escape code pattern
ANSI_PATTERN = re.compile(r'\x1b\[[0-9;]*m')

# Docker timestamp pattern (ISO format at start of line)
TIMESTAMP_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.?\d*Z?\s*')


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return ANSI_PATTERN.sub('', text)


def parse_log_line(line: str) -> tuple[str | None, str]:
    """Parse timestamp and message from a log line."""
    line = strip_ansi(line.strip())
    match = TIMESTAMP_PATTERN.match(line)
    if match:
        timestamp = match.group(1).replace('T', ' ')
        message = line[match.end():].strip()
        return timestamp, message
    return None, line


def is_error_line(line: str) -> bool:
    """Check if a log line contains an error."""
    return any(p.search(line) for p in ERROR_PATTERNS)


def is_warning_line(line: str) -> bool:
    """Check if a log line contains a warning."""
    return any(p.search(line) for p in WARNING_PATTERNS)


async def stream_logs(container_names: list[str], level: str) -> AsyncGenerator[str, None]:
    """Stream filtered logs from containers as SSE."""
    include_errors = "error" in level
    include_warnings = "warning" in level

    # Get containers
    containers = []
    for name in container_names:
        try:
            containers.append(client.containers.get(name))
        except docker.errors.NotFound:
            yield f"data: {{'container': '{name}', 'error': 'not found'}}\n\n"

    if not containers:
        yield "data: {'error': 'no containers found'}\n\n"
        return

    # Stream logs from each container
    for container in containers:
        try:
            # Get last 100 lines, then stream
            for log_line in container.logs(tail=100, stream=True, timestamps=True):
                line = log_line.decode("utf-8", errors="replace").strip()

                # Filter by level
                is_err = is_error_line(line)
                is_warn = is_warning_line(line)

                if (include_errors and is_err) or (include_warnings and is_warn):
                    level_tag = "error" if is_err else "warning"
                    # Escape for JSON
                    escaped = line.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                    yield f"data: {{\"container\": \"{container.name}\", \"level\": \"{level_tag}\", \"line\": \"{escaped}\"}}\n\n"
                    await asyncio.sleep(0.01)  # Prevent blocking
        except Exception as e:
            yield f"data: {{\"container\": \"{container.name}\", \"error\": \"{str(e)}\"}}\n\n"


@app.get("/api/gateway/logs/{app_name}")
async def get_logs(app_name: str, level: str = "error,warning"):
    """
    Stream filtered logs from an app's containers.

    Args:
        app_name: App name or "all" for all apps
        level: Comma-separated levels to include: "error", "warning", or "error,warning"
    """
    if app_name == "all":
        container_names = []
        for app_info in APPS.values():
            container_names.extend(app_info["containers"])
    elif app_name in APPS:
        container_names = APPS[app_name]["containers"]
    else:
        raise HTTPException(status_code=404, detail=f"Unknown app: {app_name}")

    return StreamingResponse(
        stream_logs(container_names, level),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/gateway/logs-snapshot/{app_name}")
async def get_logs_snapshot(app_name: str, level: str = "error,warning", lines: int = 50):
    """
    Get a snapshot of recent filtered logs (non-streaming).
    """
    if app_name == "all":
        container_names = []
        for app_info in APPS.values():
            container_names.extend(app_info["containers"])
    elif app_name in APPS:
        container_names = APPS[app_name]["containers"]
    else:
        raise HTTPException(status_code=404, detail=f"Unknown app: {app_name}")

    include_errors = "error" in level
    include_warnings = "warning" in level

    results = []
    for name in container_names:
        try:
            container = client.containers.get(name)
            log_lines = container.logs(tail=500, timestamps=True).decode("utf-8", errors="replace").split("\n")

            for line in log_lines:
                line = line.strip()
                if not line:
                    continue

                # Parse and clean the line
                timestamp, message = parse_log_line(line)

                is_err = is_error_line(message)
                is_warn = is_warning_line(message)

                if (include_errors and is_err) or (include_warnings and is_warn):
                    results.append({
                        "container": name,
                        "level": "error" if is_err else "warning",
                        "timestamp": timestamp,
                        "message": message,
                    })
        except docker.errors.NotFound:
            pass
        except Exception as e:
            results.append({"container": name, "error": str(e)})

    # Sort by timestamp and return most recent N lines
    results.sort(key=lambda x: x.get("timestamp") or "")
    return {"logs": results[-lines:]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

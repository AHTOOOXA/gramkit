"""Socket.IO event handlers for demo."""

import asyncio
import random
from collections import deque
from datetime import UTC, datetime

from .server import sio

# Fake usernames for demo
FAKE_USERNAMES = [
    "Alex",
    "Jordan",
    "Sam",
    "Charlie",
    "Morgan",
    "Riley",
    "Casey",
    "Quinn",
    "Avery",
    "Taylor",
    "Drew",
    "Jamie",
    "Skyler",
    "Reese",
    "Parker",
]

# Global demo state
counter = 0
fake_users = random.randint(1, 3)
simulation_task: asyncio.Task | None = None
recent_events: deque = deque(maxlen=3)


def get_demo_user_count() -> int:
    """Get count of users in demo room."""
    return len(list(sio.manager.get_participants("/", "demo")))


def create_event(username: str, delta: int) -> dict:
    """Create an event dict."""
    return {
        "user": username,
        "delta": delta,
        "time": datetime.now(UTC).isoformat(),
    }


async def broadcast_state(event: dict | None = None):
    """Broadcast current state to all connected clients in demo room."""
    if event:
        recent_events.append(event)

    await sio.emit(
        "update",
        {
            "counter": counter,
            "users": fake_users + get_demo_user_count(),
            "events": list(recent_events),
        },
        room="demo",
    )


async def simulate_activity():
    """Background task: simulate other users changing counter."""
    global counter, fake_users
    while True:
        await asyncio.sleep(random.uniform(5, 12))
        delta = random.choice([-3, -2, -1, 1, 2, 3])
        counter += delta
        fake_users = max(1, min(5, fake_users + random.choice([-1, 0, 0, 0, 1])))
        event = create_event(random.choice(FAKE_USERNAMES), delta)
        await broadcast_state(event)


@sio.event
async def connect(sid, environ, auth=None):
    """Handle new connection."""
    global simulation_task
    await sio.enter_room(sid, "demo")

    if simulation_task is None or simulation_task.done():
        simulation_task = asyncio.create_task(simulate_activity())

    await sio.emit(
        "update",
        {
            "counter": counter,
            "users": fake_users + get_demo_user_count(),
            "events": list(recent_events),
        },
        to=sid,
    )


@sio.event
async def disconnect(sid):
    """Handle disconnection."""
    global simulation_task
    await sio.leave_room(sid, "demo")

    if get_demo_user_count() == 0 and simulation_task:
        simulation_task.cancel()
        simulation_task = None


@sio.event
async def increment(sid, delta: int = 1):
    """Handle increment/decrement request from client."""
    global counter
    delta = max(-3, min(3, delta))
    if delta == 0:
        delta = 1
    counter += delta
    event = create_event("You", delta)
    await broadcast_state(event)

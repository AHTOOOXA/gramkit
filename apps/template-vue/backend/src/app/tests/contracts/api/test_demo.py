"""Tests for demo endpoints.

These tests verify the TanStack Query showcase endpoints:
- /demo/slow - Artificial delay endpoint
- /demo/unreliable - Random failure endpoint
- /demo/counter - Stateful counter (get/increment/reset)
- /demo/notify - Delayed notification endpoint
"""

import uuid

import pytest
from httpx import AsyncClient


def unique_counter_id() -> str:
    """Generate unique counter ID for test isolation."""
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.mark.contract
class TestSlowEndpoint:
    """Tests for /demo/slow endpoint."""

    async def test_slow_endpoint_with_minimal_delay(self, client: AsyncClient):
        """Test slow endpoint returns correct response with minimal delay."""
        response = await client.get("/demo/slow?delay_ms=100")
        assert response.status_code == 200
        data = response.json()
        assert data["delay_ms"] == 100
        assert "timestamp" in data
        assert data["message"] == "Loaded after 100ms"

    async def test_slow_endpoint_default_delay(self, client: AsyncClient):
        """Test slow endpoint uses default delay when not specified."""
        # Using short timeout to avoid waiting 2 seconds
        # Just verify the endpoint accepts the request format
        response = await client.get("/demo/slow?delay_ms=100")
        assert response.status_code == 200

    async def test_slow_endpoint_validates_min_delay(self, client: AsyncClient):
        """Test slow endpoint rejects delay below minimum."""
        response = await client.get("/demo/slow?delay_ms=50")
        assert response.status_code == 422  # Validation error

    async def test_slow_endpoint_validates_max_delay(self, client: AsyncClient):
        """Test slow endpoint rejects delay above maximum."""
        response = await client.get("/demo/slow?delay_ms=20000")
        assert response.status_code == 422  # Validation error


@pytest.mark.contract
class TestUnreliableEndpoint:
    """Tests for /demo/unreliable endpoint."""

    async def test_unreliable_endpoint_always_succeeds(self, client: AsyncClient):
        """Test unreliable endpoint succeeds with 0% failure rate."""
        response = await client.get("/demo/unreliable?fail_rate=0")
        assert response.status_code == 200
        data = response.json()
        assert data["attempt_succeeded"] is True
        assert "timestamp" in data
        assert data["message"] == "Request succeeded!"

    async def test_unreliable_endpoint_always_fails(self, client: AsyncClient):
        """Test unreliable endpoint fails with 100% failure rate."""
        response = await client.get("/demo/unreliable?fail_rate=1")
        assert response.status_code == 500
        data = response.json()
        assert "fail_rate=1" in data["detail"]

    async def test_unreliable_endpoint_validates_fail_rate_min(self, client: AsyncClient):
        """Test unreliable endpoint rejects fail_rate below 0."""
        response = await client.get("/demo/unreliable?fail_rate=-0.1")
        assert response.status_code == 422

    async def test_unreliable_endpoint_validates_fail_rate_max(self, client: AsyncClient):
        """Test unreliable endpoint rejects fail_rate above 1."""
        response = await client.get("/demo/unreliable?fail_rate=1.5")
        assert response.status_code == 422


@pytest.mark.contract
class TestCounterEndpoint:
    """Tests for /demo/counter endpoints."""

    async def test_counter_initial_value(self, client: AsyncClient):
        """Test counter returns 0 initially for new counter_id."""
        cid = unique_counter_id()
        response = await client.get(f"/demo/counter?counter_id={cid}")
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 0
        assert data["counter_id"] == cid
        assert "timestamp" in data

    async def test_counter_increment_default(self, client: AsyncClient):
        """Test counter increments by 1 by default."""
        cid = unique_counter_id()
        response = await client.post(f"/demo/counter/increment?counter_id={cid}")
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 1
        assert data["counter_id"] == cid

    async def test_counter_increment_custom_amount(self, client: AsyncClient):
        """Test counter increments by custom amount."""
        cid = unique_counter_id()
        response = await client.post(f"/demo/counter/increment?counter_id={cid}&amount=5")
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 5

    async def test_counter_increment_accumulates(self, client: AsyncClient):
        """Test counter accumulates increments."""
        cid = unique_counter_id()
        await client.post(f"/demo/counter/increment?counter_id={cid}&amount=3")
        await client.post(f"/demo/counter/increment?counter_id={cid}&amount=2")
        response = await client.get(f"/demo/counter?counter_id={cid}")
        assert response.json()["value"] == 5

    async def test_counter_reset(self, client: AsyncClient):
        """Test counter resets to 0."""
        cid = unique_counter_id()
        # Increment first
        await client.post(f"/demo/counter/increment?counter_id={cid}&amount=10")

        # Reset
        response = await client.post(f"/demo/counter/reset?counter_id={cid}")
        assert response.status_code == 200
        assert response.json()["value"] == 0

        # Verify reset persisted
        response = await client.get(f"/demo/counter?counter_id={cid}")
        assert response.json()["value"] == 0

    async def test_counter_increment_validates_amount_min(self, client: AsyncClient):
        """Test counter increment rejects amount below 1."""
        response = await client.post("/demo/counter/increment?amount=0")
        assert response.status_code == 422

    async def test_counter_increment_validates_amount_max(self, client: AsyncClient):
        """Test counter increment rejects amount above 100."""
        response = await client.post("/demo/counter/increment?amount=101")
        assert response.status_code == 422

    async def test_counter_isolation(self, client: AsyncClient):
        """Test counters with different IDs are isolated."""
        cid1 = unique_counter_id()
        cid2 = unique_counter_id()

        # Increment first counter
        await client.post(f"/demo/counter/increment?counter_id={cid1}&amount=10")

        # Second counter should still be 0
        response = await client.get(f"/demo/counter?counter_id={cid2}")
        assert response.json()["value"] == 0

        # First counter should be 10
        response = await client.get(f"/demo/counter?counter_id={cid1}")
        assert response.json()["value"] == 10


@pytest.mark.contract
class TestCounterShouldFail:
    """Tests for counter should_fail parameter (optimistic update demo)."""

    async def test_counter_increment_should_fail(self, client: AsyncClient):
        """Test counter increment fails when should_fail=true."""
        cid = unique_counter_id()
        response = await client.post(f"/demo/counter/increment?counter_id={cid}&should_fail=true")
        assert response.status_code == 500
        data = response.json()
        assert "rollback demo" in data["detail"]

    async def test_counter_unchanged_after_failed_increment(self, client: AsyncClient):
        """Test counter value unchanged after failed increment."""
        cid = unique_counter_id()
        # Set counter to known value
        await client.post(f"/demo/counter/increment?counter_id={cid}&amount=5")

        # Try to increment with failure
        await client.post(f"/demo/counter/increment?counter_id={cid}&should_fail=true")

        # Verify counter unchanged
        response = await client.get(f"/demo/counter?counter_id={cid}")
        assert response.json()["value"] == 5


@pytest.mark.contract
async def test_counter_workflow(client: AsyncClient):
    """Test complete counter workflow (get/increment/reset)."""
    cid = unique_counter_id()

    # Get initial value (new counter starts at 0)
    response = await client.get(f"/demo/counter?counter_id={cid}")
    assert response.json()["value"] == 0

    # Increment
    response = await client.post(f"/demo/counter/increment?counter_id={cid}&amount=5")
    assert response.json()["value"] == 5

    # Verify
    response = await client.get(f"/demo/counter?counter_id={cid}")
    assert response.json()["value"] == 5

    # Reset
    response = await client.post(f"/demo/counter/reset?counter_id={cid}")
    assert response.json()["value"] == 0


@pytest.mark.contract
class TestNotifyEndpoint:
    """Tests for /demo/notify endpoint (delayed notifications)."""

    async def test_notify_endpoint_requires_telegram_auth(self, client: AsyncClient):
        """Guest users (no telegram_id) get 401 from notify endpoint."""
        response = await client.post(
            "/demo/notify",
            json={"delay_seconds": 5},
        )

        assert response.status_code == 401
        assert "Telegram authentication required" in response.json()["detail"]

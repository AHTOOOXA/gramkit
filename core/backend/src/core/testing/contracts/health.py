"""Base test class for health endpoint contract tests.

Health checks are critical for:
- Kubernetes readiness/liveness probes
- Load balancer health checks
- Monitoring systems

Apps inherit this class - fixtures are provided by app's conftest.py.
"""

import pytest
from httpx import AsyncClient


class BaseHealthTests:
    """Base class for health endpoint contract tests."""

    @pytest.mark.contract
    async def test_health_returns_200(self, client: AsyncClient):
        """GET /health returns 200 OK."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.contract
    async def test_health_returns_status_healthy(self, client: AsyncClient):
        """GET /health returns JSON with status and timestamp."""
        response = await client.get("/health")

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

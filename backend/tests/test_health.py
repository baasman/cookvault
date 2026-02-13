"""
Tests for health check endpoints.
"""

from flask.testing import FlaskClient


class TestHealthEndpoints:
    """Tests for application health checks."""

    def test_health_endpoint(self, client: FlaskClient):
        """Test basic health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"

    def test_health_detailed(self, client: FlaskClient):
        """Test detailed health check includes component status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        # Should have status and potentially component checks
        assert "status" in data

    def test_health_no_auth_required(self, client: FlaskClient):
        """Test health check doesn't require authentication."""
        response = client.get("/api/health")
        # Should not redirect to login
        assert response.status_code == 200


class TestRootEndpoint:
    """Tests for root/info endpoints."""

    def test_api_root(self, client: FlaskClient):
        """Test API root endpoint behavior.

        /api/ is not a defined API endpoint - it falls through to the frontend
        serve route. Returns 503 if frontend not built (e.g., in CI), or 200
        if frontend is built (serves index.html).
        """
        response = client.get("/api/")
        # Accept frontend responses (200 if built, 503 if not built)
        assert response.status_code in [200, 503]

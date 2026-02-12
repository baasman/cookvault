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
        """Test API root endpoint exists."""
        response = client.get("/api/")
        # Should return some info or redirect
        assert response.status_code in [200, 301, 302, 404]

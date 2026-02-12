"""
Tests for authentication endpoints.
"""
import pytest
from flask.testing import FlaskClient


class TestRegistration:
    """Tests for user registration."""

    def test_register_success(self, client: FlaskClient):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "user" in data
        assert data["user"]["username"] == "newuser"
        assert data["user"]["email"] == "newuser@example.com"

    def test_register_missing_username(self, client: FlaskClient):
        """Test registration fails without username."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_register_missing_email(self, client: FlaskClient):
        """Test registration fails without email."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 400

    def test_register_missing_password(self, client: FlaskClient):
        """Test registration fails without password."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com"
            }
        )
        assert response.status_code == 400

    def test_register_short_password(self, client: FlaskClient):
        """Test registration fails with short password."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "short"
            }
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "password" in data["error"].lower()

    def test_register_invalid_email(self, client: FlaskClient):
        """Test registration fails with invalid email."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "notanemail",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 400

    def test_register_duplicate_username(self, client: FlaskClient, test_user):
        """Test registration fails with duplicate username."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",  # Same as test_user
                "email": "different@example.com",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 409
        data = response.get_json()
        assert "username" in data["error"].lower()

    def test_register_duplicate_email(self, client: FlaskClient, test_user):
        """Test registration fails with duplicate email."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "differentuser",
                "email": "test@example.com",  # Same as test_user
                "password": "securepassword123"
            }
        )
        assert response.status_code == 409
        data = response.get_json()
        assert "email" in data["error"].lower()


class TestLogin:
    """Tests for user login."""

    def test_login_with_username(self, client: FlaskClient, test_user, test_user_data):
        """Test successful login with username."""
        response = client.post(
            "/api/auth/login",
            json={
                "login": test_user_data["username"],
                "password": test_user_data["password"]
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert data["user"]["username"] == test_user_data["username"]

    def test_login_with_email(self, client: FlaskClient, test_user, test_user_data):
        """Test successful login with email."""
        response = client.post(
            "/api/auth/login",
            json={
                "login": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data

    def test_login_wrong_password(self, client: FlaskClient, test_user, test_user_data):
        """Test login fails with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={
                "login": test_user_data["username"],
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

    def test_login_nonexistent_user(self, client: FlaskClient):
        """Test login fails for nonexistent user."""
        response = client.post(
            "/api/auth/login",
            json={
                "login": "nonexistent",
                "password": "anypassword"
            }
        )
        assert response.status_code == 401

    def test_login_missing_credentials(self, client: FlaskClient):
        """Test login fails without credentials."""
        response = client.post(
            "/api/auth/login",
            json={}
        )
        assert response.status_code == 400


class TestLogout:
    """Tests for user logout."""

    def test_logout_success(self, auth_client):
        """Test successful logout."""
        response = auth_client.post("/api/auth/logout")
        assert response.status_code == 200

    def test_logout_unauthenticated(self, client: FlaskClient):
        """Test logout without authentication returns error."""
        response = client.post("/api/auth/logout")
        # Should redirect or return 401/302
        assert response.status_code in [302, 401]


class TestAuthStatus:
    """Tests for auth status endpoint."""

    def test_auth_status_authenticated(self, auth_client, test_user_data):
        """Test auth status returns user info when authenticated."""
        response = auth_client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["authenticated"] is True
        assert data["user"]["username"] == test_user_data["username"]

    def test_auth_status_unauthenticated(self, client: FlaskClient):
        """Test auth status returns unauthenticated when not logged in."""
        response = client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["authenticated"] is False


class TestCurrentUser:
    """Tests for /auth/me endpoint."""

    def test_get_current_user(self, auth_client, test_user_data):
        """Test getting current user info."""
        response = auth_client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.get_json()
        assert "user" in data
        assert data["user"]["username"] == test_user_data["username"]
        assert data["user"]["email"] == test_user_data["email"]

    def test_get_current_user_unauthenticated(self, client: FlaskClient):
        """Test getting current user without auth fails."""
        response = client.get("/api/auth/me")
        assert response.status_code in [302, 401]

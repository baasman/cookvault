"""
Tests for cookbook API endpoints.
"""

from flask.testing import FlaskClient


class TestGetCookbooks:
    """Tests for listing cookbooks."""

    def test_get_cookbooks_authenticated(self, auth_client):
        """Test getting cookbooks when authenticated."""
        response = auth_client.get("/api/cookbooks")
        assert response.status_code == 200
        data = response.get_json()
        assert "cookbooks" in data
        assert isinstance(data["cookbooks"], list)

    def test_get_cookbooks_unauthenticated(self, client: FlaskClient):
        """Test getting cookbooks without auth."""
        response = client.get("/api/cookbooks")
        # Should either redirect or return 401
        assert response.status_code in [302, 401]


class TestGetCookbook:
    """Tests for getting a single cookbook."""

    def test_get_cookbook_exists(self, auth_client, sample_cookbook):
        """Test getting an existing cookbook."""
        response = auth_client.get(f"/api/cookbooks/{sample_cookbook.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "The Joy of Cooking"
        assert data["author"] == "Irma S. Rombauer"

    def test_get_cookbook_not_found(self, auth_client):
        """Test getting a nonexistent cookbook."""
        response = auth_client.get("/api/cookbooks/99999")
        assert response.status_code == 404

    def test_get_cookbook_unauthenticated(self, client: FlaskClient, sample_cookbook):
        """Test getting cookbook without auth."""
        response = client.get(f"/api/cookbooks/{sample_cookbook.id}")
        assert response.status_code in [302, 401]


class TestCreateCookbook:
    """Tests for creating cookbooks."""

    def test_create_cookbook_success(self, auth_client):
        """Test creating a cookbook with valid data."""
        response = auth_client.post(
            "/api/cookbooks",
            json={
                "title": "My Test Cookbook",
                "author": "Test Author",
                "description": "A test cookbook",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["cookbook"]["title"] == "My Test Cookbook"
        assert data["cookbook"]["author"] == "Test Author"

    def test_create_cookbook_minimal(self, auth_client):
        """Test creating cookbook with just a title."""
        response = auth_client.post(
            "/api/cookbooks", json={"title": "Minimal Cookbook"}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["cookbook"]["title"] == "Minimal Cookbook"

    def test_create_cookbook_no_title(self, auth_client):
        """Test creating cookbook without title fails."""
        response = auth_client.post("/api/cookbooks", json={"author": "Test Author"})
        assert response.status_code == 400

    def test_create_cookbook_unauthenticated(self, client: FlaskClient):
        """Test creating cookbook without auth fails."""
        response = client.post(
            "/api/cookbooks", json={"title": "Test"}, content_type="application/json"
        )
        assert response.status_code in [302, 401]


class TestUpdateCookbook:
    """Tests for updating cookbooks."""

    def test_update_cookbook_title(self, auth_client, sample_cookbook):
        """Test updating cookbook title."""
        response = auth_client.put(
            f"/api/cookbooks/{sample_cookbook.id}",
            json={"title": "Updated Cookbook Title"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["cookbook"]["title"] == "Updated Cookbook Title"

    def test_update_cookbook_description(self, auth_client, sample_cookbook):
        """Test updating cookbook description."""
        response = auth_client.put(
            f"/api/cookbooks/{sample_cookbook.id}",
            json={"description": "New description"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["cookbook"]["description"] == "New description"

    def test_update_cookbook_not_found(self, auth_client):
        """Test updating nonexistent cookbook."""
        response = auth_client.put("/api/cookbooks/99999", json={"title": "Test"})
        assert response.status_code == 404

    def test_update_cookbook_unauthenticated(
        self, client: FlaskClient, sample_cookbook
    ):
        """Test updating cookbook without auth fails."""
        response = client.put(
            f"/api/cookbooks/{sample_cookbook.id}",
            json={"title": "Test"},
            content_type="application/json",
        )
        assert response.status_code in [302, 401]


class TestDeleteCookbook:
    """Tests for deleting cookbooks."""

    def test_delete_cookbook(self, auth_client, sample_cookbook, app):
        """Test deleting a cookbook."""
        cookbook_id = sample_cookbook.id
        response = auth_client.delete(f"/api/cookbooks/{cookbook_id}")
        assert response.status_code == 200

        # Verify it's deleted
        response = auth_client.get(f"/api/cookbooks/{cookbook_id}")
        assert response.status_code == 404

    def test_delete_cookbook_not_found(self, auth_client):
        """Test deleting nonexistent cookbook."""
        response = auth_client.delete("/api/cookbooks/99999")
        assert response.status_code == 404

    def test_delete_cookbook_unauthenticated(
        self, client: FlaskClient, sample_cookbook
    ):
        """Test deleting cookbook without auth fails."""
        response = client.delete(f"/api/cookbooks/{sample_cookbook.id}")
        assert response.status_code in [302, 401]


class TestCookbookRecipes:
    """Tests for cookbook recipe management."""

    def test_get_cookbook_recipes(self, auth_client, sample_cookbook):
        """Test getting recipes in a cookbook."""
        response = auth_client.get(f"/api/cookbooks/{sample_cookbook.id}/recipes")
        assert response.status_code == 200
        data = response.get_json()
        assert "recipes" in data
        assert isinstance(data["recipes"], list)

    def test_add_recipe_to_cookbook(self, auth_client, sample_cookbook, sample_recipe):
        """Test linking a recipe to a cookbook."""
        # Link recipe to cookbook using the recipes endpoint
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}/cookbook",
            json={"cookbook_id": sample_cookbook.id},
        )
        assert response.status_code == 200

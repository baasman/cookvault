"""
Tests for recipe API endpoints.
"""
import pytest
from flask.testing import FlaskClient


class TestGetRecipes:
    """Tests for listing recipes."""

    def test_get_recipes_authenticated(self, auth_client):
        """Test getting recipes when authenticated."""
        response = auth_client.get("/api/recipes")
        assert response.status_code == 200
        data = response.get_json()
        assert "recipes" in data
        assert isinstance(data["recipes"], list)

    def test_get_recipes_unauthenticated(self, client: FlaskClient):
        """Test getting recipes without auth redirects."""
        response = client.get("/api/recipes")
        assert response.status_code in [302, 401]

    def test_get_recipes_with_data(self, auth_client, sample_recipe):
        """Test getting recipes returns created recipes."""
        response = auth_client.get("/api/recipes")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["recipes"]) >= 1
        # Find our test recipe
        recipe_titles = [r["title"] for r in data["recipes"]]
        assert "Test Recipe" in recipe_titles

    def test_get_recipes_pagination(self, auth_client):
        """Test recipe pagination parameters."""
        response = auth_client.get("/api/recipes?page=1&per_page=5")
        assert response.status_code == 200
        data = response.get_json()
        assert "recipes" in data
        assert "total" in data or "pagination" in data or "page" in data


class TestGetRecipe:
    """Tests for getting a single recipe."""

    def test_get_recipe_exists(self, auth_client, sample_recipe):
        """Test getting an existing recipe."""
        response = auth_client.get(f"/api/recipes/{sample_recipe.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Test Recipe"
        assert data["description"] == "A test recipe"

    def test_get_recipe_not_found(self, auth_client):
        """Test getting a nonexistent recipe."""
        response = auth_client.get("/api/recipes/99999")
        assert response.status_code == 404

    def test_get_recipe_unauthenticated(self, client: FlaskClient, sample_recipe):
        """Test getting recipe without auth (private recipe)."""
        response = client.get(f"/api/recipes/{sample_recipe.id}")
        # Private recipe should not be accessible without auth
        assert response.status_code in [302, 401, 403, 404]


class TestCreateRecipe:
    """Tests for creating recipes."""

    def test_create_empty_recipe(self, auth_client):
        """Test creating an empty recipe with just a title."""
        response = auth_client.post(
            "/api/recipes",
            json={"title": "My New Recipe"}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["recipe"]["title"] == "My New Recipe"

    def test_create_recipe_no_title(self, auth_client):
        """Test creating recipe without title fails."""
        response = auth_client.post(
            "/api/recipes",
            json={}
        )
        assert response.status_code == 400

    def test_create_recipe_unauthenticated(self, client: FlaskClient):
        """Test creating recipe without auth fails."""
        response = client.post(
            "/api/recipes",
            json={"title": "Test"},
            content_type="application/json"
        )
        assert response.status_code in [302, 401]


class TestUpdateRecipe:
    """Tests for updating recipes."""

    def test_update_recipe_title(self, auth_client, sample_recipe):
        """Test updating recipe title."""
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}",
            json={"title": "Updated Recipe Title"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["recipe"]["title"] == "Updated Recipe Title"

    def test_update_recipe_description(self, auth_client, sample_recipe):
        """Test updating recipe description."""
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}",
            json={"description": "New description"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["recipe"]["description"] == "New description"

    def test_update_recipe_times(self, auth_client, sample_recipe):
        """Test updating prep and cook times."""
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}",
            json={
                "prep_time": 20,
                "cook_time": 45
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["recipe"]["prep_time"] == 20
        assert data["recipe"]["cook_time"] == 45

    def test_update_recipe_not_found(self, auth_client):
        """Test updating nonexistent recipe."""
        response = auth_client.put(
            "/api/recipes/99999",
            json={"title": "Test"}
        )
        assert response.status_code == 404

    def test_update_recipe_unauthenticated(self, client: FlaskClient, sample_recipe):
        """Test updating recipe without auth fails."""
        response = client.put(
            f"/api/recipes/{sample_recipe.id}",
            json={"title": "Test"},
            content_type="application/json"
        )
        assert response.status_code in [302, 401]


class TestDeleteRecipe:
    """Tests for deleting recipes."""

    def test_delete_recipe(self, auth_client, sample_recipe, app):
        """Test deleting a recipe."""
        recipe_id = sample_recipe.id
        response = auth_client.delete(f"/api/recipes/{recipe_id}")
        assert response.status_code == 200

        # Verify it's deleted
        response = auth_client.get(f"/api/recipes/{recipe_id}")
        assert response.status_code == 404

    def test_delete_recipe_not_found(self, auth_client):
        """Test deleting nonexistent recipe."""
        response = auth_client.delete("/api/recipes/99999")
        assert response.status_code == 404

    def test_delete_recipe_unauthenticated(self, client: FlaskClient, sample_recipe):
        """Test deleting recipe without auth fails."""
        response = client.delete(f"/api/recipes/{sample_recipe.id}")
        assert response.status_code in [302, 401]


class TestRecipeInstructions:
    """Tests for recipe instructions."""

    def test_update_instructions(self, auth_client, sample_recipe):
        """Test updating recipe instructions."""
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}/instructions",
            json={
                "instructions": [
                    "Step 1: Preheat oven",
                    "Step 2: Mix ingredients",
                    "Step 3: Bake"
                ]
            }
        )
        assert response.status_code == 200

        # Verify instructions were updated
        response = auth_client.get(f"/api/recipes/{sample_recipe.id}")
        data = response.get_json()
        assert len(data["instructions"]) == 3


class TestRecipeIngredients:
    """Tests for recipe ingredients."""

    def test_update_ingredients(self, auth_client, sample_recipe):
        """Test updating recipe ingredients."""
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}/ingredients",
            json={
                "ingredients": [
                    {"name": "butter", "quantity": 1, "unit": "cup"},
                    {"name": "sugar", "quantity": 2, "unit": "cups"},
                ]
            }
        )
        assert response.status_code == 200


class TestRecipeTags:
    """Tests for recipe tags."""

    def test_update_tags(self, auth_client, sample_recipe):
        """Test updating recipe tags."""
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}/tags",
            json={"tags": ["breakfast", "healthy", "quick"]}
        )
        assert response.status_code == 200


class TestRecipePrivacy:
    """Tests for recipe privacy settings."""

    def test_make_recipe_public(self, auth_client, sample_recipe):
        """Test making a recipe public."""
        # Make public (requires copyright consent object with all fields)
        copyright_consent = {
            "rightsToShare": True,
            "understandsPublic": True,
            "personalUseOnly": True,
            "noCopyrightViolation": True,
        }
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}/privacy",
            json={"is_public": True, "copyright_consent": copyright_consent}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["recipe"]["is_public"] is True

    def test_cannot_make_public_without_consent(self, auth_client, sample_recipe):
        """Test that making public without consent fails."""
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}/privacy",
            json={"is_public": True}  # Missing copyright_consent
        )
        assert response.status_code == 400

    def test_cannot_make_public_recipe_private(self, auth_client, sample_recipe):
        """Test that public recipes cannot be made private."""
        # First make it public
        copyright_consent = {
            "rightsToShare": True,
            "understandsPublic": True,
            "personalUseOnly": True,
            "noCopyrightViolation": True,
        }
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}/privacy",
            json={"is_public": True, "copyright_consent": copyright_consent}
        )
        assert response.status_code == 200

        # Try to make it private - should fail
        response = auth_client.put(
            f"/api/recipes/{sample_recipe.id}/privacy",
            json={"is_public": False}
        )
        assert response.status_code == 400


class TestRecipeSearch:
    """Tests for recipe search."""

    def test_search_recipes(self, auth_client, sample_recipe):
        """Test searching recipes."""
        response = auth_client.get("/api/recipes?search=Test")
        assert response.status_code == 200
        data = response.get_json()
        assert "recipes" in data

    def test_search_no_results(self, auth_client):
        """Test search with no matching results."""
        response = auth_client.get("/api/recipes?search=xyznonexistent123")
        assert response.status_code == 200
        data = response.get_json()
        assert data["recipes"] == []

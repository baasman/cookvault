"""
Test fixtures for the cookbook creator application.
"""

import os
import tempfile
import typing as t
from flask.testing import FlaskClient

import pytest
from app import create_app, db
from app.models import Recipe, RecipeImage, Tag, Instruction, Ingredient, Cookbook
from app.models.user import User, UserStatus, UserRole


@pytest.fixture
def app() -> t.Generator:
    """Create application for testing with a temporary database."""
    db_fd, db_path = tempfile.mkstemp()
    upload_dir = tempfile.mkdtemp()
    app = create_app("testing")
    app.config.update(
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "UPLOAD_FOLDER": upload_dir,
            "TESTING": True,
            "DEBUG": True,  # Disable Talisman's force_https in tests
            "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
            "REQUIRE_EMAIL_VERIFICATION": False,  # Skip email verification in tests
        }
    )
    # Also set app.debug directly since Talisman checks this
    app.debug = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app) -> FlaskClient:
    """Create a test client without authentication."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a CLI test runner."""
    return app.test_cli_runner()


# =============================================================================
# Authentication Fixtures
# =============================================================================


class TestUser:
    """Simple data holder for test user to avoid SQLAlchemy session issues."""

    def __init__(self, id: int, username: str, email: str):
        self.id = id
        self.username = username
        self.email = email


@pytest.fixture
def test_user(app) -> TestUser:
    """Create a verified, active test user."""
    with app.app_context():
        user = User(
            username="testuser",
            email="test@example.com",
            status=UserStatus.ACTIVE,
            role=UserRole.USER,
        )
        user.set_password("testpassword123")
        db.session.add(user)
        db.session.commit()

        # Refresh to get the ID
        db.session.refresh(user)
        return TestUser(id=user.id, username=user.username, email=user.email)


@pytest.fixture
def test_user_data() -> dict:
    """Return test user credentials for login."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    }


@pytest.fixture
def auth_token(client, test_user, test_user_data) -> str:
    """Get a valid JWT token for the test user."""
    response = client.post(
        "/api/auth/login",
        json={
            "login": test_user_data["username"],
            "password": test_user_data["password"],
        },
    )
    assert response.status_code == 200, f"Login failed: {response.get_json()}"
    data = response.get_json()
    return data["access_token"]


@pytest.fixture
def auth_headers(auth_token) -> dict:
    """Return headers with JWT authentication."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class AuthenticatedClient:
    """A test client wrapper that includes authentication headers."""

    def __init__(self, client: FlaskClient, headers: dict):
        self._client = client
        self._headers = headers

    def get(self, *args, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.post(*args, **kwargs)

    def put(self, *args, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.put(*args, **kwargs)

    def delete(self, *args, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.delete(*args, **kwargs)

    def patch(self, *args, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.patch(*args, **kwargs)


@pytest.fixture
def auth_client(client, auth_headers) -> AuthenticatedClient:
    """Create an authenticated test client."""
    return AuthenticatedClient(client, auth_headers)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


class SampleRecipe:
    """Simple data holder for sample recipe to avoid SQLAlchemy session issues."""

    def __init__(self, id: int, title: str, description: str, user_id: int):
        self.id = id
        self.title = title
        self.description = description
        self.user_id = user_id


@pytest.fixture
def sample_recipe(app, test_user) -> SampleRecipe:
    """Create a sample recipe with ingredients and instructions."""
    with app.app_context():
        # Re-fetch user in this context
        user = db.session.get(User, test_user.id)

        recipe = Recipe(
            title="Test Recipe",
            description="A test recipe",
            prep_time=15,
            cook_time=30,
            servings=4,
            difficulty="easy",
            user_id=user.id,
            uploaded_by_id=user.id,
            is_public=False,
        )
        db.session.add(recipe)
        db.session.flush()

        # Add instructions
        instruction1 = Instruction(
            recipe_id=recipe.id, step_number=1, text="Mix ingredients"
        )
        instruction2 = Instruction(
            recipe_id=recipe.id, step_number=2, text="Bake for 30 minutes"
        )
        db.session.add_all([instruction1, instruction2])

        # Add tags
        tag1 = Tag(recipe_id=recipe.id, name="dessert")
        tag2 = Tag(recipe_id=recipe.id, name="quick")
        db.session.add_all([tag1, tag2])

        # Add ingredients
        ingredient1 = Ingredient(name="flour")
        ingredient2 = Ingredient(name="eggs")
        db.session.add_all([ingredient1, ingredient2])
        db.session.flush()

        # Create ingredient associations
        from app.models.recipe import recipe_ingredients

        stmt1 = recipe_ingredients.insert().values(
            recipe_id=recipe.id,
            ingredient_id=ingredient1.id,
            quantity=1.0,
            unit="cup",
            order=1,
        )
        stmt2 = recipe_ingredients.insert().values(
            recipe_id=recipe.id,
            ingredient_id=ingredient2.id,
            quantity=2.0,
            unit="pieces",
            order=2,
        )
        db.session.execute(stmt1)
        db.session.execute(stmt2)
        db.session.commit()

        # Return a simple data holder instead of the ORM object
        return SampleRecipe(
            id=recipe.id,
            title=recipe.title,
            description=recipe.description,
            user_id=recipe.user_id,
        )


class SampleCookbook:
    """Simple data holder for sample cookbook to avoid SQLAlchemy session issues."""

    def __init__(
        self, id: int, title: str, author: str, description: str, user_id: int
    ):
        self.id = id
        self.title = title
        self.author = author
        self.description = description
        self.user_id = user_id


@pytest.fixture
def sample_cookbook(app, test_user) -> SampleCookbook:
    """Create a sample cookbook owned by the test user."""
    with app.app_context():
        # Re-fetch user in this context
        user = db.session.get(User, test_user.id)

        cookbook = Cookbook(
            title="The Joy of Cooking",
            author="Irma S. Rombauer",
            description="Classic American cookbook",
            publisher="Scribner",
            user_id=user.id,
        )
        db.session.add(cookbook)
        db.session.commit()

        return SampleCookbook(
            id=cookbook.id,
            title=cookbook.title,
            author=cookbook.author,
            description=cookbook.description,
            user_id=cookbook.user_id,
        )


@pytest.fixture
def sample_image() -> RecipeImage:
    """Create a sample recipe image object."""
    return RecipeImage(
        filename="test_image.jpg",
        original_filename="original_test.jpg",
        file_path="/path/to/test.jpg",
        file_size=1024,
        content_type="image/jpeg",
    )


@pytest.fixture
def second_user(app) -> TestUser:
    """Create a second test user for permission testing."""
    with app.app_context():
        user = User(
            username="otheruser",
            email="other@example.com",
            status=UserStatus.ACTIVE,
            role=UserRole.USER,
        )
        user.set_password("otherpassword123")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return TestUser(id=user.id, username=user.username, email=user.email)

import os
import tempfile
from pathlib import Path
import typing as t
from flask.testing import FlaskClient

import pytest
from app import create_app, db
from app.models import Recipe, RecipeImage, ProcessingJob, Tag, Instruction, Ingredient, Cookbook


@pytest.fixture
def app() -> t.Generator:
    db_fd, db_path = tempfile.mkstemp()
    upload_dir = tempfile.mkdtemp()
    app = create_app("testing")
    app.config.update(
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "UPLOAD_FOLDER": upload_dir,
            "TESTING": True,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def sample_recipe(app) -> Recipe:
    with app.app_context():
        recipe = Recipe(
            title="Test Recipe",
            description="A test recipe",
            prep_time=15,
            cook_time=30,
            servings=4,
            difficulty="easy",
        )
        db.session.add(recipe)
        db.session.flush()
        
        # Add instructions
        instruction1 = Instruction(
            recipe_id=recipe.id,
            step_number=1,
            text="Mix ingredients"
        )
        instruction2 = Instruction(
            recipe_id=recipe.id,
            step_number=2,
            text="Bake for 30 minutes"
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
            order=1
        )
        stmt2 = recipe_ingredients.insert().values(
            recipe_id=recipe.id,
            ingredient_id=ingredient2.id,
            quantity=2.0,
            unit="pieces",
            order=2
        )
        db.session.execute(stmt1)
        db.session.execute(stmt2)
        db.session.commit()
        
        return recipe


@pytest.fixture
def sample_cookbook(app) -> Cookbook:
    with app.app_context():
        cookbook = Cookbook(
            title="The Joy of Cooking",
            author="Irma S. Rombauer",
            description="Classic American cookbook",
            publisher="Scribner"
        )
        db.session.add(cookbook)
        db.session.commit()
        return cookbook


@pytest.fixture
def sample_image() -> RecipeImage:
    return RecipeImage(
        filename="test_image.jpg",
        original_filename="original_test.jpg",
        file_path="/path/to/test.jpg",
        file_size=1024,
        content_type="image/jpeg",
    )

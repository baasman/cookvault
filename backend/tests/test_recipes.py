import io
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from flask.testing import FlaskClient

import pytest
from app import db
from app.models import Recipe, RecipeImage, ProcessingJob, ProcessingStatus, Tag, Instruction, Ingredient, Cookbook


class TestGetRecipes:
    def test_get_recipes_empty(self, client: FlaskClient) -> None:
        response = client.get("/api/recipes")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["recipes"] == []
        assert data["total"] == 0
        assert data["pages"] == 0
        assert data["current_page"] == 1

    def test_get_recipes_with_data(
        self, client: FlaskClient, sample_recipe: Recipe
    ) -> None:
        with client.application.app_context():
            db.session.add(sample_recipe)
            db.session.commit()

        response = client.get("/api/recipes")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["recipes"]) == 1
        assert data["recipes"][0]["title"] == "Test Recipe"
        assert data["total"] == 1

    def test_get_recipes_pagination(self, client: FlaskClient) -> None:
        with client.application.app_context():
            for i in range(15):
                recipe = Recipe(
                    title=f"Recipe {i}",
                    description="Test recipe description",
                )
                db.session.add(recipe)
                db.session.flush()
                
                # Add instruction
                instruction = Instruction(
                    recipe_id=recipe.id,
                    step_number=1,
                    text="Test instruction"
                )
                db.session.add(instruction)
            db.session.commit()

        response = client.get("/api/recipes?page=2&per_page=5")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["recipes"]) == 5
        assert data["total"] == 15
        assert data["pages"] == 3
        assert data["current_page"] == 2


class TestGetRecipe:
    def test_get_recipe_exists(
        self, client: FlaskClient, sample_recipe: Recipe
    ) -> None:
        with client.application.app_context():
            db.session.add(sample_recipe)
            db.session.commit()
            recipe_id = sample_recipe.id

        response = client.get(f"/api/recipes/{recipe_id}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["title"] == "Test Recipe"
        assert data["id"] == recipe_id

    def test_get_recipe_not_found(self, client: FlaskClient) -> None:
        response = client.get("/api/recipes/999")
        assert response.status_code == 404


class TestUploadRecipe:
    def test_upload_no_file(self, client: FlaskClient) -> None:
        response = client.post("/api/recipes/upload")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "No image file provided" in data["error"]

    def test_upload_empty_filename(self, client: FlaskClient) -> None:
        data = {"image": (io.BytesIO(b"fake image data"), "")}
        response = client.post("/api/recipes/upload", data=data)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "No file selected" in data["error"]

    def test_upload_invalid_file_type(self, client: FlaskClient) -> None:
        data = {"image": (io.BytesIO(b"fake data"), "test.txt")}
        response = client.post("/api/recipes/upload", data=data)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "File type not allowed" in data["error"]

    @patch("app.api.recipes._process_recipe_image")
    def test_upload_valid_file(self, mock_process, client: FlaskClient) -> None:  # type: ignore
        mock_process.return_value = None

        data = {"image": (io.BytesIO(b"fake image data"), "test.jpg")}
        response = client.post(
            "/api/recipes/upload", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert "Image uploaded successfully" in response_data["message"]
        assert "job_id" in response_data
        assert "image_id" in response_data
        assert response_data["cookbook"] is None
        assert response_data["page_number"] is None

    @patch("app.api.recipes._process_recipe_image")
    def test_upload_with_cookbook_info(self, mock_process, client: FlaskClient, sample_cookbook: Cookbook) -> None:
        mock_process.return_value = None

        with client.application.app_context():
            db.session.add(sample_cookbook)
            db.session.commit()
            cookbook_id = sample_cookbook.id

        data = {
            "image": (io.BytesIO(b"fake image data"), "test.jpg"),
            "cookbook_id": str(cookbook_id),
            "page_number": "42"
        }
        response = client.post(
            "/api/recipes/upload", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert "Image uploaded successfully" in response_data["message"]
        assert response_data["cookbook"]["title"] == "The Joy of Cooking"
        assert response_data["page_number"] == 42

    @patch("app.api.recipes._process_recipe_image")
    def test_upload_with_invalid_cookbook_id(self, mock_process, client: FlaskClient) -> None:
        mock_process.return_value = None

        data = {
            "image": (io.BytesIO(b"fake image data"), "test.jpg"),
            "cookbook_id": "999"
        }
        response = client.post(
            "/api/recipes/upload", data=data, content_type="multipart/form-data"
        )
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "Cookbook not found" in response_data["error"]

    @patch("app.api.recipes.Path.stat")
    @patch("app.api.recipes._process_recipe_image")
    def test_upload_creates_database_records(
        self, mock_process, mock_stat, client: FlaskClient
    ) -> None:
        mock_process.return_value = None
        mock_stat.return_value = MagicMock(st_size=1024)

        data = {"image": (io.BytesIO(b"fake image data"), "test.jpg")}
        response = client.post(
            "/api/recipes/upload", data=data, content_type="multipart/form-data"
        )

        with client.application.app_context():
            images = RecipeImage.query.all()
            jobs = ProcessingJob.query.all()

            assert len(images) == 1
            assert len(jobs) == 1
            assert images[0].original_filename == "test.jpg"
            assert jobs[0].image_id == images[0].id


class TestGetProcessingJob:
    def test_get_job_exists(
        self, client: FlaskClient, sample_image: RecipeImage
    ) -> None:
        with client.application.app_context():
            db.session.add(sample_image)
            db.session.flush()

            job = ProcessingJob(
                image_id=sample_image.id, status=ProcessingStatus.PENDING
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["id"] == job_id
        assert data["status"] == "pending"

    def test_get_job_not_found(self, client: FlaskClient) -> None:
        response = client.get("/api/jobs/999")
        assert response.status_code == 404


class TestProcessRecipeImage:
    @patch("app.api.recipes.OCRService")
    @patch("app.api.recipes.RecipeParser")
    def test_process_recipe_image_success(
        self, mock_parser_class, mock_ocr_class, client: FlaskClient, sample_image: RecipeImage
    ) -> None:
        from app.api.recipes import _process_recipe_image

        # Mock OCR service
        mock_ocr = MagicMock()
        mock_ocr.extract_text_from_image.return_value = "Test extracted text"
        mock_ocr_class.return_value = mock_ocr

        # Mock recipe parser
        mock_parser = MagicMock()
        mock_parser.parse_recipe_text.return_value = {
            "title": "Mock Recipe",
            "description": "A mocked recipe",
            "instructions": ["Step 1: Mix", "Step 2: Bake"],
            "tags": ["test", "mock"],
            "ingredients": ["1 cup flour", "2 eggs"],
            "prep_time": 10,
            "cook_time": 20,
            "servings": 4,
            "difficulty": "easy"
        }
        mock_parser_class.return_value = mock_parser

        with client.application.app_context():
            db.session.add(sample_image)
            db.session.flush()

            job = ProcessingJob(
                image_id=sample_image.id, status=ProcessingStatus.PENDING
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            _process_recipe_image(job_id)

            updated_job = ProcessingJob.query.get(job_id)
            assert updated_job.status == ProcessingStatus.COMPLETED
            assert updated_job.recipe_id is not None

            recipe = Recipe.query.get(updated_job.recipe_id)
            assert recipe is not None
            assert recipe.title == "Mock Recipe"
            assert recipe.description == "A mocked recipe"
            
            # Check instructions were created
            instructions = Instruction.query.filter_by(recipe_id=recipe.id).order_by(Instruction.step_number).all()
            assert len(instructions) == 2
            assert instructions[0].text == "Step 1: Mix"
            assert instructions[1].text == "Step 2: Bake"
            
            # Check tags were created
            tags = Tag.query.filter_by(recipe_id=recipe.id).all()
            assert len(tags) == 2
            tag_names = [tag.name for tag in tags]
            assert "test" in tag_names
            assert "mock" in tag_names
            
            # Check ingredients were created
            ingredients = Ingredient.query.all()
            assert len(ingredients) == 2
            ingredient_names = [ing.name for ing in ingredients]
            assert "flour" in ingredient_names
            assert "eggs" in ingredient_names

    def test_process_recipe_image_nonexistent_job(self, client: FlaskClient) -> None:
        from app.api.recipes import _process_recipe_image

        with client.application.app_context():
            _process_recipe_image(999)

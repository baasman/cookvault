"""
Tests for recipe upload and processing functionality.

Note: Basic recipe CRUD tests are in test_api_recipes.py.
These tests focus on file upload and image processing.
"""

import io
import json
from unittest.mock import patch, MagicMock

from app import db
from app.models import (
    RecipeImage,
    ProcessingJob,
    ProcessingStatus,
)


def _auth_header_only(auth_headers):
    """Return only the Authorization header (no Content-Type) for multipart uploads."""
    return {"Authorization": auth_headers["Authorization"]}


class TestUploadRecipe:
    def test_upload_no_file(self, client, auth_headers) -> None:
        response = client.post(
            "/api/recipes/upload", headers=_auth_header_only(auth_headers)
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "No image file provided" in data["error"]

    def test_upload_empty_filename(self, client, auth_headers) -> None:
        data = {"image": (io.BytesIO(b"fake image data"), "")}
        response = client.post(
            "/api/recipes/upload",
            data=data,
            headers=_auth_header_only(auth_headers),
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "No file selected" in data["error"]

    def test_upload_invalid_file_type(self, client, auth_headers) -> None:
        data = {"image": (io.BytesIO(b"fake data"), "test.txt")}
        response = client.post(
            "/api/recipes/upload",
            data=data,
            headers=_auth_header_only(auth_headers),
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "File type not allowed" in data["error"]

    @patch("app.tasks.recipe_tasks.process_single_recipe_task")
    def test_upload_valid_file(self, mock_task, client, auth_headers) -> None:
        mock_task.delay = MagicMock()

        data = {"image": (io.BytesIO(b"fake image data"), "test.jpg")}
        response = client.post(
            "/api/recipes/upload",
            data=data,
            content_type="multipart/form-data",
            headers=_auth_header_only(auth_headers),
        )
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert "Image uploaded successfully" in response_data["message"]
        assert "job_id" in response_data
        assert "image_id" in response_data
        assert response_data["cookbook"] is None

    @patch("app.tasks.recipe_tasks.process_single_recipe_task")
    def test_upload_with_cookbook_info(
        self, mock_task, client, auth_headers, sample_cookbook
    ) -> None:
        mock_task.delay = MagicMock()

        data = {
            "image": (io.BytesIO(b"fake image data"), "test.jpg"),
            "cookbook_id": str(sample_cookbook.id),
        }
        response = client.post(
            "/api/recipes/upload",
            data=data,
            content_type="multipart/form-data",
            headers=_auth_header_only(auth_headers),
        )
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert "Image uploaded successfully" in response_data["message"]
        assert response_data["cookbook"]["title"] == "The Joy of Cooking"

    @patch("app.tasks.recipe_tasks.process_single_recipe_task")
    def test_upload_with_invalid_cookbook_id(
        self, mock_task, client, auth_headers
    ) -> None:
        mock_task.delay = MagicMock()

        data = {
            "image": (io.BytesIO(b"fake image data"), "test.jpg"),
            "cookbook_id": "999",
        }
        response = client.post(
            "/api/recipes/upload",
            data=data,
            content_type="multipart/form-data",
            headers=_auth_header_only(auth_headers),
        )
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "Cookbook not found" in response_data["error"]

    @patch("app.tasks.recipe_tasks.process_single_recipe_task")
    def test_upload_creates_database_records(
        self, mock_task, client, auth_headers, app
    ) -> None:
        mock_task.delay = MagicMock()

        data = {"image": (io.BytesIO(b"fake image data"), "test.jpg")}
        client.post(
            "/api/recipes/upload",
            data=data,
            content_type="multipart/form-data",
            headers=_auth_header_only(auth_headers),
        )

        with app.app_context():
            images = RecipeImage.query.all()
            jobs = ProcessingJob.query.all()

            assert len(images) == 1
            assert len(jobs) == 1
            assert images[0].original_filename == "test.jpg"
            assert jobs[0].image_id == images[0].id

    def test_upload_requires_auth(self, client) -> None:
        response = client.post("/api/recipes/upload")
        assert response.status_code == 401


class TestGetProcessingJob:
    def test_get_job_exists(self, app, auth_client, sample_image: RecipeImage) -> None:
        with app.app_context():
            db.session.add(sample_image)
            db.session.flush()

            job = ProcessingJob(
                image_id=sample_image.id, status=ProcessingStatus.PENDING
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        response = auth_client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200

    def test_get_job_not_found(self, auth_client) -> None:
        response = auth_client.get("/api/jobs/999")
        assert response.status_code == 404

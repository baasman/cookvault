"""
Tests for the POST /recipes/upload-youtube API endpoint.

Uses the conftest fixtures (app, client, auth_headers, etc.).
Celery task is mocked to avoid actual processing.
"""

from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.models.video_job import VideoProcessingJob, VideoProcessingStatus


class TestUploadYouTubeEndpoint:
    """Test the YouTube upload API endpoint."""

    # ── Validation errors ───────────────────────────────────────────

    def test_missing_url_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/recipes/upload-youtube",
            json={},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_empty_url_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/recipes/upload-youtube",
            json={"url": ""},
        )
        assert response.status_code == 400

    def test_invalid_non_youtube_url_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/recipes/upload-youtube",
            json={"url": "https://www.vimeo.com/12345"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "Not a valid YouTube" in data["error"]

    def test_playlist_url_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/recipes/upload-youtube",
            json={
                "url": "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
            },
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "playlist" in data["error"].lower()

    # ── Successful submission ───────────────────────────────────────

    @patch("app.tasks.recipe_tasks.process_youtube_recipe_task")
    def test_valid_url_creates_job_and_queues_task(
        self, mock_task, auth_client, app, test_user
    ):
        mock_task.delay = MagicMock()

        response = auth_client.post(
            "/api/recipes/upload-youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )

        assert response.status_code == 202
        data = response.get_json()
        assert "video_job_id" in data
        assert data["status"] == "pending"
        assert "message" in data

        # Verify Celery task was queued
        mock_task.delay.assert_called_once()

        # Verify job was created in DB
        with app.app_context():
            job = db.session.get(VideoProcessingJob, data["video_job_id"])
            assert job is not None
            assert job.youtube_video_id == "dQw4w9WgXcQ"
            assert job.youtube_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            assert job.user_id == test_user.id
            assert job.video_filename == "youtube_dQw4w9WgXcQ"

    @patch("app.tasks.recipe_tasks.process_youtube_recipe_task")
    def test_valid_url_with_cookbook_id(
        self, mock_task, auth_client, app, test_user, sample_cookbook
    ):
        mock_task.delay = MagicMock()

        response = auth_client.post(
            "/api/recipes/upload-youtube",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "cookbook_id": sample_cookbook.id,
            },
        )

        assert response.status_code == 202
        data = response.get_json()

        with app.app_context():
            job = db.session.get(VideoProcessingJob, data["video_job_id"])
            assert job.cookbook_id == sample_cookbook.id

    @patch("app.tasks.recipe_tasks.process_youtube_recipe_task")
    def test_valid_url_with_create_new_cookbook(
        self, mock_task, auth_client, app, test_user
    ):
        mock_task.delay = MagicMock()

        response = auth_client.post(
            "/api/recipes/upload-youtube",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "create_new_cookbook": True,
                "new_cookbook_title": "YouTube Recipes",
            },
        )

        assert response.status_code == 202
        data = response.get_json()

        with app.app_context():
            job = db.session.get(VideoProcessingJob, data["video_job_id"])
            assert job.cookbook_id is not None

    @patch("app.tasks.recipe_tasks.process_youtube_recipe_task")
    def test_valid_short_url(self, mock_task, auth_client, app, test_user):
        mock_task.delay = MagicMock()

        response = auth_client.post(
            "/api/recipes/upload-youtube",
            json={"url": "https://youtu.be/dQw4w9WgXcQ"},
        )

        assert response.status_code == 202
        data = response.get_json()

        with app.app_context():
            job = db.session.get(VideoProcessingJob, data["video_job_id"])
            assert job.youtube_video_id == "dQw4w9WgXcQ"

    # ── Authentication ──────────────────────────────────────────────

    def test_unauthenticated_returns_401(self, client):
        response = client.post(
            "/api/recipes/upload-youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            content_type="application/json",
        )
        assert response.status_code == 401

    # ── Video job status works for YouTube jobs ─────────────────────

    @patch("app.tasks.recipe_tasks.process_youtube_recipe_task")
    def test_video_job_status_returns_youtube_fields(
        self, mock_task, auth_client, app, test_user
    ):
        mock_task.delay = MagicMock()

        # Create a YouTube job
        create_response = auth_client.post(
            "/api/recipes/upload-youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert create_response.status_code == 202
        job_id = create_response.get_json()["video_job_id"]

        # Check status
        status_response = auth_client.get(
            f"/api/recipes/video-job-status/{job_id}"
        )
        assert status_response.status_code == 200
        data = status_response.get_json()
        assert data["youtube_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert data["youtube_video_id"] == "dQw4w9WgXcQ"
        assert data["status"] == "pending"

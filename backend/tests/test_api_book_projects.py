"""Tests for the BookProject API endpoints (organizer + guest-via-share-token)."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient

from app import db
from app.models import (
    BookProject,
    GuestContributor,
    ProjectShareLink,
    ProjectStatus,
    ProjectType,
    Recipe,
)


def _make_share_link(project, **kwargs):
    """Helper that creates a persisted ProjectShareLink for ``project``."""
    defaults = {
        "project_id": project.id,
        "token": kwargs.pop("token", "testtoken-" + str(project.id)),
    }
    defaults.update(kwargs)
    link = ProjectShareLink(**defaults)
    db.session.add(link)
    db.session.commit()
    return link


_FAKE_PARSED_RECIPE = {
    "title": "Grandma's Apple Pie",
    "description": "Old family recipe",
    "prep_time": 30,
    "cook_time": 60,
    "servings": 8,
    "difficulty": "medium",
    "course_type": "dessert",
    "ingredients": [
        {"name": "flour", "quantity": 2.0, "unit": "cup"},
        {"name": "apples", "quantity": 6, "unit": "whole"},
    ],
    "instructions": ["Mix flour", "Add apples", "Bake until golden"],
    "tags": ["dessert", "fall"],
}


def _make_project(test_user, **kwargs):
    """Helper that returns a persisted BookProject owned by test_user."""
    defaults = {
        "owner_user_id": test_user.id,
        "title": "Test Wedding Book",
        "project_type": ProjectType.WEDDING,
    }
    defaults.update(kwargs)
    project = BookProject(**defaults)
    db.session.add(project)
    db.session.commit()
    return project


class TestCreateBookProject:
    def test_create_minimal(self, auth_client):
        response = auth_client.post(
            "/api/book-projects/",
            json={"title": "Sarah & Maya's Recipe Book"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["project"]["title"] == "Sarah & Maya's Recipe Book"
        assert data["project"]["project_type"] == "general"
        assert data["project"]["status"] == "collecting"
        assert data["project"]["honorees"] == []

    def test_create_full(self, auth_client):
        response = auth_client.post(
            "/api/book-projects/",
            json={
                "title": "Wedding Cookbook",
                "subtitle": "A gift from your guests",
                "project_type": "wedding",
                "dedication": "For Sarah and Maya",
                "honorees": ["Sarah", "Maya"],
                "occasion_date": "2026-08-15",
                "submission_deadline": "2026-07-15",
                "metadata": {"venue": "Lake House"},
            },
        )
        assert response.status_code == 201
        proj = response.get_json()["project"]
        assert proj["project_type"] == "wedding"
        assert proj["honorees"] == ["Sarah", "Maya"]
        assert proj["occasion_date"] == "2026-08-15"
        assert proj["submission_deadline"] == "2026-07-15"
        assert proj["metadata"] == {"venue": "Lake House"}

    def test_create_honorees_from_csv_string(self, auth_client):
        response = auth_client.post(
            "/api/book-projects/",
            json={"title": "Anniversary Book", "honorees": "John, Jane"},
        )
        assert response.status_code == 201
        assert response.get_json()["project"]["honorees"] == ["John", "Jane"]

    def test_create_missing_title(self, auth_client):
        response = auth_client.post("/api/book-projects/", json={})
        assert response.status_code == 400

    def test_create_empty_title(self, auth_client):
        response = auth_client.post(
            "/api/book-projects/", json={"title": "   "}
        )
        assert response.status_code == 400

    def test_create_invalid_project_type(self, auth_client):
        response = auth_client.post(
            "/api/book-projects/",
            json={"title": "Test", "project_type": "graduation"},
        )
        assert response.status_code == 400

    def test_create_unauthenticated(self, client: FlaskClient):
        response = client.post("/api/book-projects/", json={"title": "Test"})
        assert response.status_code in (401, 302)


class TestListBookProjects:
    def test_list_empty(self, auth_client):
        response = auth_client.get("/api/book-projects/")
        assert response.status_code == 200
        assert response.get_json()["projects"] == []

    def test_list_returns_owned_only(self, auth_client, test_user, second_user):
        own = _make_project(test_user, title="Mine")
        _make_project(second_user, title="Theirs")
        response = auth_client.get("/api/book-projects/")
        assert response.status_code == 200
        projects = response.get_json()["projects"]
        assert len(projects) == 1
        assert projects[0]["id"] == own.id

    def test_list_unauthenticated(self, client: FlaskClient):
        response = client.get("/api/book-projects/")
        assert response.status_code in (401, 302)


class TestGetBookProject:
    def test_get_owned(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.get(f"/api/book-projects/{project.id}")
        assert response.status_code == 200
        data = response.get_json()["project"]
        assert data["id"] == project.id
        assert "share_links" in data
        assert "contributors" in data

    def test_get_not_owned_returns_404(self, auth_client, second_user):
        project = _make_project(second_user)
        response = auth_client.get(f"/api/book-projects/{project.id}")
        # Treating "not yours" as "not found" prevents project-existence enumeration.
        assert response.status_code == 404

    def test_get_missing(self, auth_client):
        response = auth_client.get("/api/book-projects/999999")
        assert response.status_code == 404


class TestUpdateBookProject:
    def test_update_partial(self, auth_client, test_user):
        project = _make_project(test_user, title="Original")
        response = auth_client.patch(
            f"/api/book-projects/{project.id}",
            json={"title": "Updated", "dedication": "Love wins"},
        )
        assert response.status_code == 200
        proj = response.get_json()["project"]
        assert proj["title"] == "Updated"
        assert proj["dedication"] == "Love wins"
        # project_type unchanged
        assert proj["project_type"] == "wedding"

    def test_update_status(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.patch(
            f"/api/book-projects/{project.id}", json={"status": "review"}
        )
        assert response.status_code == 200
        assert response.get_json()["project"]["status"] == "review"

    def test_update_invalid_status(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.patch(
            f"/api/book-projects/{project.id}", json={"status": "shipped"}
        )
        assert response.status_code == 400

    def test_update_empty_title_rejected(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.patch(
            f"/api/book-projects/{project.id}", json={"title": "  "}
        )
        assert response.status_code == 400

    def test_update_not_owned(self, auth_client, second_user):
        project = _make_project(second_user)
        response = auth_client.patch(
            f"/api/book-projects/{project.id}", json={"title": "Hijacked"}
        )
        assert response.status_code == 404


class TestDeleteBookProject:
    def test_delete_owned(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.delete(f"/api/book-projects/{project.id}")
        assert response.status_code == 200
        assert BookProject.query.get(project.id) is None

    def test_delete_detaches_recipes(self, auth_client, test_user, sample_recipe):
        project = _make_project(test_user)
        recipe = db.session.get(Recipe, sample_recipe.id)
        recipe.book_project_id = project.id
        db.session.commit()
        response = auth_client.delete(f"/api/book-projects/{project.id}")
        assert response.status_code == 200
        # Recipe row survives; book_project_id is cleared.
        refreshed = db.session.get(Recipe, sample_recipe.id)
        assert refreshed is not None
        assert refreshed.book_project_id is None

    def test_delete_not_owned(self, auth_client, second_user):
        project = _make_project(second_user)
        response = auth_client.delete(f"/api/book-projects/{project.id}")
        assert response.status_code == 404
        # Survives.
        assert BookProject.query.get(project.id) is not None


class TestShareLinks:
    def test_create_minimal(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.post(
            f"/api/book-projects/{project.id}/share-links", json={}
        )
        assert response.status_code == 201
        link = response.get_json()["share_link"]
        assert link["project_id"] == project.id
        assert link["revoked"] is False
        assert link["submission_count"] == 0
        assert link["is_active"] is True
        assert len(link["token"]) >= 32

    def test_create_with_cap_and_expiry(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.post(
            f"/api/book-projects/{project.id}/share-links",
            json={"submission_cap": 50, "expires_at": "2026-12-31T23:59:59"},
        )
        assert response.status_code == 201
        link = response.get_json()["share_link"]
        assert link["submission_cap"] == 50
        assert link["expires_at"] is not None

    def test_create_invalid_cap(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.post(
            f"/api/book-projects/{project.id}/share-links",
            json={"submission_cap": 0},
        )
        assert response.status_code == 400

    def test_create_invalid_expires_at(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.post(
            f"/api/book-projects/{project.id}/share-links",
            json={"expires_at": "not-a-date"},
        )
        assert response.status_code == 400

    def test_revoke_share_link(self, auth_client, test_user):
        project = _make_project(test_user)
        link = ProjectShareLink(project_id=project.id, token="testtoken123")
        db.session.add(link)
        db.session.commit()
        response = auth_client.delete(
            f"/api/book-projects/{project.id}/share-links/testtoken123"
        )
        assert response.status_code == 200
        assert response.get_json()["share_link"]["revoked"] is True
        # Persisted.
        refreshed = ProjectShareLink.query.get(link.id)
        assert refreshed.revoked is True

    def test_revoke_missing_link(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.delete(
            f"/api/book-projects/{project.id}/share-links/nosuchtoken"
        )
        assert response.status_code == 404

    def test_create_share_link_not_owned(self, auth_client, second_user):
        project = _make_project(second_user)
        response = auth_client.post(
            f"/api/book-projects/{project.id}/share-links", json={}
        )
        assert response.status_code == 404


class TestSubmissions:
    def test_list_empty(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.get(f"/api/book-projects/{project.id}/submissions")
        assert response.status_code == 200
        assert response.get_json()["submissions"] == []

    def test_list_with_guest_contributor(
        self, auth_client, test_user, sample_recipe
    ):
        project = _make_project(test_user)
        contributor = GuestContributor(
            project_id=project.id,
            display_name="Aunt Linda",
            email="aunt@example.com",
        )
        db.session.add(contributor)
        db.session.flush()

        recipe = db.session.get(Recipe, sample_recipe.id)
        recipe.book_project_id = project.id
        recipe.guest_contributor_id = contributor.id
        db.session.commit()

        response = auth_client.get(f"/api/book-projects/{project.id}/submissions")
        assert response.status_code == 200
        submissions = response.get_json()["submissions"]
        assert len(submissions) == 1
        sub = submissions[0]
        assert sub["recipe_id"] == sample_recipe.id
        assert sub["contributor"]["display_name"] == "Aunt Linda"
        # Email should NOT be exposed by default.
        assert "email" not in sub["contributor"]
        assert sub["is_excluded_from_project"] is False

    def test_update_submission_exclude(self, auth_client, test_user, sample_recipe):
        project = _make_project(test_user)
        recipe = db.session.get(Recipe, sample_recipe.id)
        recipe.book_project_id = project.id
        db.session.commit()

        response = auth_client.patch(
            f"/api/book-projects/{project.id}/submissions/{sample_recipe.id}",
            json={"is_excluded_from_project": True},
        )
        assert response.status_code == 200
        assert response.get_json()["submission"]["is_excluded_from_project"] is True
        refreshed = db.session.get(Recipe, sample_recipe.id)
        assert refreshed.is_excluded_from_project is True

    def test_update_submission_not_part_of_project(
        self, auth_client, test_user, sample_recipe
    ):
        # Recipe exists but isn't linked to this project — must 404.
        project = _make_project(test_user)
        response = auth_client.patch(
            f"/api/book-projects/{project.id}/submissions/{sample_recipe.id}",
            json={"is_excluded_from_project": True},
        )
        assert response.status_code == 404

    def test_list_submissions_not_owned(self, auth_client, second_user):
        project = _make_project(second_user)
        response = auth_client.get(f"/api/book-projects/{project.id}/submissions")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Guest endpoints (share-token, no auth)
# ---------------------------------------------------------------------------


class TestGetProjectByToken:
    def test_valid_token_returns_public_info(self, client, test_user):
        project = _make_project(
            test_user,
            title="Wedding Book",
            honorees=["Sarah", "Maya"],
            project_type=ProjectType.WEDDING,
            dedication="With love",
        )
        link = _make_share_link(project, token="goodtoken123")
        response = client.get(f"/api/book-projects/by-token/{link.token}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["project"]["title"] == "Wedding Book"
        assert data["project"]["honorees"] == ["Sarah", "Maya"]
        assert data["project"]["project_type"] == "wedding"
        assert data["project"]["dedication"] == "With love"
        # PII checks — organizer info must NOT leak through this public endpoint.
        assert "owner_user_id" not in data["project"]
        assert "contributors" not in data
        assert data["share_link"]["submission_count"] == 0

    def test_invalid_token(self, client):
        response = client.get("/api/book-projects/by-token/no-such-token")
        assert response.status_code == 404

    def test_revoked_token(self, client, test_user):
        project = _make_project(test_user)
        link = _make_share_link(project, token="revokedtoken", revoked=True)
        response = client.get(f"/api/book-projects/by-token/{link.token}")
        assert response.status_code == 403

    def test_expired_token(self, client, test_user):
        project = _make_project(test_user)
        link = _make_share_link(
            project,
            token="expiredtoken",
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        response = client.get(f"/api/book-projects/by-token/{link.token}")
        assert response.status_code == 403

    def test_token_over_cap(self, client, test_user):
        project = _make_project(test_user)
        link = _make_share_link(
            project,
            token="cappedtoken",
            submission_cap=5,
            submission_count=5,
        )
        response = client.get(f"/api/book-projects/by-token/{link.token}")
        assert response.status_code == 403


class TestSubmitTextByToken:
    @patch("app.api.book_projects.RecipeParser")
    def test_submit_text_creates_recipe_and_contributor(
        self, mock_parser_cls, client, test_user
    ):
        mock_parser = MagicMock()
        mock_parser.parse_recipe_text.return_value = _FAKE_PARSED_RECIPE
        mock_parser_cls.return_value = mock_parser

        project = _make_project(test_user, title="Family Book")
        link = _make_share_link(project, token="texttoken")

        response = client.post(
            f"/api/book-projects/by-token/{link.token}/submit-text",
            json={
                "text": "Some recipe text from Aunt Linda's card",
                "display_name": "Aunt Linda",
                "email": "linda@example.com",
            },
        )

        assert response.status_code == 201
        sub = response.get_json()["submission"]
        assert sub["title"] == "Grandma's Apple Pie"
        assert sub["contributor"]["display_name"] == "Aunt Linda"

        # Recipe stored with the right ownership + attribution.
        recipe = db.session.get(Recipe, sub["recipe_id"])
        assert recipe.user_id == project.owner_user_id
        assert recipe.book_project_id == project.id
        assert recipe.guest_contributor_id is not None
        assert recipe.uploaded_by_id is None

        # Submission count incremented exactly once.
        db.session.refresh(link)
        assert link.submission_count == 1

        # GuestContributor was created with the email — used for future
        # contribution matching.
        contributor = GuestContributor.query.get(recipe.guest_contributor_id)
        assert contributor.email == "linda@example.com"
        assert contributor.project_id == project.id

    @patch("app.api.book_projects.RecipeParser")
    def test_same_email_reuses_contributor(
        self, mock_parser_cls, client, test_user
    ):
        mock_parser = MagicMock()
        mock_parser.parse_recipe_text.return_value = _FAKE_PARSED_RECIPE
        mock_parser_cls.return_value = mock_parser

        project = _make_project(test_user)
        link = _make_share_link(project, token="dedupetoken")

        for _ in range(2):
            response = client.post(
                f"/api/book-projects/by-token/{link.token}/submit-text",
                json={
                    "text": "Recipe text",
                    "display_name": "Aunt Linda",
                    "email": "linda@example.com",
                },
            )
            assert response.status_code == 201

        contributors = GuestContributor.query.filter_by(
            project_id=project.id, email="linda@example.com"
        ).all()
        assert len(contributors) == 1
        # Two recipes, one contributor.
        recipes = Recipe.query.filter_by(book_project_id=project.id).all()
        assert len(recipes) == 2
        assert all(r.guest_contributor_id == contributors[0].id for r in recipes)

        db.session.refresh(link)
        assert link.submission_count == 2

    def test_submit_text_missing_text(self, client, test_user):
        project = _make_project(test_user)
        link = _make_share_link(project, token="missing")
        response = client.post(
            f"/api/book-projects/by-token/{link.token}/submit-text",
            json={"display_name": "Anon"},
        )
        assert response.status_code == 400

    def test_submit_text_invalid_token(self, client):
        response = client.post(
            "/api/book-projects/by-token/no-such-token/submit-text",
            json={"text": "hi"},
        )
        assert response.status_code == 404

    def test_submit_text_revoked_token_rejected(self, client, test_user):
        project = _make_project(test_user)
        link = _make_share_link(project, token="revoked2", revoked=True)
        response = client.post(
            f"/api/book-projects/by-token/{link.token}/submit-text",
            json={"text": "hi"},
        )
        assert response.status_code == 403

    @patch("app.api.book_projects.RecipeParser")
    def test_submit_text_anonymous(self, mock_parser_cls, client, test_user):
        mock_parser = MagicMock()
        mock_parser.parse_recipe_text.return_value = _FAKE_PARSED_RECIPE
        mock_parser_cls.return_value = mock_parser

        project = _make_project(test_user)
        link = _make_share_link(project, token="anontoken")

        response = client.post(
            f"/api/book-projects/by-token/{link.token}/submit-text",
            json={"text": "Recipe text"},
        )
        assert response.status_code == 201
        sub = response.get_json()["submission"]
        assert sub["contributor"]["display_name"] == "Anonymous"
        recipe = db.session.get(Recipe, sub["recipe_id"])
        contributor = db.session.get(GuestContributor, recipe.guest_contributor_id)
        assert contributor.email is None


class TestSubmitUrlByToken:
    @patch("app.services.url_recipe_service.UrlRecipeService")
    def test_submit_url_creates_recipe(
        self, mock_service_cls, client, test_user
    ):
        mock_service = MagicMock()
        mock_service.import_from_url.return_value = {
            "recipe_data": _FAKE_PARSED_RECIPE,
            "extraction_method": "json-ld",
            "source_url": "https://example.com/recipe",
        }
        mock_service_cls.return_value = mock_service

        project = _make_project(test_user)
        link = _make_share_link(project, token="urltoken")

        response = client.post(
            f"/api/book-projects/by-token/{link.token}/submit-url",
            json={
                "url": "https://example.com/recipe",
                "display_name": "Cousin Jane",
            },
        )

        assert response.status_code == 201
        sub = response.get_json()["submission"]
        assert sub["title"] == "Grandma's Apple Pie"
        assert sub["source"] == "https://example.com/recipe"

        recipe = db.session.get(Recipe, sub["recipe_id"])
        assert recipe.source == "https://example.com/recipe"
        assert recipe.book_project_id == project.id
        assert recipe.is_original_recipe is True

        db.session.refresh(link)
        assert link.submission_count == 1

    def test_submit_url_missing(self, client, test_user):
        project = _make_project(test_user)
        link = _make_share_link(project, token="missingurltoken")
        response = client.post(
            f"/api/book-projects/by-token/{link.token}/submit-url",
            json={"display_name": "Someone"},
        )
        assert response.status_code == 400

    def test_submit_url_invalid_token(self, client):
        response = client.post(
            "/api/book-projects/by-token/bogus/submit-url",
            json={"url": "https://example.com/recipe"},
        )
        assert response.status_code == 404


class TestSubmitImageByToken:
    @patch("app.tasks.recipe_tasks.process_single_recipe_task")
    @patch("app.api.book_projects.process_and_save_image")
    def test_submit_image_creates_job_and_contributor(
        self, mock_save_image, mock_task, client, test_user
    ):
        from io import BytesIO

        from app.models import ProcessingJob, RecipeImage

        def fake_save_image(file, filename, folder="recipes"):
            img = RecipeImage(
                filename=filename,
                original_filename=filename,
                file_size=len(file.read() if hasattr(file, "read") else b""),
                content_type="image/jpeg",
                file_path=f"test/{filename}",
            )
            return img

        mock_save_image.side_effect = fake_save_image
        mock_task.delay = MagicMock()

        project = _make_project(test_user)
        link = _make_share_link(project, token="imgtoken")

        response = client.post(
            f"/api/book-projects/by-token/{link.token}/submit-image",
            data={
                "image": (BytesIO(b"fakeimagebytes"), "card.jpg"),
                "display_name": "Aunt Linda",
                "email": "linda@example.com",
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 201
        sub = response.get_json()["submission"]
        assert sub["status"] == "processing"
        assert sub["contributor"]["display_name"] == "Aunt Linda"

        # ProcessingJob created with the project + contributor attribution.
        job = db.session.get(ProcessingJob, sub["job_id"])
        assert job is not None
        assert job.book_project_id == project.id
        assert job.guest_contributor_id is not None
        assert job.cookbook_id is None
        assert job.user_id is None

        # Celery task dispatched once.
        assert mock_task.delay.call_count == 1
        called_with_job_id, called_with_user_id = mock_task.delay.call_args[0]
        assert called_with_job_id == sub["job_id"]
        assert called_with_user_id is None

        # Share-link counter incremented.
        db.session.refresh(link)
        assert link.submission_count == 1

    def test_submit_image_missing_file(self, client, test_user):
        project = _make_project(test_user)
        link = _make_share_link(project, token="noimgtoken")
        response = client.post(
            f"/api/book-projects/by-token/{link.token}/submit-image",
            data={"display_name": "Anon"},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_submit_image_bad_extension(self, client, test_user):
        from io import BytesIO

        project = _make_project(test_user)
        link = _make_share_link(project, token="badexttoken")
        response = client.post(
            f"/api/book-projects/by-token/{link.token}/submit-image",
            data={
                "image": (BytesIO(b"data"), "card.exe"),
                "display_name": "Anon",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_submit_image_invalid_token(self, client):
        from io import BytesIO

        response = client.post(
            "/api/book-projects/by-token/no-such-token/submit-image",
            data={"image": (BytesIO(b"data"), "card.jpg")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 404


class TestCreateRecipeFromParsedDataBookProject:
    """Async-pipeline integration: when a ProcessingJob has book_project_id set,
    the resulting Recipe is owned by the project organizer with guest-contributor
    attribution, NOT attached to a cookbook."""

    def test_create_from_job_with_book_project(self, app, test_user):
        from app.api.recipes.routes import _create_recipe_from_parsed_data
        from app.models import (
            BookProject,
            GuestContributor,
            ProcessingJob,
            ProjectType,
            RecipeImage,
        )

        with app.app_context():
            project = BookProject(
                owner_user_id=test_user.id,
                title="Heirloom Book",
                project_type=ProjectType.HEIRLOOM,
            )
            db.session.add(project)
            db.session.flush()

            contributor = GuestContributor(
                project_id=project.id, display_name="Grandma"
            )
            db.session.add(contributor)
            db.session.flush()

            image = RecipeImage(
                filename="x.jpg",
                original_filename="x.jpg",
                file_size=1,
                content_type="image/jpeg",
                file_path="test/x.jpg",
            )
            db.session.add(image)
            db.session.flush()

            job = ProcessingJob(
                image_id=image.id,
                user_id=None,
                cookbook_id=None,
                book_project_id=project.id,
                guest_contributor_id=contributor.id,
            )
            db.session.add(job)
            db.session.flush()

            recipe = _create_recipe_from_parsed_data(
                parsed_recipe={
                    "title": "Grandma's Pie",
                    "ingredients": [],
                    "instructions": ["Bake it"],
                    "tags": [],
                },
                extracted_text="Grandma's Pie",
                job=job,
                upload_user_id=None,
            )
            db.session.commit()

            assert recipe.user_id == project.owner_user_id
            assert recipe.book_project_id == project.id
            assert recipe.guest_contributor_id == contributor.id
            assert recipe.cookbook_id is None
            assert recipe.uploaded_by_id is None

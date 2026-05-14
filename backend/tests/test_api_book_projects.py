"""Tests for the organizer-side BookProject API endpoints."""

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

"""BookProject API — organizer-side endpoints.

These endpoints power the buyer/organizer surface: creating a project, generating and
revoking share links, listing and curating submissions, and exporting the final PDF.

Guest-side submission endpoints (the share-link landing flow used by family/friends
without accounts) live in a separate module added in a later step alongside the
share-token decorator. PDF export and Stripe payment endpoints also follow in later
steps; their stub endpoints are not yet defined here.
"""

import secrets
import traceback
from datetime import date, datetime
from typing import Optional

from flask import Blueprint, Response, current_app, jsonify, request

from app import db
from app.api.auth import require_auth
from app.models import (
    BookProject,
    GuestContributor,
    ProjectShareLink,
    ProjectStatus,
    ProjectType,
    Recipe,
)

bp = Blueprint("book_projects", __name__, url_prefix="/book-projects")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_project_type(value: Optional[str]) -> Optional[ProjectType]:
    """Return a ProjectType for the given input, or None if invalid. A missing value
    defaults to GENERAL."""
    if value is None or value == "":
        return ProjectType.GENERAL
    try:
        return ProjectType(value)
    except ValueError:
        return None


def _parse_status(value: Optional[str]) -> Optional[ProjectStatus]:
    if value is None or value == "":
        return None
    try:
        return ProjectStatus(value)
    except ValueError:
        return None


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, str) and "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _project_for_owner(project_id: int, current_user) -> Optional[BookProject]:
    """Return the BookProject if it exists AND is owned by current_user. Otherwise None.
    Admins still go through this — projects are personal artifacts."""
    return BookProject.query.filter_by(
        id=project_id, owner_user_id=current_user.id
    ).first()


def _share_link_url(token: str) -> str:
    """Build the public share URL for a given token. Uses FRONTEND_URL from app config
    so the link points at the contributor landing page on the deployed frontend."""
    base = (current_app.config.get("FRONTEND_URL") or "").rstrip("/")
    if not base:
        # Fallback so tests and local dev still produce a usable string.
        base = ""
    return f"{base}/contribute/{token}"


def _normalize_honorees(value) -> list:
    """Accept either a list of strings or a comma-separated string."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------


@bp.route("/", methods=["POST"])
@require_auth
def create_book_project(current_user) -> Response:
    """Create a new BookProject owned by the current user."""
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    project_type = _parse_project_type(data.get("project_type"))
    if project_type is None:
        return jsonify({"error": "invalid project_type"}), 400

    try:
        project = BookProject(
            owner_user_id=current_user.id,
            title=title,
            project_type=project_type,
            subtitle=(data.get("subtitle") or "").strip() or None,
            dedication=(data.get("dedication") or "").strip() or None,
            honorees=_normalize_honorees(data.get("honorees")),
            occasion_date=_parse_date(data.get("occasion_date")),
            submission_deadline=_parse_date(data.get("submission_deadline")),
            cover_image_url=(data.get("cover_image_url") or "").strip() or None,
            project_metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
        )
        db.session.add(project)
        db.session.commit()
        return jsonify({"project": project.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to create BookProject for user {current_user.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to create project"}), 500


@bp.route("/", methods=["GET"])
@require_auth
def list_book_projects(current_user) -> Response:
    """List BookProjects owned by the current user."""
    projects = (
        BookProject.query.filter_by(owner_user_id=current_user.id)
        .order_by(BookProject.created_at.desc())
        .all()
    )
    return jsonify({"projects": [p.to_dict() for p in projects]}), 200


@bp.route("/<int:project_id>", methods=["GET"])
@require_auth
def get_book_project(current_user, project_id: int) -> Response:
    """Return detail for one BookProject the user owns."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    result = project.to_dict()
    result["share_links"] = [link.to_dict() for link in project.share_links]
    result["contributors"] = [
        c.to_dict(include_email=False) for c in project.contributors
    ]
    return jsonify({"project": result}), 200


@bp.route("/<int:project_id>", methods=["PATCH"])
@require_auth
def update_book_project(current_user, project_id: int) -> Response:
    """Patch metadata on a BookProject. Only fields present in the request body are
    touched; everything else is left alone."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        project.title = title

    if "subtitle" in data:
        project.subtitle = (data.get("subtitle") or "").strip() or None

    if "dedication" in data:
        project.dedication = (data.get("dedication") or "").strip() or None

    if "honorees" in data:
        project.honorees = _normalize_honorees(data.get("honorees"))

    if "occasion_date" in data:
        project.occasion_date = _parse_date(data.get("occasion_date"))

    if "submission_deadline" in data:
        project.submission_deadline = _parse_date(data.get("submission_deadline"))

    if "cover_image_url" in data:
        project.cover_image_url = (data.get("cover_image_url") or "").strip() or None

    if "metadata" in data and isinstance(data.get("metadata"), dict):
        project.project_metadata = data["metadata"]

    if "project_type" in data:
        new_type = _parse_project_type(data.get("project_type"))
        if new_type is None:
            return jsonify({"error": "invalid project_type"}), 400
        project.project_type = new_type

    if "status" in data:
        new_status = _parse_status(data.get("status"))
        if new_status is None:
            return jsonify({"error": "invalid status"}), 400
        project.status = new_status

    try:
        db.session.commit()
        return jsonify({"project": project.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to update BookProject {project_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to update project"}), 500


@bp.route("/<int:project_id>", methods=["DELETE"])
@require_auth
def delete_book_project(current_user, project_id: int) -> Response:
    """Hard delete a BookProject and its dependent rows (share links, contributors,
    exports). Recipes that were submitted to this project keep their rows but have
    their book_project_id cleared so they aren't orphaned."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    try:
        # Detach recipes from the project before deleting (they still belong to the
        # organizer's user_id and stay in their account; the project relationship
        # just goes away).
        Recipe.query.filter_by(book_project_id=project.id).update(
            {
                Recipe.book_project_id: None,
                Recipe.guest_contributor_id: None,
                Recipe.is_excluded_from_project: False,
            },
            synchronize_session=False,
        )
        db.session.delete(project)
        db.session.commit()
        return jsonify({"message": "Project deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to delete BookProject {project_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to delete project"}), 500


# ---------------------------------------------------------------------------
# Share links
# ---------------------------------------------------------------------------


@bp.route("/<int:project_id>/share-links", methods=["POST"])
@require_auth
def create_share_link(current_user, project_id: int) -> Response:
    """Generate a new share link for a project. Optional body fields:
    expires_at (ISO datetime), submission_cap (int)."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json(silent=True) or {}

    expires_at_raw = data.get("expires_at")
    expires_at: Optional[datetime] = None
    if expires_at_raw:
        try:
            expires_at = datetime.fromisoformat(
                str(expires_at_raw).replace("Z", "+00:00")
            )
            # Normalize to naive UTC for storage consistency with other DateTime columns.
            if expires_at.tzinfo is not None:
                expires_at = expires_at.astimezone(tz=None).replace(tzinfo=None)
        except (ValueError, TypeError):
            return jsonify({"error": "invalid expires_at"}), 400

    submission_cap_raw = data.get("submission_cap")
    submission_cap: Optional[int] = None
    if submission_cap_raw is not None:
        try:
            submission_cap = int(submission_cap_raw)
            if submission_cap <= 0:
                return jsonify({"error": "submission_cap must be positive"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "submission_cap must be an integer"}), 400

    try:
        token = secrets.token_urlsafe(32)
        share_link = ProjectShareLink(
            project_id=project.id,
            token=token,
            expires_at=expires_at,
            submission_cap=submission_cap,
        )
        db.session.add(share_link)
        db.session.commit()

        payload = share_link.to_dict()
        payload["url"] = _share_link_url(token)
        return jsonify({"share_link": payload}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to create share link for project {project_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to create share link"}), 500


@bp.route("/<int:project_id>/share-links/<string:token>", methods=["DELETE"])
@require_auth
def revoke_share_link(current_user, project_id: int, token: str) -> Response:
    """Revoke a share link (does not delete the row; revoked=True makes subsequent
    submissions reject with 403)."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    share_link = ProjectShareLink.query.filter_by(
        project_id=project.id, token=token
    ).first()
    if not share_link:
        return jsonify({"error": "Share link not found"}), 404

    if share_link.revoked:
        return jsonify({"share_link": share_link.to_dict()}), 200

    try:
        share_link.revoked = True
        db.session.commit()
        return jsonify({"share_link": share_link.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to revoke share link {token}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to revoke share link"}), 500


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------


@bp.route("/<int:project_id>/submissions", methods=["GET"])
@require_auth
def list_submissions(current_user, project_id: int) -> Response:
    """Return the recipes submitted to this project, with contributor attribution
    inlined so the organizer dashboard can render without a second round trip."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    recipes = (
        Recipe.query.filter_by(book_project_id=project.id)
        .order_by(Recipe.created_at.desc())
        .all()
    )

    submissions = []
    for recipe in recipes:
        contributor = recipe.guest_contributor
        submissions.append(
            {
                "recipe_id": recipe.id,
                "title": recipe.title,
                "description": recipe.description,
                "is_excluded_from_project": recipe.is_excluded_from_project,
                "contributor": contributor.to_dict(include_email=False)
                if contributor
                else None,
                "uploaded_by_id": recipe.uploaded_by_id,
                "created_at": recipe.created_at.isoformat()
                if recipe.created_at
                else None,
            }
        )

    return jsonify({"submissions": submissions}), 200


@bp.route(
    "/<int:project_id>/submissions/<int:recipe_id>", methods=["PATCH"]
)
@require_auth
def update_submission(current_user, project_id: int, recipe_id: int) -> Response:
    """Edit submission metadata that's specific to the project context. For now this
    is just the exclude/include toggle. Editing the underlying recipe fields (title,
    ingredients, instructions, etc.) is done through the existing /recipes endpoints
    — the organizer owns the recipe, so those already work."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    recipe = Recipe.query.filter_by(
        id=recipe_id, book_project_id=project.id
    ).first()
    if not recipe:
        return jsonify({"error": "Submission not found"}), 404

    data = request.get_json(silent=True) or {}
    changed = False

    if "is_excluded_from_project" in data:
        new_value = bool(data["is_excluded_from_project"])
        if recipe.is_excluded_from_project != new_value:
            recipe.is_excluded_from_project = new_value
            changed = True

    if not changed:
        return jsonify(
            {
                "submission": {
                    "recipe_id": recipe.id,
                    "is_excluded_from_project": recipe.is_excluded_from_project,
                }
            }
        ), 200

    try:
        db.session.commit()
        return jsonify(
            {
                "submission": {
                    "recipe_id": recipe.id,
                    "is_excluded_from_project": recipe.is_excluded_from_project,
                }
            }
        ), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to update submission {recipe_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to update submission"}), 500

"""BookProject API — organizer-side endpoints.

These endpoints power the buyer/organizer surface: creating a project, generating and
revoking share links, listing and curating submissions, and exporting the final PDF.

Guest-side submission endpoints (the share-link landing flow used by family/friends
without accounts) live in a separate module added in a later step alongside the
share-token decorator. PDF export and Stripe payment endpoints also follow in later
steps; their stub endpoints are not yet defined here.
"""

import os
import secrets
import traceback
from datetime import date, datetime
from typing import Optional

import requests
from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    request,
    send_file,
    stream_with_context,
)

from app import db
from app.api.auth import require_auth, require_share_token
from app.api.recipes.helpers import (
    ALLOWED_EXTENSIONS,
    allowed_file,
    process_and_save_image,
    safe_int_conversion,
)
from app.models import (
    BookProject,
    BookProjectExport,
    GuestContributor,
    ProcessingJob,
    ProjectShareLink,
    ProjectStatus,
    ProjectType,
    Recipe,
)
from app.services.recipe_parser import RecipeParser
from app.services.recipe_parsing_service import (
    create_recipe_ingredients,
    create_recipe_instructions,
    create_recipe_tags,
)
from app.utils.rate_limiting import rate_limit_upload

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


# ---------------------------------------------------------------------------
# Guest submission endpoints (share-token authenticated, no user account)
# ---------------------------------------------------------------------------


def _get_or_create_guest_contributor(
    project: BookProject,
    share_link: ProjectShareLink,
    display_name: Optional[str],
    email: Optional[str],
) -> GuestContributor:
    """Match a contributor by (project, email) so multiple submissions from the same
    person collapse to a single GuestContributor row. With no email, always create a
    fresh row."""
    display_name = (display_name or "").strip() or "Anonymous"
    email_norm = (email or "").strip().lower() or None

    if email_norm:
        existing = GuestContributor.query.filter_by(
            project_id=project.id, email=email_norm
        ).first()
        if existing:
            if display_name and existing.display_name != display_name:
                existing.display_name = display_name
            return existing

    contributor = GuestContributor(
        project_id=project.id,
        share_link_id=share_link.id,
        display_name=display_name,
        email=email_norm,
    )
    db.session.add(contributor)
    db.session.flush()
    return contributor


def _public_project_payload(project: BookProject) -> dict:
    """Minimal project info exposed to the public contributor landing page. No PII —
    no organizer name, no contributor list, no email addresses."""
    return {
        "id": project.id,
        "title": project.title,
        "subtitle": project.subtitle,
        "project_type": project.project_type.value if project.project_type else None,
        "honorees": project.honorees or [],
        "occasion_date": project.occasion_date.isoformat()
        if project.occasion_date
        else None,
        "submission_deadline": project.submission_deadline.isoformat()
        if project.submission_deadline
        else None,
        "dedication": project.dedication,
        "cover_image_url": project.cover_image_url,
    }


@bp.route("/by-token/<string:token>", methods=["GET"])
@require_share_token
def get_project_by_token(token: str) -> Response:
    """Validate the share token and return public project info for the contributor
    landing page. No auth required."""
    project = g.book_project
    share_link = g.share_link
    return jsonify(
        {
            "project": _public_project_payload(project),
            "share_link": {
                "submission_count": share_link.submission_count,
                "submission_cap": share_link.submission_cap,
                "expires_at": share_link.expires_at.isoformat()
                if share_link.expires_at
                else None,
            },
        }
    ), 200


@bp.route("/by-token/<string:token>/submit-text", methods=["POST"])
@require_share_token
@rate_limit_upload
def submit_text_by_token(token: str) -> Response:
    """Submit a recipe via raw text (paste or typed). Synchronous — parses
    immediately via the shared RecipeParser and creates a Recipe owned by the
    project organizer with guest_contributor attribution."""
    project: BookProject = g.book_project
    share_link: ProjectShareLink = g.share_link

    data = request.get_json(silent=True) or {}
    recipe_text = (data.get("text") or "").strip()
    if not recipe_text:
        return jsonify({"error": "No recipe text provided"}), 400

    max_text_length = current_app.config.get("MAX_RECIPE_TEXT_LENGTH", 50000)
    if len(recipe_text) > max_text_length:
        return jsonify(
            {
                "error": (
                    f"Recipe text too long ({len(recipe_text)} characters). "
                    f"Maximum {max_text_length} characters allowed."
                )
            }
        ), 400

    display_name = data.get("display_name")
    email = data.get("email")

    try:
        contributor = _get_or_create_guest_contributor(
            project, share_link, display_name, email
        )

        parser = RecipeParser()
        parsed_recipe = parser.parse_recipe_text(
            recipe_text, translate_to_english=False
        )

        recipe_title = parsed_recipe.get("title") or "Untitled Recipe"
        if not recipe_title.strip():
            recipe_title = "Untitled Recipe"

        recipe = Recipe(
            title=recipe_title,
            description=parsed_recipe.get("description"),
            # Recipe is owned by the project organizer so it lives in their
            # account; attribution to the actual contributor goes via
            # guest_contributor_id.
            user_id=project.owner_user_id,
            uploaded_by_id=None,
            book_project_id=project.id,
            guest_contributor_id=contributor.id,
            is_public=False,
            # Source unknown for guest text submissions — they may be typing in
            # their own recipe or copying from somewhere else. None means legacy
            # / unknown, which matches the existing column semantics.
            is_original_recipe=None,
            prep_time=safe_int_conversion(parsed_recipe.get("prep_time")),
            cook_time=safe_int_conversion(parsed_recipe.get("cook_time")),
            servings=safe_int_conversion(parsed_recipe.get("servings")),
            difficulty=parsed_recipe.get("difficulty"),
            course_type=parsed_recipe.get("course_type"),
        )
        db.session.add(recipe)
        db.session.flush()

        create_recipe_ingredients(recipe.id, parsed_recipe)
        create_recipe_instructions(recipe.id, parsed_recipe, recipe_text)
        create_recipe_tags(recipe.id, parsed_recipe)

        share_link.submission_count += 1

        db.session.commit()

        return jsonify(
            {
                "submission": {
                    "recipe_id": recipe.id,
                    "title": recipe.title,
                    "contributor": contributor.to_dict(include_email=False),
                }
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Guest text submission failed for project {project.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to submit recipe"}), 500


@bp.route("/by-token/<string:token>/submit-url", methods=["POST"])
@require_share_token
@rate_limit_upload
def submit_url_by_token(token: str) -> Response:
    """Submit a recipe via URL (e.g. a recipe blog). Synchronous — fetches and
    parses via the shared UrlRecipeService."""
    from app.services.url_recipe_service import (
        BotProtectionError,
        RecipeNotFoundError,
        UrlFetchError,
        UrlRecipeService,
        UrlValidationError,
    )

    project: BookProject = g.book_project
    share_link: ProjectShareLink = g.share_link

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    display_name = data.get("display_name")
    email = data.get("email")

    url_service = UrlRecipeService()
    try:
        result = url_service.import_from_url(url, translate_to_english=False)
    except UrlValidationError as e:
        return jsonify({"error": str(e)}), 400
    except UrlFetchError as e:
        return jsonify({"error": str(e)}), 400
    except BotProtectionError as e:
        return jsonify({"error": str(e)}), 403
    except RecipeNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        current_app.logger.error(
            f"Guest URL import failed (parsing) for project {project.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to fetch or parse the URL"}), 500

    parsed_recipe = result["recipe_data"]
    source_url = result["source_url"]

    try:
        contributor = _get_or_create_guest_contributor(
            project, share_link, display_name, email
        )

        recipe_title = parsed_recipe.get("title") or "Untitled Recipe"
        if not recipe_title.strip():
            recipe_title = "Untitled Recipe"

        recipe = Recipe(
            title=recipe_title,
            description=parsed_recipe.get("description"),
            user_id=project.owner_user_id,
            uploaded_by_id=None,
            book_project_id=project.id,
            guest_contributor_id=contributor.id,
            is_public=False,
            # URL-imported recipes come from a publicly-accessible web page —
            # safe to mark is_original_recipe=True per the project's existing
            # convention for URL imports.
            is_original_recipe=True,
            source=source_url,
            prep_time=safe_int_conversion(parsed_recipe.get("prep_time")),
            cook_time=safe_int_conversion(parsed_recipe.get("cook_time")),
            servings=safe_int_conversion(parsed_recipe.get("servings")),
            difficulty=parsed_recipe.get("difficulty"),
            course_type=parsed_recipe.get("course_type"),
        )
        db.session.add(recipe)
        db.session.flush()

        create_recipe_ingredients(recipe.id, parsed_recipe)
        create_recipe_instructions(recipe.id, parsed_recipe, "")
        create_recipe_tags(recipe.id, parsed_recipe)

        share_link.submission_count += 1

        db.session.commit()

        return jsonify(
            {
                "submission": {
                    "recipe_id": recipe.id,
                    "title": recipe.title,
                    "source": source_url,
                    "contributor": contributor.to_dict(include_email=False),
                }
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Guest URL submission failed (persist) for project {project.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to submit recipe"}), 500


@bp.route("/by-token/<string:token>/submit-image", methods=["POST"])
@require_share_token
@rate_limit_upload
def submit_image_by_token(token: str) -> Response:
    """Submit a recipe via image upload (photo of a handwritten card or printed
    page). Asynchronous: the file is saved, a ProcessingJob is created with the
    BookProject/GuestContributor attribution, and a Celery task is dispatched to
    OCR and parse it. The resulting Recipe lands in the organizer's project.

    Form fields: image (file), display_name (optional), email (optional).
    """
    project: BookProject = g.book_project
    share_link: ProjectShareLink = g.share_link

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify(
            {"error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}
        ), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    file_size_mb = file_size / (1024 * 1024)
    max_upload_size = current_app.config.get("MAX_UPLOAD_SIZE", 8)
    if file_size_mb > max_upload_size:
        return jsonify(
            {
                "error": (
                    f"File too large ({file_size_mb:.1f}MB). "
                    f"Please use files smaller than {max_upload_size}MB."
                )
            }
        ), 400

    display_name = request.form.get("display_name")
    email = request.form.get("email")

    try:
        contributor = _get_or_create_guest_contributor(
            project, share_link, display_name, email
        )

        recipe_image = process_and_save_image(
            file, file.filename, folder=f"book-projects/{project.id}"
        )
        db.session.add(recipe_image)
        db.session.flush()

        processing_job = ProcessingJob(
            image_id=recipe_image.id,
            # No cookbook attachment for book-project submissions.
            cookbook_id=None,
            # No authenticated uploader — _create_recipe_from_parsed_data reads
            # owner_user_id from the BookProject when book_project_id is set.
            user_id=None,
            book_project_id=project.id,
            guest_contributor_id=contributor.id,
            is_original_recipe=None,
            translate_to_english=False,
        )
        db.session.add(processing_job)

        share_link.submission_count += 1
        db.session.commit()

        from app.tasks.recipe_tasks import process_single_recipe_task

        current_app.logger.info(
            f"Queuing guest submission task: project={project.id}, "
            f"contributor={contributor.id}, job={processing_job.id}"
        )
        # user_id=None — the task uses the project's owner as the Recipe.user_id.
        process_single_recipe_task.delay(processing_job.id, None)

        return jsonify(
            {
                "submission": {
                    "job_id": processing_job.id,
                    "image_id": recipe_image.id,
                    "status": "processing",
                    "contributor": contributor.to_dict(include_email=False),
                }
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Guest image submission failed for project {project.id}: {e}\n{traceback.format_exc()}"
        )
        # Force GC to clean up any image data lingering in memory after a failure,
        # matching the pattern used by the authenticated upload endpoint.
        import gc

        gc.collect()
        return jsonify({"error": "Failed to submit recipe image"}), 500


# ---------------------------------------------------------------------------
# Organizer-side submission endpoints
#
# Mirror the guest /by-token/<token>/submit-* endpoints, but for the organizer
# contributing recipes directly to their own project. No GuestContributor is
# created — the resulting Recipe is owned by the organizer with
# guest_contributor_id null, so the submissions list will show "Added by you".
# ---------------------------------------------------------------------------


def _build_organizer_recipe(
    *,
    project: BookProject,
    parsed_recipe: dict,
    current_user_id: int,
    fallback_text: str = "",
    source_url: Optional[str] = None,
    is_original_recipe: Optional[bool] = None,
) -> Recipe:
    """Build a Recipe owned by ``current_user_id`` and attached to ``project``.
    Doesn't commit — the caller commits after any additional bookkeeping."""
    recipe_title = parsed_recipe.get("title") or "Untitled Recipe"
    if not str(recipe_title).strip():
        recipe_title = "Untitled Recipe"

    recipe = Recipe(
        title=recipe_title,
        description=parsed_recipe.get("description"),
        user_id=current_user_id,
        uploaded_by_id=current_user_id,
        book_project_id=project.id,
        guest_contributor_id=None,
        is_public=False,
        is_original_recipe=is_original_recipe,
        source=source_url,
        prep_time=safe_int_conversion(parsed_recipe.get("prep_time")),
        cook_time=safe_int_conversion(parsed_recipe.get("cook_time")),
        servings=safe_int_conversion(parsed_recipe.get("servings")),
        difficulty=parsed_recipe.get("difficulty"),
        course_type=parsed_recipe.get("course_type"),
    )
    db.session.add(recipe)
    db.session.flush()

    create_recipe_ingredients(recipe.id, parsed_recipe)
    create_recipe_instructions(recipe.id, parsed_recipe, fallback_text)
    create_recipe_tags(recipe.id, parsed_recipe)
    return recipe


@bp.route("/<int:project_id>/contributions/submit-text", methods=["POST"])
@require_auth
def submit_text_as_organizer(current_user, project_id: int) -> Response:
    """Organizer adds a recipe to their own project via pasted text."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json(silent=True) or {}
    recipe_text = (data.get("text") or "").strip()
    if not recipe_text:
        return jsonify({"error": "No recipe text provided"}), 400

    max_text_length = current_app.config.get("MAX_RECIPE_TEXT_LENGTH", 50000)
    if len(recipe_text) > max_text_length:
        return jsonify(
            {"error": f"Recipe text too long (max {max_text_length} chars)"}
        ), 400

    try:
        parser = RecipeParser()
        parsed_recipe = parser.parse_recipe_text(recipe_text, translate_to_english=False)
        recipe = _build_organizer_recipe(
            project=project,
            parsed_recipe=parsed_recipe,
            current_user_id=current_user.id,
            fallback_text=recipe_text,
        )
        db.session.commit()
        return jsonify(
            {"submission": {"recipe_id": recipe.id, "title": recipe.title}}
        ), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Organizer text submission failed for project {project.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to submit recipe"}), 500


@bp.route("/<int:project_id>/contributions/submit-url", methods=["POST"])
@require_auth
def submit_url_as_organizer(current_user, project_id: int) -> Response:
    """Organizer adds a recipe to their own project via a URL."""
    from app.services.url_recipe_service import (
        BotProtectionError,
        RecipeNotFoundError,
        UrlFetchError,
        UrlRecipeService,
        UrlValidationError,
    )

    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    url_service = UrlRecipeService()
    try:
        result = url_service.import_from_url(url, translate_to_english=False)
    except UrlValidationError as e:
        return jsonify({"error": str(e)}), 400
    except UrlFetchError as e:
        return jsonify({"error": str(e)}), 400
    except BotProtectionError as e:
        return jsonify({"error": str(e)}), 403
    except RecipeNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        current_app.logger.error(
            f"Organizer URL parse failed for project {project.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to fetch or parse the URL"}), 500

    parsed_recipe = result["recipe_data"]
    source_url = result["source_url"]

    try:
        recipe = _build_organizer_recipe(
            project=project,
            parsed_recipe=parsed_recipe,
            current_user_id=current_user.id,
            source_url=source_url,
            # URL imports come from publicly-accessible pages — matches the
            # existing convention for is_original_recipe on URL imports.
            is_original_recipe=True,
        )
        db.session.commit()
        return jsonify(
            {
                "submission": {
                    "recipe_id": recipe.id,
                    "title": recipe.title,
                    "source": source_url,
                }
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Organizer URL submission persist failed for project {project.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to submit recipe"}), 500


@bp.route("/<int:project_id>/contributions/from-collection", methods=["POST"])
@require_auth
def add_recipes_from_collection(current_user, project_id: int) -> Response:
    """Attach existing recipes from the organizer's collection to this project.

    Body: ``{"recipe_ids": [<int>, ...]}``

    Only recipes owned by the current user are accepted. Idempotent — recipes
    already attached to this project are reported as ``already_added`` and
    don't error out, so the UI can fire-and-forget without checking state
    beforehand. Recipes that exist but belong to another user or are not
    found at all show up under ``errors`` with a short reason.
    """
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json(silent=True) or {}
    raw_ids = data.get("recipe_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return jsonify({"error": "recipe_ids must be a non-empty list"}), 400

    try:
        recipe_ids = [int(r) for r in raw_ids]
    except (TypeError, ValueError):
        return jsonify({"error": "recipe_ids must be integers"}), 400

    added: list[int] = []
    already_added: list[int] = []
    errors: list[dict] = []

    try:
        for rid in recipe_ids:
            recipe = db.session.get(Recipe, rid)
            if not recipe:
                errors.append({"id": rid, "reason": "not_found"})
                continue
            if recipe.user_id != current_user.id:
                # Don't leak existence — same shape as not_found from the
                # caller's perspective.
                errors.append({"id": rid, "reason": "not_found"})
                continue
            if recipe.book_project_id == project.id:
                already_added.append(rid)
                continue

            recipe.book_project_id = project.id
            # Recipes added from collection start out included (organizer chose
            # them explicitly), and any prior exclusion is reset.
            recipe.is_excluded_from_project = False
            added.append(rid)

        db.session.commit()
        return jsonify(
            {"added": added, "already_added": already_added, "errors": errors}
        ), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to add recipes from collection to project {project.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to add recipes"}), 500


@bp.route("/<int:project_id>/contributions/submit-image", methods=["POST"])
@require_auth
@rate_limit_upload
def submit_image_as_organizer(current_user, project_id: int) -> Response:
    """Organizer adds a recipe via image upload. Async via Celery, same as the
    guest image path — the resulting Recipe is owned by the organizer."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify(
            {"error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}
        ), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    file_size_mb = file_size / (1024 * 1024)
    max_upload_size = current_app.config.get("MAX_UPLOAD_SIZE", 8)
    if file_size_mb > max_upload_size:
        return jsonify(
            {
                "error": (
                    f"File too large ({file_size_mb:.1f}MB). "
                    f"Please use files smaller than {max_upload_size}MB."
                )
            }
        ), 400

    try:
        recipe_image = process_and_save_image(
            file, file.filename, folder=f"book-projects/{project.id}"
        )
        db.session.add(recipe_image)
        db.session.flush()

        processing_job = ProcessingJob(
            image_id=recipe_image.id,
            cookbook_id=None,
            user_id=current_user.id,
            book_project_id=project.id,
            guest_contributor_id=None,
            is_original_recipe=None,
            translate_to_english=False,
        )
        db.session.add(processing_job)
        db.session.commit()

        from app.tasks.recipe_tasks import process_single_recipe_task

        current_app.logger.info(
            f"Queuing organizer-submitted task: project={project.id}, "
            f"user={current_user.id}, job={processing_job.id}"
        )
        process_single_recipe_task.delay(processing_job.id, current_user.id)

        return jsonify(
            {
                "submission": {
                    "job_id": processing_job.id,
                    "image_id": recipe_image.id,
                    "status": "processing",
                }
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Organizer image submission failed for project {project.id}: {e}\n{traceback.format_exc()}"
        )
        import gc

        gc.collect()
        return jsonify({"error": "Failed to submit recipe image"}), 500


# ---------------------------------------------------------------------------
# Export endpoints (PDF preview + paid clean export)
# ---------------------------------------------------------------------------


@bp.route("/<int:project_id>/export/preview", methods=["POST"])
@require_auth
def create_export_preview(current_user, project_id: int) -> Response:
    """Render a free watermarked PDF preview of the BookProject. Synchronous.
    Returns the export id so the caller can immediately fetch the file from
    /exports/<export_id>/download."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    from app.services.book_project_pdf_service import render_book_project_pdf

    try:
        rendered = render_book_project_pdf(project, watermarked=True)
    except FileNotFoundError as e:
        current_app.logger.error(
            f"Preview template missing for project {project_id}: {e}"
        )
        return jsonify({"error": "Template not found"}), 500
    except Exception as e:
        current_app.logger.error(
            f"Preview PDF render failed for project {project_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to render preview PDF"}), 500

    try:
        export = BookProjectExport(
            project_id=project.id,
            user_id=current_user.id,
            payment_id=None,
            pdf_file_path=rendered["pdf_file_path"],
            cloudinary_public_id=rendered["cloudinary_public_id"],
            cloudinary_url=rendered["cloudinary_url"],
            is_watermarked=True,
        )
        db.session.add(export)
        db.session.commit()
        return jsonify(
            {
                "export": export.to_dict(),
                "download_url": (
                    f"/api/book-projects/{project.id}/exports/{export.id}/download"
                ),
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to persist preview export for project {project_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to record preview"}), 500


@bp.route("/<int:project_id>/export/purchase", methods=["POST"])
@require_auth
def create_export_purchase(current_user, project_id: int) -> Response:
    """Start a paid clean-PDF export. Creates a placeholder BookProjectExport
    + a Stripe PaymentIntent; the webhook handler fills in pdf_file_path once
    the payment succeeds."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    try:
        # Placeholder export row — pdf_file_path filled in by the webhook.
        export = BookProjectExport(
            project_id=project.id,
            user_id=current_user.id,
            payment_id=None,
            pdf_file_path=None,
            is_watermarked=False,
        )
        db.session.add(export)
        db.session.flush()

        from app.services.stripe_service import StripeService

        stripe_service = StripeService()
        intent_info = stripe_service.create_book_project_export_payment_intent(
            user=current_user, project=project, export_id=export.id
        )

        return jsonify({"export_id": export.id, **intent_info}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to create export purchase for project {project_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to start export purchase"}), 500


@bp.route("/<int:project_id>/export/regenerate", methods=["POST"])
@require_auth
def regenerate_clean_export(current_user, project_id: int) -> Response:
    """Re-render the clean PDF for a project the user already paid for. Synchronous —
    returns the new export row directly so the frontend can download immediately.
    No new Stripe charge: the original payment unlocks unlimited regenerations of
    the clean version of this project. Requires the user to already have at least
    one paid clean export for this project."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # Gate: at least one previously-paid clean export must exist for this user
    # on this project. Without this check anyone could call regenerate to bypass
    # the paywall.
    has_paid_clean = (
        BookProjectExport.query.filter_by(
            project_id=project.id,
            user_id=current_user.id,
            is_watermarked=False,
        )
        .filter(BookProjectExport.payment_id.isnot(None))
        .first()
        is not None
    )
    if not has_paid_clean:
        return jsonify(
            {"error": "Buy the clean PDF first; regeneration is free after that"}
        ), 403

    from app.services.book_project_pdf_service import render_book_project_pdf

    try:
        rendered = render_book_project_pdf(project, watermarked=False)
    except FileNotFoundError as e:
        current_app.logger.error(
            f"Regenerate template missing for project {project_id}: {e}"
        )
        return jsonify({"error": "Template not found"}), 500
    except Exception as e:
        current_app.logger.error(
            f"Regenerate render failed for project {project_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to render PDF"}), 500

    try:
        export = BookProjectExport(
            project_id=project.id,
            user_id=current_user.id,
            payment_id=None,  # regenerated rows don't have their own payment
            pdf_file_path=rendered["pdf_file_path"],
            cloudinary_public_id=rendered["cloudinary_public_id"],
            cloudinary_url=rendered["cloudinary_url"],
            is_watermarked=False,
        )
        db.session.add(export)
        db.session.commit()
        return jsonify(
            {
                "export": export.to_dict(),
                "download_url": (
                    f"/api/book-projects/{project.id}/exports/{export.id}/download"
                ),
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to persist regenerated export for project {project_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to record export"}), 500


@bp.route("/<int:project_id>/exports", methods=["GET"])
@require_auth
def list_exports(current_user, project_id: int) -> Response:
    """List BookProjectExports for this project that the current user has
    requested. Includes both watermarked previews and paid clean exports;
    the consumer (frontend) can filter or sort however it wants."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    exports = (
        BookProjectExport.query.filter_by(
            project_id=project.id, user_id=current_user.id
        )
        .order_by(BookProjectExport.created_at.desc())
        .all()
    )
    return jsonify({"exports": [e.to_dict() for e in exports]}), 200


@bp.route(
    "/<int:project_id>/exports/<int:export_id>/download", methods=["GET"]
)
@require_auth
def download_export(current_user, project_id: int, export_id: int) -> Response:
    """Stream the generated PDF if the caller owns it. Paid exports that
    haven't finished rendering yet return 202 so the frontend can poll
    rather than treating it as a hard failure."""
    project = _project_for_owner(project_id, current_user)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    export = BookProjectExport.query.filter_by(
        id=export_id, project_id=project.id, user_id=current_user.id
    ).first()
    if not export:
        return jsonify({"error": "Export not found"}), 404

    if not export.cloudinary_url and not export.pdf_file_path:
        # Paid exports are rendered by the webhook; until that fires the file
        # isn't stored anywhere. Frontend can poll the list endpoint to detect
        # ready.
        return jsonify(
            {"error": "Export is still being generated", "status": "pending"}
        ), 202

    download_name = (
        f"book-project-{project.id}"
        f"{'-preview' if export.is_watermarked else ''}.pdf"
    )

    if export.cloudinary_url:
        # Proxy the download so the client never sees the Cloudinary URL
        # (which is publicly resolvable — we want all access to go through
        # the auth'd endpoint).
        try:
            upstream = requests.get(export.cloudinary_url, stream=True, timeout=30)
            upstream.raise_for_status()
        except requests.RequestException as e:
            current_app.logger.error(
                f"Failed to fetch export from Cloudinary: export={export.id} "
                f"public_id={export.cloudinary_public_id}: {e}\n{traceback.format_exc()}"
            )
            return jsonify({"error": "Export file is missing"}), 410

        def _proxy():
            try:
                for chunk in upstream.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        return Response(
            stream_with_context(_proxy()),
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{download_name}"',
            },
        )

    if not os.path.exists(export.pdf_file_path):
        current_app.logger.error(
            f"Export file missing from disk: export={export.id} path={export.pdf_file_path}"
        )
        return jsonify({"error": "Export file is missing"}), 410

    return send_file(
        export.pdf_file_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )

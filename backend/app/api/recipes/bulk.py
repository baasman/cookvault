"""
Bulk operation endpoints for recipes: batch delete, group management, privacy, and tags.
"""

import traceback
from pathlib import Path

from flask import Response, current_app, jsonify, request

from app import db
from app.api import bp
from app.api.auth import require_auth, should_apply_user_filter
from app.models import Recipe, RecipeGroup, Tag, CopyrightConsent
from app.models.recipe import recipe_group_memberships
from app.services.cloudinary_service import cloudinary_service

MAX_BULK_SIZE = 50


def _validate_recipe_ids(data: dict) -> tuple[list[int] | None, Response | None]:
    """Validate and extract recipe_ids from request data.
    Returns (recipe_ids, error_response). One will always be None.
    """
    if not data or "recipe_ids" not in data:
        return None, (jsonify({"error": "recipe_ids is required"}), 400)

    recipe_ids = data["recipe_ids"]
    if not isinstance(recipe_ids, list) or not recipe_ids:
        return None, (jsonify({"error": "recipe_ids must be a non-empty list"}), 400)

    if len(recipe_ids) > MAX_BULK_SIZE:
        return None, (
            jsonify(
                {"error": f"Cannot process more than {MAX_BULK_SIZE} recipes at once"}
            ),
            400,
        )

    if not all(isinstance(rid, int) for rid in recipe_ids):
        return None, (jsonify({"error": "All recipe_ids must be integers"}), 400)

    return recipe_ids, None


@bp.route("/recipes/bulk/delete", methods=["POST"])
@require_auth
def bulk_delete_recipes(current_user) -> Response:
    """Delete multiple recipes at once."""
    data = request.get_json()
    recipe_ids, error = _validate_recipe_ids(data)
    if error:
        return error

    deleted = []
    errors = []
    is_admin = not should_apply_user_filter(current_user)

    try:
        recipes = Recipe.query.filter(Recipe.id.in_(recipe_ids)).all()
        found_ids = {r.id for r in recipes}

        for rid in recipe_ids:
            if rid not in found_ids:
                errors.append({"id": rid, "reason": "Recipe not found"})

        for recipe in recipes:
            if (
                not is_admin
                and recipe.user_id != current_user.id
                and recipe.uploaded_by_id != current_user.id
            ):
                errors.append({"id": recipe.id, "reason": "Access denied"})
                continue

            # Clean up images
            for image in recipe.images:
                try:
                    if image.cloudinary_public_id and cloudinary_service.is_enabled():
                        cloudinary_service.delete_image(image.cloudinary_public_id)
                    if image.file_path:
                        file_path = Path(image.file_path)
                        if file_path.exists():
                            file_path.unlink()
                except Exception as e:
                    current_app.logger.error(
                        f"Error cleaning up image {image.id} for recipe {recipe.id}: {e}"
                    )

            db.session.delete(recipe)
            deleted.append(recipe.id)

        db.session.commit()
        current_app.logger.info(
            f"Bulk deleted {len(deleted)} recipes by user {current_user.id}"
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Bulk delete failed for user {current_user.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Bulk delete failed"}), 500

    return jsonify({"deleted": deleted, "errors": errors}), 200


@bp.route("/recipes/bulk/add-to-group", methods=["POST"])
@require_auth
def bulk_add_to_group(current_user) -> Response:
    """Add multiple recipes to a group."""
    data = request.get_json()
    recipe_ids, error = _validate_recipe_ids(data)
    if error:
        return error

    group_id = data.get("group_id")
    if not group_id or not isinstance(group_id, int):
        return jsonify({"error": "group_id is required and must be an integer"}), 400

    try:
        group = RecipeGroup.query.filter_by(
            id=group_id, user_id=current_user.id
        ).first()
        if not group:
            return jsonify({"error": "Recipe group not found"}), 404

        recipes = Recipe.query.filter(Recipe.id.in_(recipe_ids)).all()
        found_ids = {r.id for r in recipes}

        # Get existing memberships
        existing = set()
        rows = db.session.execute(
            recipe_group_memberships.select().where(
                recipe_group_memberships.c.group_id == group_id,
                recipe_group_memberships.c.recipe_id.in_(recipe_ids),
            )
        ).fetchall()
        existing = {row.recipe_id for row in rows}

        # Get current max order
        max_order = (
            db.session.execute(
                db.text(
                    'SELECT COALESCE(MAX("order"), 0) FROM recipe_group_memberships WHERE group_id = :gid'
                ),
                {"gid": group_id},
            ).scalar()
            or 0
        )

        added = []
        already_in_group = []
        errors = []
        next_order = max_order

        for rid in recipe_ids:
            if rid not in found_ids:
                errors.append({"id": rid, "reason": "Recipe not found"})
                continue

            recipe = next(r for r in recipes if r.id == rid)
            if recipe.user_id != current_user.id and not recipe.is_public:
                errors.append({"id": rid, "reason": "Recipe not accessible"})
                continue

            if rid in existing:
                already_in_group.append(rid)
                continue

            next_order += 1
            db.session.execute(
                recipe_group_memberships.insert().values(
                    group_id=group_id, recipe_id=rid, order=next_order
                )
            )
            added.append(rid)

        # Update cover image from the last added recipe
        if added:
            last_recipe = next(r for r in recipes if r.id == added[-1])
            if last_recipe.images and len(last_recipe.images) > 0:
                primary_image = last_recipe.images[0]
                if primary_image.cloudinary_url:
                    group.cover_image_url = primary_image.cloudinary_url
                else:
                    group.cover_image_url = f"/api/images/{primary_image.filename}"

        db.session.commit()
        current_app.logger.info(
            f"Bulk added {len(added)} recipes to group {group_id} by user {current_user.id}"
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Bulk add-to-group failed for user {current_user.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Bulk add to group failed"}), 500

    return jsonify(
        {"added": added, "already_in_group": already_in_group, "errors": errors}
    ), 200


@bp.route("/recipes/bulk/remove-from-group", methods=["POST"])
@require_auth
def bulk_remove_from_group(current_user) -> Response:
    """Remove multiple recipes from a group."""
    data = request.get_json()
    recipe_ids, error = _validate_recipe_ids(data)
    if error:
        return error

    group_id = data.get("group_id")
    if not group_id or not isinstance(group_id, int):
        return jsonify({"error": "group_id is required and must be an integer"}), 400

    try:
        group = RecipeGroup.query.filter_by(
            id=group_id, user_id=current_user.id
        ).first()
        if not group:
            return jsonify({"error": "Recipe group not found"}), 404

        result = db.session.execute(
            recipe_group_memberships.delete().where(
                recipe_group_memberships.c.group_id == group_id,
                recipe_group_memberships.c.recipe_id.in_(recipe_ids),
            )
        )
        removed_count = result.rowcount

        db.session.commit()
        current_app.logger.info(
            f"Bulk removed {removed_count} recipes from group {group_id} by user {current_user.id}"
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Bulk remove-from-group failed for user {current_user.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Bulk remove from group failed"}), 500

    return jsonify({"removed": removed_count}), 200


@bp.route("/recipes/bulk/privacy", methods=["POST"])
@require_auth
def bulk_toggle_privacy(current_user) -> Response:
    """Toggle privacy for multiple recipes (private -> public only)."""
    data = request.get_json()
    recipe_ids, error = _validate_recipe_ids(data)
    if error:
        return error

    is_public = data.get("is_public")
    if not isinstance(is_public, bool):
        return jsonify({"error": "is_public must be a boolean"}), 400

    if not is_public:
        return jsonify(
            {"error": "Bulk privacy toggle only supports making recipes public"}
        ), 400

    copyright_consent = data.get("copyright_consent", {})
    required_consents = [
        "rightsToShare",
        "understandsPublic",
        "personalUseOnly",
        "noCopyrightViolation",
    ]
    for consent in required_consents:
        if not copyright_consent.get(consent):
            return jsonify(
                {"error": f"Copyright consent required: {consent} must be acknowledged"}
            ), 400

    try:
        recipes = Recipe.query.filter(
            Recipe.id.in_(recipe_ids),
            Recipe.user_id == current_user.id,
        ).all()
        found_ids = {r.id for r in recipes}

        updated = []
        errors = []

        for rid in recipe_ids:
            if rid not in found_ids:
                errors.append(
                    {"id": rid, "reason": "Recipe not found or access denied"}
                )
                continue

            recipe = next(r for r in recipes if r.id == rid)

            if recipe.is_public:
                errors.append({"id": rid, "reason": "Recipe is already public"})
                continue

            can_publish, restriction_reason = recipe.can_be_published()
            if not can_publish:
                errors.append({"id": rid, "reason": restriction_reason})
                continue

            consent_record = CopyrightConsent(
                user_id=current_user.id,
                recipe_id=recipe.id,
                consent_data=copyright_consent,
                consent_type="publish",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
            )
            db.session.add(consent_record)
            recipe.publish()
            updated.append(rid)

        db.session.commit()
        current_app.logger.info(
            f"Bulk privacy update: {len(updated)} recipes made public by user {current_user.id}"
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Bulk privacy toggle failed for user {current_user.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Bulk privacy update failed"}), 500

    return jsonify({"updated": updated, "errors": errors}), 200


@bp.route("/recipes/bulk/tags", methods=["POST"])
@require_auth
def bulk_update_tags(current_user) -> Response:
    """Bulk update tags on multiple recipes. Supports add, remove, or set actions."""
    data = request.get_json()
    recipe_ids, error = _validate_recipe_ids(data)
    if error:
        return error

    tags = data.get("tags")
    if not isinstance(tags, list):
        return jsonify({"error": "tags must be a list of strings"}), 400

    tag_names = [t.strip() for t in tags if isinstance(t, str) and t.strip()]

    action = data.get("action", "add")
    if action not in ("add", "remove", "set"):
        return jsonify({"error": "action must be 'add', 'remove', or 'set'"}), 400

    is_admin = not should_apply_user_filter(current_user)

    try:
        if is_admin:
            recipes = Recipe.query.filter(Recipe.id.in_(recipe_ids)).all()
        else:
            recipes = Recipe.query.filter(
                Recipe.id.in_(recipe_ids),
                db.or_(
                    Recipe.user_id == current_user.id,
                    Recipe.uploaded_by_id == current_user.id,
                ),
            ).all()

        found_ids = {r.id for r in recipes}
        updated = []
        errors = []

        for rid in recipe_ids:
            if rid not in found_ids:
                errors.append(
                    {"id": rid, "reason": "Recipe not found or access denied"}
                )

        for recipe in recipes:
            if action == "set":
                Tag.query.filter_by(recipe_id=recipe.id).delete()
                for name in tag_names:
                    db.session.add(Tag(recipe_id=recipe.id, name=name))

            elif action == "add":
                existing_tags = {
                    t.name.lower()
                    for t in Tag.query.filter_by(recipe_id=recipe.id).all()
                }
                for name in tag_names:
                    if name.lower() not in existing_tags:
                        db.session.add(Tag(recipe_id=recipe.id, name=name))

            elif action == "remove":
                Tag.query.filter(
                    Tag.recipe_id == recipe.id,
                    db.func.lower(Tag.name).in_([n.lower() for n in tag_names]),
                ).delete(synchronize_session="fetch")

            updated.append(recipe.id)

        db.session.commit()
        current_app.logger.info(
            f"Bulk tags {action}: {len(updated)} recipes updated by user {current_user.id}"
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Bulk tags update failed for user {current_user.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Bulk tags update failed"}), 500

    return jsonify({"updated": updated, "errors": errors}), 200

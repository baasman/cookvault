"""
Smart Folders API - Auto-populating recipe folders based on filter rules.
"""

import json
import logging
import traceback

from flask import Blueprint, Response, jsonify, request

from app import db
from app.api.auth import require_auth
from app.models.recipe import SmartFolder
from app.services.smart_folder_service import build_query, validate_rules

logger = logging.getLogger(__name__)

bp = Blueprint("smart_folders", __name__)


@bp.route("/smart-folders", methods=["GET"])
@require_auth
def list_smart_folders(current_user) -> Response:
    """List all smart folders for the current user with live recipe counts."""
    try:
        folders = SmartFolder.query.filter_by(user_id=current_user.id).order_by(
            SmartFolder.updated_at.desc()
        ).all()

        result = []
        for folder in folders:
            try:
                rules = json.loads(folder.rules)
                count = build_query(rules, current_user.id).count()
            except Exception as e:
                logger.error(f"Error computing count for smart folder {folder.id}: {e}")
                count = 0
            result.append(folder.to_dict(recipe_count=count))

        return jsonify({"smart_folders": result}), 200

    except Exception as e:
        logger.error(
            f"Error listing smart folders for user {current_user.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to list smart folders"}), 500


@bp.route("/smart-folders", methods=["POST"])
@require_auth
def create_smart_folder(current_user) -> Response:
    """Create a new smart folder."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    rules = data.get("rules", {})
    validation_errors = validate_rules(rules)
    if validation_errors:
        return jsonify({"error": "Invalid rules", "details": validation_errors}), 400

    try:
        folder = SmartFolder(
            name=name[:200],
            description=data.get("description", "").strip() or None,
            user_id=current_user.id,
            rules=json.dumps(rules),
            icon=data.get("icon"),
        )
        db.session.add(folder)
        db.session.commit()

        count = build_query(rules, current_user.id).count()
        logger.info(f"Created smart folder '{name}' (id={folder.id}) for user {current_user.id}")

        return jsonify({"smart_folder": folder.to_dict(recipe_count=count)}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Error creating smart folder for user {current_user.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to create smart folder"}), 500


@bp.route("/smart-folders/<int:folder_id>", methods=["GET"])
@require_auth
def get_smart_folder(current_user, folder_id: int) -> Response:
    """Get a smart folder's details."""
    folder = SmartFolder.query.filter_by(
        id=folder_id, user_id=current_user.id
    ).first()
    if not folder:
        return jsonify({"error": "Smart folder not found"}), 404

    try:
        rules = json.loads(folder.rules)
        count = build_query(rules, current_user.id).count()
    except Exception:
        count = 0

    return jsonify({"smart_folder": folder.to_dict(recipe_count=count)}), 200


@bp.route("/smart-folders/<int:folder_id>", methods=["PUT"])
@require_auth
def update_smart_folder(current_user, folder_id: int) -> Response:
    """Update a smart folder's name, description, or rules."""
    folder = SmartFolder.query.filter_by(
        id=folder_id, user_id=current_user.id
    ).first()
    if not folder:
        return jsonify({"error": "Smart folder not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    try:
        if "name" in data:
            name = data["name"].strip()
            if not name:
                return jsonify({"error": "Name cannot be empty"}), 400
            folder.name = name[:200]

        if "description" in data:
            folder.description = data["description"].strip() or None

        if "icon" in data:
            folder.icon = data["icon"]

        if "rules" in data:
            validation_errors = validate_rules(data["rules"])
            if validation_errors:
                return jsonify({"error": "Invalid rules", "details": validation_errors}), 400
            folder.rules = json.dumps(data["rules"])

        db.session.commit()

        rules = json.loads(folder.rules)
        count = build_query(rules, current_user.id).count()
        logger.info(f"Updated smart folder {folder_id} for user {current_user.id}")

        return jsonify({"smart_folder": folder.to_dict(recipe_count=count)}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Error updating smart folder {folder_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to update smart folder"}), 500


@bp.route("/smart-folders/<int:folder_id>", methods=["DELETE"])
@require_auth
def delete_smart_folder(current_user, folder_id: int) -> Response:
    """Delete a smart folder."""
    folder = SmartFolder.query.filter_by(
        id=folder_id, user_id=current_user.id
    ).first()
    if not folder:
        return jsonify({"error": "Smart folder not found"}), 404

    try:
        db.session.delete(folder)
        db.session.commit()
        logger.info(f"Deleted smart folder {folder_id} for user {current_user.id}")
        return jsonify({"message": "Smart folder deleted"}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Error deleting smart folder {folder_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to delete smart folder"}), 500


@bp.route("/smart-folders/<int:folder_id>/recipes", methods=["GET"])
@require_auth
def get_smart_folder_recipes(current_user, folder_id: int) -> Response:
    """Get paginated recipes matching a smart folder's rules."""
    folder = SmartFolder.query.filter_by(
        id=folder_id, user_id=current_user.id
    ).first()
    if not folder:
        return jsonify({"error": "Smart folder not found"}), 404

    try:
        rules = json.loads(folder.rules)
        query = build_query(rules, current_user.id)

        # Search within results
        search = request.args.get("search", "").strip()
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    db.func.lower(db.cast(db.literal_column("recipe.title"), db.Text)).ilike(search_term),
                    db.func.lower(db.cast(db.literal_column("recipe.description"), db.Text)).ilike(search_term),
                )
            )

        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 12, type=int)
        per_page = min(per_page, 50)

        total = query.count()
        recipes = query.order_by(db.desc(db.text("recipe.updated_at"))).offset(
            (page - 1) * per_page
        ).limit(per_page).all()

        is_admin = current_user.role.value == "admin" if current_user.role else False

        return jsonify({
            "recipes": [
                r.to_dict(current_user_id=current_user.id, is_admin=is_admin)
                for r in recipes
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
        }), 200

    except Exception as e:
        logger.error(
            f"Error fetching recipes for smart folder {folder_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to fetch recipes"}), 500


@bp.route("/smart-folders/preview", methods=["POST"])
@require_auth
def preview_smart_folder(current_user) -> Response:
    """Preview: run rules and return the matching recipe count."""
    data = request.get_json()
    if not data or "rules" not in data:
        return jsonify({"error": "rules are required"}), 400

    rules = data["rules"]
    validation_errors = validate_rules(rules)
    if validation_errors:
        return jsonify({"error": "Invalid rules", "details": validation_errors}), 400

    try:
        count = build_query(rules, current_user.id).count()
        return jsonify({"count": count}), 200

    except Exception as e:
        logger.error(
            f"Error previewing smart folder for user {current_user.id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to preview"}), 500

"""
API endpoints for managing recipe sources.
Sources are auto-created domains that recipes are imported from.
"""

import logging
import traceback
from typing import Tuple

from flask import Response, current_app, jsonify, request
from sqlalchemy import desc

from app import db
from app.api import bp
from app.api.auth import require_auth
from app.models import Recipe, Source
from app.services.source_service import SourceService

logger = logging.getLogger(__name__)


@bp.route("/sources", methods=["GET"])
@require_auth
def list_sources(current_user) -> Tuple[Response, int]:
    """
    List all sources for the current user.

    Query parameters:
    - page: Page number (default 1)
    - per_page: Items per page (default 20, max 100)
    - sort: Sort field (default 'recipe_count')
    - order: Sort order ('asc' or 'desc', default 'desc')
    - search: Search term for domain/name
    """
    try:
        # Pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Sort parameters
        sort_field = request.args.get("sort", "recipe_count")
        sort_order = request.args.get("order", "desc")

        # Search parameter
        search = request.args.get("search", "").strip()

        # Build query
        query = Source.query.filter_by(user_id=current_user.id)

        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                db.or_(
                    Source.domain.ilike(search_term),
                    Source.name.ilike(search_term),
                )
            )

        # Apply sorting
        if sort_field == "domain":
            sort_column = Source.domain
        elif sort_field == "name":
            sort_column = Source.name
        elif sort_field == "created_at":
            sort_column = Source.created_at
        else:
            sort_column = Source.recipe_count

        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            "sources": [source.to_dict() for source in pagination.items],
            "pagination": {
                "page": pagination.page,
                "pages": pagination.pages,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }), 200

    except Exception as e:
        logger.error(
            f"Error listing sources for user {current_user.id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to list sources"}), 500


@bp.route("/sources/<int:source_id>", methods=["GET"])
@require_auth
def get_source(current_user, source_id: int) -> Tuple[Response, int]:
    """
    Get a specific source with its recipes.

    Query parameters:
    - page: Page number for recipes (default 1)
    - per_page: Recipes per page (default 20, max 100)
    - search: Search term for recipe titles
    """
    try:
        # Find the source
        source = Source.query.filter_by(
            id=source_id,
            user_id=current_user.id
        ).first()

        if not source:
            return jsonify({"error": "Source not found"}), 404

        # Pagination for recipes
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)
        search = request.args.get("search", "").strip()

        # Build query for recipes from this source
        recipe_query = Recipe.query.filter_by(
            source_id=source_id,
            user_id=current_user.id
        )

        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            recipe_query = recipe_query.filter(Recipe.title.ilike(search_term))

        # Order by created_at descending
        recipe_query = recipe_query.order_by(desc(Recipe.created_at))

        # Paginate
        pagination = recipe_query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            "source": source.to_dict(),
            "recipes": [
                recipe.to_dict(current_user_id=current_user.id)
                for recipe in pagination.items
            ],
            "pagination": {
                "page": pagination.page,
                "pages": pagination.pages,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }), 200

    except Exception as e:
        logger.error(
            f"Error getting source {source_id} for user {current_user.id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to get source"}), 500


@bp.route("/sources/<int:source_id>", methods=["PATCH"])
@require_auth
def update_source(current_user, source_id: int) -> Tuple[Response, int]:
    """
    Update a source (currently only the name can be updated).

    Request body:
    - name: New display name for the source (optional, can be null to clear)
    """
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "No JSON data provided"}), 400

        # Get the name from request (can be None to clear)
        name = data.get("name")

        # Update the source
        source = SourceService.update_source_name(
            source_id=source_id,
            user_id=current_user.id,
            name=name
        )

        if not source:
            return jsonify({"error": "Source not found"}), 404

        db.session.commit()

        current_app.logger.info(
            f"Updated source {source_id} name to '{name}' for user {current_user.id}"
        )

        return jsonify(source.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Error updating source {source_id} for user {current_user.id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to update source"}), 500

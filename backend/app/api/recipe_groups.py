"""
Recipe Groups API - Endpoints for managing user recipe groups
"""

from flask import Response, current_app, jsonify, request
from werkzeug.utils import secure_filename
from pathlib import Path
import uuid
import os

from app import db
from app.api import bp
from app.api.auth import require_auth
from app.models import RecipeGroup, Recipe, User, recipe_group_memberships


@bp.route("/recipe-groups", methods=["GET"])
@require_auth
def get_recipe_groups(current_user) -> Response:
    """Get all recipe groups for the current user."""
    try:
        groups = RecipeGroup.query.filter_by(user_id=current_user.id).order_by(
            RecipeGroup.updated_at.desc()
        ).all()
        
        return jsonify({
            "groups": [group.to_dict() for group in groups],
            "total": len(groups)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching recipe groups: {e}")
        return jsonify({"error": "Failed to fetch recipe groups"}), 500


@bp.route("/recipe-groups", methods=["POST"])
@require_auth
def create_recipe_group(current_user) -> Response:
    """Create a new recipe group."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Group name is required"}), 400
        
        if len(name) > 200:
            return jsonify({"error": "Group name cannot exceed 200 characters"}), 400
        
        # Check for duplicate group names for this user
        existing_group = RecipeGroup.query.filter_by(
            user_id=current_user.id, 
            name=name
        ).first()
        if existing_group:
            return jsonify({"error": "A group with this name already exists"}), 400
        
        # Create new group
        group = RecipeGroup(
            name=name,
            description=data.get("description", "").strip() or None,
            user_id=current_user.id,
            is_private=data.get("is_private", True)
        )
        
        db.session.add(group)
        db.session.commit()
        
        return jsonify({
            "group": group.to_dict(),
            "message": "Recipe group created successfully"
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating recipe group: {e}")
        return jsonify({"error": "Failed to create recipe group"}), 500


@bp.route("/recipe-groups/<int:group_id>", methods=["GET"])
@require_auth
def get_recipe_group(current_user, group_id: int) -> Response:
    """Get a specific recipe group with its recipes."""
    try:
        group = RecipeGroup.query.filter_by(
            id=group_id, 
            user_id=current_user.id
        ).first()
        
        if not group:
            return jsonify({"error": "Recipe group not found"}), 404
        
        # Get recipes in this group with pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 12, type=int)
        search = request.args.get("search", "").strip()
        
        # Base query for recipes in this group
        recipes_query = Recipe.query.join(
            recipe_group_memberships
        ).filter(
            recipe_group_memberships.c.group_id == group_id
        ).options(
            db.joinedload(Recipe.images),
            db.joinedload(Recipe.recipe_tags)
        )
        
        # Apply search filter if provided
        if search:
            recipes_query = recipes_query.filter(
                Recipe.title.ilike(f"%{search}%")
            )
        
        # Order by the order in the group, then by title
        recipes_query = recipes_query.order_by(
            recipe_group_memberships.c.order,
            Recipe.title
        )
        
        # Paginate results
        recipes_paginated = recipes_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        recipes_data = []
        for recipe in recipes_paginated.items:
            recipe_dict = recipe.to_dict(include_user=False)
            # Add group-specific metadata if needed
            recipes_data.append(recipe_dict)
        
        return jsonify({
            "group": group.to_dict(),
            "recipes": recipes_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": recipes_paginated.total,
                "pages": recipes_paginated.pages,
                "has_next": recipes_paginated.has_next,
                "has_prev": recipes_paginated.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching recipe group: {e}")
        return jsonify({"error": "Failed to fetch recipe group"}), 500


@bp.route("/recipe-groups/<int:group_id>", methods=["PUT"])
@require_auth
def update_recipe_group(current_user, group_id: int) -> Response:
    """Update a recipe group."""
    try:
        group = RecipeGroup.query.filter_by(
            id=group_id, 
            user_id=current_user.id
        ).first()
        
        if not group:
            return jsonify({"error": "Recipe group not found"}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Update fields if provided
        if "name" in data:
            name = data["name"].strip()
            if not name:
                return jsonify({"error": "Group name cannot be empty"}), 400
            
            if len(name) > 200:
                return jsonify({"error": "Group name cannot exceed 200 characters"}), 400
            
            # Check for duplicate names (excluding current group)
            existing_group = RecipeGroup.query.filter_by(
                user_id=current_user.id, 
                name=name
            ).filter(RecipeGroup.id != group_id).first()
            
            if existing_group:
                return jsonify({"error": "A group with this name already exists"}), 400
            
            group.name = name
        
        if "description" in data:
            group.description = data["description"].strip() or None
        
        if "is_private" in data:
            group.is_private = bool(data["is_private"])
        
        db.session.commit()
        
        return jsonify({
            "group": group.to_dict(),
            "message": "Recipe group updated successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating recipe group: {e}")
        return jsonify({"error": "Failed to update recipe group"}), 500


@bp.route("/recipe-groups/<int:group_id>", methods=["DELETE"])
@require_auth
def delete_recipe_group(current_user, group_id: int) -> Response:
    """Delete a recipe group."""
    try:
        group = RecipeGroup.query.filter_by(
            id=group_id, 
            user_id=current_user.id
        ).first()
        
        if not group:
            return jsonify({"error": "Recipe group not found"}), 404
        
        # Delete the group (this will also remove all recipe associations)
        db.session.delete(group)
        db.session.commit()
        
        return jsonify({"message": "Recipe group deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting recipe group: {e}")
        return jsonify({"error": "Failed to delete recipe group"}), 500


@bp.route("/recipe-groups/<int:group_id>/recipes/<int:recipe_id>", methods=["POST"])
@require_auth
def add_recipe_to_group(current_user, group_id: int, recipe_id: int) -> Response:
    """Add a recipe to a recipe group."""
    try:
        # Verify the group exists and belongs to the user
        group = RecipeGroup.query.filter_by(
            id=group_id, 
            user_id=current_user.id
        ).first()
        
        if not group:
            return jsonify({"error": "Recipe group not found"}), 404
        
        # Verify the recipe exists and user has access
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404
        
        # Check if user can access this recipe (owns it or it's public)
        if recipe.user_id != current_user.id and not recipe.is_public:
            return jsonify({"error": "Recipe not accessible"}), 403
        
        # Check if recipe is already in the group
        existing_membership = db.session.execute(
            recipe_group_memberships.select().where(
                recipe_group_memberships.c.group_id == group_id,
                recipe_group_memberships.c.recipe_id == recipe_id
            )
        ).first()
        
        if existing_membership:
            return jsonify({"error": "Recipe is already in this group"}), 400
        
        # Get the next order value for this group
        max_order_result = db.session.execute(
            db.text("""
                SELECT COALESCE(MAX("order"), 0) 
                FROM recipe_group_memberships 
                WHERE group_id = :group_id
            """),
            {"group_id": group_id}
        ).scalar()
        
        next_order = (max_order_result or 0) + 1
        
        # Add recipe to group
        membership = recipe_group_memberships.insert().values(
            group_id=group_id,
            recipe_id=recipe_id,
            order=next_order
        )
        db.session.execute(membership)
        
        # Update group cover image to the most recently added recipe's image
        if recipe.images and len(recipe.images) > 0:
            # Use the first image of the recipe as the group cover image
            primary_image = recipe.images[0]
            group.cover_image_url = f"/api/images/{primary_image.filename}"
        
        db.session.commit()
        
        return jsonify({"message": "Recipe added to group successfully"}), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding recipe to group: {e}")
        return jsonify({"error": "Failed to add recipe to group"}), 500


@bp.route("/recipe-groups/<int:group_id>/recipes/<int:recipe_id>", methods=["DELETE"])
@require_auth
def remove_recipe_from_group(current_user, group_id: int, recipe_id: int) -> Response:
    """Remove a recipe from a recipe group."""
    try:
        # Verify the group exists and belongs to the user
        group = RecipeGroup.query.filter_by(
            id=group_id, 
            user_id=current_user.id
        ).first()
        
        if not group:
            return jsonify({"error": "Recipe group not found"}), 404
        
        # Check if recipe is in the group
        existing_membership = db.session.execute(
            recipe_group_memberships.select().where(
                recipe_group_memberships.c.group_id == group_id,
                recipe_group_memberships.c.recipe_id == recipe_id
            )
        ).first()
        
        if not existing_membership:
            return jsonify({"error": "Recipe is not in this group"}), 404
        
        # Remove recipe from group
        db.session.execute(
            recipe_group_memberships.delete().where(
                recipe_group_memberships.c.group_id == group_id,
                recipe_group_memberships.c.recipe_id == recipe_id
            )
        )
        
        # Update group cover image to the most recently added recipe's image
        # Find the most recently added recipe in the group that has an image
        most_recent_recipe_with_image = db.session.execute(
            db.text("""
                SELECT r.id, ri.filename 
                FROM recipe r
                JOIN recipe_group_memberships rgm ON r.id = rgm.recipe_id
                JOIN recipe_image ri ON r.id = ri.recipe_id
                WHERE rgm.group_id = :group_id
                ORDER BY rgm."order" DESC
                LIMIT 1
            """),
            {"group_id": group_id}
        ).first()
        
        if most_recent_recipe_with_image:
            # Update to the most recent recipe's image
            group.cover_image_url = f"/api/images/{most_recent_recipe_with_image.filename}"
        else:
            # No recipes with images left, clear the cover image
            group.cover_image_url = None
        
        db.session.commit()
        
        return jsonify({"message": "Recipe removed from group successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing recipe from group: {e}")
        return jsonify({"error": "Failed to remove recipe from group"}), 500
"""
Engagement endpoints for recipes: notes, ratings, and comments.
"""

from datetime import datetime

from flask import Response, current_app, jsonify, request

from app import db
from app.api import bp
from app.api.auth import optional_auth, require_auth
from app.models import Recipe, RecipeComment, RecipeNote


# Recipe Notes Endpoints


@bp.route("/recipes/<int:recipe_id>/notes", methods=["GET"])
@require_auth
def get_recipe_note(current_user, recipe_id: int) -> Response:
    """Get the owner's note for a specific recipe. Anyone who can view the recipe can see the owner's notes."""
    # First, check if the recipe exists and user can view it
    recipe = Recipe.query.get_or_404(recipe_id)

    if not recipe.can_be_viewed_by(current_user.id, current_user.role.value == "admin"):
        return jsonify({"error": "Recipe not found"}), 404

    # Get the recipe owner's note for this recipe (not the current user's note)
    note = RecipeNote.query.filter_by(
        user_id=recipe.user_id,  # Owner's note, not current user's note
        recipe_id=recipe_id,
    ).first()

    if not note:
        return jsonify({"note": None}), 200

    return jsonify({"note": note.to_dict()}), 200


@bp.route("/recipes/<int:recipe_id>/notes", methods=["POST"])
@require_auth
def save_recipe_note(current_user, recipe_id: int) -> Response:
    """Create or update user's note for a recipe. Only recipe owners can create notes."""
    # First, check if the recipe exists and user owns it
    recipe = Recipe.query.get_or_404(recipe_id)

    # Only recipe owners or uploaders can create/edit notes
    if recipe.user_id != current_user.id and recipe.uploaded_by_id != current_user.id:
        return jsonify({"error": "Only recipe owners can create notes"}), 403

    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Note content is required"}), 400

    content = data["content"].strip()
    if not content:
        return jsonify({"error": "Note content cannot be empty"}), 400

    # Limit note length (1000 characters)
    if len(content) > 1000:
        return jsonify({"error": "Note content cannot exceed 1000 characters"}), 400

    # Check if note already exists
    note = RecipeNote.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()

    if note:
        # Update existing note
        note.content = content
        note.updated_at = datetime.utcnow()
    else:
        # Create new note
        note = RecipeNote(user_id=current_user.id, recipe_id=recipe_id, content=content)
        db.session.add(note)

    try:
        db.session.commit()
        return jsonify({"note": note.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving recipe note: {e}")
        return jsonify({"error": "Failed to save note"}), 500


@bp.route("/recipes/<int:recipe_id>/notes", methods=["DELETE"])
@require_auth
def delete_recipe_note(current_user, recipe_id: int) -> Response:
    """Delete user's note for a recipe. Only recipe owners can delete notes."""
    # First, check if the recipe exists and user owns it
    recipe = Recipe.query.get_or_404(recipe_id)

    # Only recipe owners or uploaders can delete notes
    if recipe.user_id != current_user.id and recipe.uploaded_by_id != current_user.id:
        return jsonify({"error": "Only recipe owners can delete notes"}), 403

    # Get user's note for this recipe
    note = RecipeNote.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()

    if not note:
        return jsonify({"error": "Note not found"}), 404

    try:
        db.session.delete(note)
        db.session.commit()
        return jsonify({"message": "Note deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting recipe note: {e}")
        return jsonify({"error": "Failed to delete note"}), 500


# Recipe Rating Endpoints


@bp.route("/recipes/<int:recipe_id>/rating", methods=["GET"])
@optional_auth
def get_recipe_rating(current_user, recipe_id: int) -> Response:
    """Get the aggregate rating for a recipe and the current user's rating if any.

    Returns:
        - aggregate: {average_rating, rating_count, normalized_title, cookbook_id, matching_recipe_count}
        - user_rating: RecipeRating or null if user hasn't rated
    """
    from app.services.rating_service import (
        get_aggregate_rating_for_recipe,
        get_user_rating,
    )

    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    # Check if user can view this recipe
    if current_user:
        is_admin = current_user.role.value == "admin" if current_user.role else False
        if not recipe.can_be_viewed_by(current_user.id, is_admin):
            return jsonify({"error": "Recipe not found"}), 404
    else:
        # Unauthenticated users can only view public recipes
        if not recipe.is_public:
            return jsonify({"error": "Recipe not found"}), 404

    # Get aggregate rating
    aggregate = get_aggregate_rating_for_recipe(recipe_id)

    # Get user's rating if authenticated
    user_rating = None
    if current_user:
        rating_obj = get_user_rating(current_user.id, recipe_id)
        if rating_obj:
            user_rating = rating_obj.to_dict()

    return jsonify({"aggregate": aggregate, "user_rating": user_rating}), 200


@bp.route("/recipes/<int:recipe_id>/rating", methods=["POST"])
@require_auth
def submit_recipe_rating(current_user, recipe_id: int) -> Response:
    """Submit or update a rating for a recipe.

    Body: {"rating": 1-5}

    Returns:
        - aggregate: updated aggregate rating
        - user_rating: the user's rating
    """
    from app.services.rating_service import (
        submit_rating,
        get_aggregate_rating_for_recipe,
    )

    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    # Check if user can view this recipe
    is_admin = current_user.role.value == "admin" if current_user.role else False
    if not recipe.can_be_viewed_by(current_user.id, is_admin):
        return jsonify({"error": "Recipe not found"}), 404

    data = request.get_json()
    if not data or "rating" not in data:
        return jsonify({"error": "Rating value is required"}), 400

    rating_value = data["rating"]
    if not isinstance(rating_value, int) or not 1 <= rating_value <= 5:
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400

    try:
        rating_obj = submit_rating(current_user.id, recipe_id, rating_value)
        aggregate = get_aggregate_rating_for_recipe(recipe_id)

        return jsonify(
            {"aggregate": aggregate, "user_rating": rating_obj.to_dict()}
        ), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error submitting rating for recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to submit rating"}), 500


@bp.route("/recipes/<int:recipe_id>/rating", methods=["DELETE"])
@require_auth
def delete_recipe_rating(current_user, recipe_id: int) -> Response:
    """Delete the current user's rating for a recipe.

    Returns:
        - message: success message
        - aggregate: updated aggregate rating
    """
    from app.services.rating_service import (
        delete_rating,
        get_aggregate_rating_for_recipe,
    )

    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    # Check if user can view this recipe
    is_admin = current_user.role.value == "admin" if current_user.role else False
    if not recipe.can_be_viewed_by(current_user.id, is_admin):
        return jsonify({"error": "Recipe not found"}), 404

    try:
        deleted = delete_rating(current_user.id, recipe_id)

        if not deleted:
            return jsonify({"error": "No rating found to delete"}), 404

        aggregate = get_aggregate_rating_for_recipe(recipe_id)

        return jsonify(
            {"message": "Rating deleted successfully", "aggregate": aggregate}
        ), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting rating for recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to delete rating"}), 500


# Recipe Comments Endpoints


@bp.route("/recipes/<int:recipe_id>/comments", methods=["GET"])
@require_auth
def get_recipe_comments(current_user, recipe_id: int) -> Response:
    """Get paginated comments for a recipe."""
    # Check if recipe exists and user can view it
    recipe = Recipe.query.get_or_404(recipe_id)

    if not recipe.can_be_viewed_by(current_user.id, current_user.role.value == "admin"):
        return jsonify({"error": "Recipe not found"}), 404

    # Get pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = min(
        request.args.get("per_page", 20, type=int), 50
    )  # Max 50 comments per page

    # Query comments with user information, ordered by creation date (newest first)
    comments_query = RecipeComment.query.filter_by(recipe_id=recipe_id).order_by(
        RecipeComment.created_at.desc()
    )

    comments_paginated = comments_query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    return (
        jsonify(
            {
                "comments": [
                    comment.to_dict(include_user=True)
                    for comment in comments_paginated.items
                ],
                "total": comments_paginated.total,
                "pages": comments_paginated.pages,
                "current_page": page,
                "per_page": per_page,
                "has_next": comments_paginated.has_next,
                "has_prev": comments_paginated.has_prev,
            }
        ),
        200,
    )


@bp.route("/recipes/<int:recipe_id>/comments", methods=["POST"])
@require_auth
def create_recipe_comment(current_user, recipe_id: int) -> Response:
    """Create a new comment on a recipe."""
    # Check if recipe exists and user can view it
    recipe = Recipe.query.get_or_404(recipe_id)

    if not recipe.can_be_viewed_by(current_user.id, current_user.role.value == "admin"):
        return jsonify({"error": "Recipe not found"}), 404

    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Comment content is required"}), 400

    content = data["content"].strip()
    if not content:
        return jsonify({"error": "Comment content cannot be empty"}), 400

    # Limit comment length (500 characters)
    if len(content) > 500:
        return jsonify({"error": "Comment content cannot exceed 500 characters"}), 400

    # Create new comment
    comment = RecipeComment(
        recipe_id=recipe_id, user_id=current_user.id, content=content
    )

    try:
        db.session.add(comment)
        db.session.commit()

        # Return the comment with user information
        return jsonify({"comment": comment.to_dict(include_user=True)}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating comment: {e}")
        return jsonify({"error": "Failed to create comment"}), 500


@bp.route("/recipes/<int:recipe_id>/comments/<int:comment_id>", methods=["PUT"])
@require_auth
def update_recipe_comment(current_user, recipe_id: int, comment_id: int) -> Response:
    """Update a comment. Only the comment author can edit their comment."""
    # Check if recipe exists and user can view it
    recipe = Recipe.query.get_or_404(recipe_id)

    if not recipe.can_be_viewed_by(current_user.id, current_user.role.value == "admin"):
        return jsonify({"error": "Recipe not found"}), 404

    # Get the comment
    comment = RecipeComment.query.filter_by(id=comment_id, recipe_id=recipe_id).first()

    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    # Only comment author can edit their comment
    if comment.user_id != current_user.id:
        return jsonify({"error": "You can only edit your own comments"}), 403

    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Comment content is required"}), 400

    content = data["content"].strip()
    if not content:
        return jsonify({"error": "Comment content cannot be empty"}), 400

    # Limit comment length (500 characters)
    if len(content) > 500:
        return jsonify({"error": "Comment content cannot exceed 500 characters"}), 400

    # Update comment
    comment.content = content
    comment.updated_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({"comment": comment.to_dict(include_user=True)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating comment: {e}")
        return jsonify({"error": "Failed to update comment"}), 500


@bp.route("/recipes/<int:recipe_id>/comments/<int:comment_id>", methods=["DELETE"])
@require_auth
def delete_recipe_comment(current_user, recipe_id: int, comment_id: int) -> Response:
    """Delete a comment. Comment author or admin can delete."""
    # Check if recipe exists and user can view it
    recipe = Recipe.query.get_or_404(recipe_id)

    if not recipe.can_be_viewed_by(current_user.id, current_user.role.value == "admin"):
        return jsonify({"error": "Recipe not found"}), 404

    # Get the comment
    comment = RecipeComment.query.filter_by(id=comment_id, recipe_id=recipe_id).first()

    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    # Only comment author or admin can delete comment
    is_admin = current_user.role.value == "admin"
    if comment.user_id != current_user.id and not is_admin:
        return jsonify({"error": "You can only delete your own comments"}), 403

    try:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({"message": "Comment deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting comment: {e}")
        return jsonify({"error": "Failed to delete comment"}), 500

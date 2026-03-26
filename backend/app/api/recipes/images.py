"""
Image upload and serving endpoints for recipes.
"""

import traceback
from pathlib import Path
from typing import Tuple

from flask import Response, current_app, jsonify, redirect, request, send_file

from app import db
from app.api import bp
from app.api.auth import optional_auth, require_auth, should_apply_user_filter
from app.models import Cookbook, Recipe, RecipeImage, UserRole
from app.api.recipes.helpers import allowed_file, process_and_save_image


@bp.route("/recipes/<int:recipe_id>/images", methods=["POST"])
@require_auth
def upload_recipe_image(current_user, recipe_id: int) -> Tuple[Response, int]:
    """Upload an image for an existing recipe."""

    # Verify recipe exists and user has permission
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    try:
        # Use the new helper function to handle image processing
        recipe_image = process_and_save_image(file, file.filename, folder="recipes")
        recipe_image.recipe_id = recipe.id

        db.session.add(recipe_image)
        db.session.commit()

        current_app.logger.info(
            f"Image uploaded for recipe {recipe_id} by user {current_user.id}"
        )

        return (
            jsonify(
                {
                    "message": "Image uploaded successfully",
                    "image": recipe_image.to_dict(),
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Image upload failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Image upload failed"}), 500


@bp.route("/recipes/<int:recipe_id>/images/primary", methods=["POST"])
@require_auth
def upload_primary_recipe_image(current_user, recipe_id: int) -> Tuple[Response, int]:
    """Upload a primary image (food photo) for an existing recipe.

    This shifts all existing images' image_order up by 1 and
    saves the new image with image_order=0, making it the primary display image.
    """
    # Verify recipe exists and user has permission
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    try:
        # Log current image orders before modification
        existing_images = RecipeImage.query.filter_by(recipe_id=recipe.id).all()
        current_app.logger.info(
            f"Recipe {recipe_id} existing images before shift: {[(img.id, img.image_order) for img in existing_images]}"
        )

        # Shift all existing images' order up by 1
        for img in existing_images:
            img.image_order = (img.image_order or 0) + 1

        # Flush to persist the order changes before adding new image
        db.session.flush()

        # Process and save the new image with image_order=0 (primary)
        recipe_image = process_and_save_image(file, file.filename, folder="recipes")
        recipe_image.recipe_id = recipe.id
        recipe_image.image_order = 0

        db.session.add(recipe_image)
        db.session.commit()

        # Expire the images relationship to force reload with correct ordering
        db.session.expire(recipe, ["images"])

        # Log the final image orders
        current_app.logger.info(
            f"Recipe {recipe_id} images after upload: {[(img.id, img.image_order) for img in recipe.images]}"
        )

        current_app.logger.info(
            f"Primary image uploaded for recipe {recipe_id} by user {current_user.id}"
        )

        # Return the recipe with updated images
        is_admin = current_user.role.value == "admin" if current_user.role else False
        return (
            jsonify(
                {
                    "message": "Primary image uploaded successfully",
                    "image": recipe_image.to_dict(),
                    "recipe": recipe.to_dict(
                        current_user_id=current_user.id, is_admin=is_admin
                    ),
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Primary image upload failed for recipe {recipe_id}: {str(e)}\n{traceback.format_exc()}"
        )
        return jsonify({"error": "Primary image upload failed"}), 500


@bp.route("/images/<string:filename>", methods=["GET"])
@optional_auth  # Changed to optional_auth to allow public access
def serve_image(current_user, filename: str) -> Response:
    """Serve uploaded images (recipe and cookbook images)."""
    try:
        current_app.logger.debug(f"Serving image: {filename}")

        # Check if it's a recipe image
        recipe_image = RecipeImage.query.filter_by(filename=filename).first()
        if recipe_image:
            # Check if user can access the recipe associated with this image
            if recipe_image.recipe_id:
                recipe = Recipe.query.get(recipe_image.recipe_id)
                if not recipe:
                    return jsonify({"error": "Recipe not found"}), 404

                # Allow access if recipe is public OR if user is authenticated and owns the recipe
                if recipe.is_public:
                    # Public recipes are accessible to everyone
                    can_access = True
                elif current_user:
                    # Private recipes only accessible to owner or admin
                    can_access = recipe.user_id == current_user.id or (
                        hasattr(current_user, "role")
                        and current_user.role == UserRole.ADMIN
                    )
                else:
                    # Unauthenticated users can't access private recipes
                    can_access = False

                # Additional check: if this image is used as a recipe group cover
                # and the user owns the group, allow access
                if not can_access and current_user:
                    from app.models import RecipeGroup

                    group_using_image = RecipeGroup.query.filter(
                        RecipeGroup.cover_image_url.like(f"%{filename}%"),
                        RecipeGroup.user_id == current_user.id,
                    ).first()
                    if group_using_image:
                        can_access = True

                if not can_access:
                    return jsonify({"error": "Access denied"}), 403
            else:
                # Image doesn't have recipe_id yet (probably just uploaded, processing)
                # Allow access if user is authenticated (they likely just uploaded it)
                if not current_user:
                    return jsonify({"error": "Access denied"}), 403
                can_access = True

            # If image is stored in Cloudinary, redirect to Cloudinary URL
            if recipe_image.cloudinary_url:
                return redirect(recipe_image.cloudinary_url)
        else:
            # Check if it's a cookbook cover image
            cookbook = Cookbook.query.filter(
                Cookbook.cover_image_url.like(f"%{filename}")
            ).first()
            if cookbook:
                # Check if cookbook has public recipes (making it viewable publicly)
                has_public_recipes = (
                    Recipe.query.filter_by(
                        cookbook_id=cookbook.id, is_public=True
                    ).first()
                    is not None
                )

                if has_public_recipes:
                    # Cookbook with public recipes is accessible to everyone
                    can_access = True
                elif current_user:
                    # Private cookbooks only accessible to owner or admin
                    can_access = cookbook.user_id == current_user.id or (
                        hasattr(current_user, "role")
                        and current_user.role == UserRole.ADMIN
                    )
                else:
                    # Unauthenticated users can't access private cookbook images
                    can_access = False

                if not can_access:
                    return jsonify({"error": "Access denied"}), 403
            else:
                return jsonify({"error": "Image not found"}), 404

        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        file_path = upload_folder / filename

        # Security check - ensure file is within upload folder
        if not str(file_path.resolve()).startswith(str(upload_folder.resolve())):
            current_app.logger.error(f"Security check failed for file: {filename}")
            return jsonify({"error": "Invalid file path"}), 400

        if not file_path.exists():
            current_app.logger.error(f"File not found: {filename} at {file_path}")
            return jsonify({"error": "Image not found"}), 404

        return send_file(file_path)

    except Exception as e:
        current_app.logger.error(f"Error serving image {filename}: {str(e)}")
        return jsonify({"error": "Error serving image"}), 500

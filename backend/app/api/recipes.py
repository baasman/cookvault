import re
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

from flask import Response, current_app, jsonify, request, send_file
from sqlalchemy import select, text
from werkzeug.utils import secure_filename

from app import db
from app.api import bp
from app.api.auth import (
    require_auth,
    require_admin,
    optional_auth,
    should_apply_user_filter,
)
from app.utils.rate_limiting import rate_limit_upload
from app.models import (
    Cookbook,
    Ingredient,
    Instruction,
    MultiRecipeJob,
    ProcessingJob,
    ProcessingStatus,
    Recipe,
    RecipeComment,
    RecipeImage,
    RecipeNote,
    Tag,
    UserRecipeCollection,
    CopyrightConsent,
    UserRole,
)
from app.models.recipe import recipe_ingredients
from app.services.recipe_parser import RecipeParser
from app.services.cloudinary_service import cloudinary_service
import requests

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tiff"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_and_save_image(
    file, original_filename: str, folder: str = "recipes"
) -> RecipeImage:
    """
    Process and save an image file, using Cloudinary if enabled, otherwise local storage.

    Args:
        file: The uploaded file object
        original_filename: The original filename from the user
        folder: The Cloudinary folder to upload to (if using Cloudinary)

    Returns:
        RecipeImage: The created RecipeImage object
    """
    filename = secure_filename(f"{uuid.uuid4().hex}_{original_filename}")

    # Read file data for Cloudinary upload
    file.seek(0)
    file_data = file.read()
    file.seek(0)  # Reset for local save if needed

    recipe_image = RecipeImage(
        filename=filename,
        original_filename=original_filename,
        file_size=len(file_data),
        content_type=file.content_type or "image/jpeg",
    )

    # Try Cloudinary first if enabled
    if cloudinary_service.is_enabled():
        try:
            current_app.logger.info("Uploading image to Cloudinary...")
            cloudinary_result = cloudinary_service.upload_image(
                file_data, original_filename, folder=folder, generate_thumbnail=True
            )

            # Store Cloudinary information
            recipe_image.cloudinary_public_id = cloudinary_result["public_id"]
            recipe_image.cloudinary_url = cloudinary_result["url"]
            recipe_image.cloudinary_thumbnail_url = cloudinary_result.get(
                "thumbnail_url"
            )
            recipe_image.cloudinary_width = cloudinary_result["width"]
            recipe_image.cloudinary_height = cloudinary_result["height"]
            recipe_image.cloudinary_format = cloudinary_result["format"]
            recipe_image.cloudinary_bytes = cloudinary_result["bytes"]

            # For Cloudinary images, we don't need local file path
            recipe_image.file_path = f"cloudinary:{cloudinary_result['public_id']}"

            current_app.logger.info(
                f"Successfully uploaded to Cloudinary: {cloudinary_result['public_id']}"
            )

        except Exception as e:
            current_app.logger.error(
                f"Cloudinary upload failed, falling back to local storage: {str(e)}"
            )
            # Fall through to local storage

    # Local storage fallback (or primary if Cloudinary not enabled)
    if not recipe_image.cloudinary_public_id:
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        file_path = upload_folder / filename

        # Save file locally
        with open(file_path, "wb") as f:
            f.write(file_data)

        recipe_image.file_path = str(file_path)
        current_app.logger.info(f"Saved image locally: {file_path}")

    return recipe_image


def get_image_data_for_ocr(recipe_image: RecipeImage) -> bytes:
    """
    Get image data for OCR processing, handling both Cloudinary and local images.

    Args:
        recipe_image: RecipeImage object

    Returns:
        bytes: Image data

    Raises:
        Exception: If image cannot be retrieved
    """
    # Check if it's a Cloudinary image
    if recipe_image.file_path.startswith("cloudinary:"):
        if not recipe_image.cloudinary_url:
            raise Exception("Cloudinary image has no URL")

        current_app.logger.info(
            f"Downloading Cloudinary image for OCR: {recipe_image.cloudinary_url}"
        )

        try:
            response = requests.get(recipe_image.cloudinary_url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            current_app.logger.error(f"Failed to download Cloudinary image: {e}")
            raise Exception(f"Failed to download Cloudinary image: {str(e)}")

    # Local image
    else:
        image_path = Path(recipe_image.file_path)
        if not image_path.exists():
            raise Exception(f"Local image file not found: {image_path}")

        current_app.logger.info(f"Reading local image for OCR: {image_path}")
        return image_path.read_bytes()


def safe_int_conversion(value: Any) -> int | None:
    """Safely convert a value to an integer, handling ranges and extracting numbers from text"""
    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        value_str = value.strip()
        if not value_str:
            return None

        # Handle range values like "8-10", "4-6 servings", "2-3 hours", "2 to 4 servings"
        # Look for patterns like "8-10", "4-6", "2 to 4", etc.
        range_match = re.search(r"(\d+)\s*(?:[-–—]|to)\s*(\d+)", value_str)
        if range_match:
            start_val = int(range_match.group(1))
            end_val = int(range_match.group(2))
            # Take the average of the range, rounded down
            result = (start_val + end_val) // 2
            current_app.logger.info(
                f"Converted range '{value_str}' to {result} for servings field"
            )
            return result

        # Look for single numbers (ignoring text like "servings", "minutes", etc.)
        number_match = re.search(r"(\d+)", value_str)
        if number_match:
            result = int(number_match.group(1))
            current_app.logger.debug(
                f"Extracted number {result} from '{value_str}' for servings field"
            )
            return result

    try:
        return int(value)
    except (ValueError, TypeError):
        current_app.logger.warning(
            f"Could not convert '{value}' to integer for servings field"
        )
        return None


@bp.route("/ingredients/search", methods=["GET"])
def search_ingredients() -> Response:
    """Search for ingredients by name for autocomplete functionality."""
    try:
        query = request.args.get("q", "").strip()
        limit = request.args.get("limit", 10, type=int)

        if not query or len(query) < 2:
            return jsonify({"ingredients": []})

        # Limit the limit to prevent abuse
        limit = min(limit, 50)

        ingredients = (
            Ingredient.query.filter(Ingredient.name.ilike(f"%{query}%"))
            .order_by(Ingredient.name)
            .limit(limit)
            .all()
        )

        # Return unique ingredient names (since Ingredient table may have duplicates)
        seen_names = set()
        unique_ingredients = []
        for ing in ingredients:
            name_lower = ing.name.lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_ingredients.append({"id": ing.id, "name": ing.name})

        return jsonify({"ingredients": unique_ingredients})

    except Exception as e:
        current_app.logger.error(f"Error searching ingredients: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify(
            {"error": "Failed to search ingredients", "details": str(e)}
        ), 500


@bp.route("/recipes", methods=["GET"])
@require_auth
def get_recipes(current_user) -> Response:
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "")
    cookbook_id = request.args.get("cookbook_id", type=int)
    filter_type = request.args.get("filter", "collection")  # collection, discover, mine

    # Base query with privacy filtering
    query = Recipe.query.options(db.joinedload(Recipe.images))

    # Apply ownership and collection filtering based on user role and filter type
    if should_apply_user_filter(current_user):
        if filter_type == "mine":
            # Only recipes uploaded by this user (regardless of cookbook ownership)
            query = query.filter(Recipe.uploaded_by_id == current_user.id)
        elif filter_type == "collection":
            # Only recipes in user's collection (both own and added from others)
            # Include recipes that are either:
            # 1. Uploaded by the user
            # 2. Explicitly added to their collection via UserRecipeCollection
            user_recipe_ids_subquery = (
                db.session.query(UserRecipeCollection.recipe_id)
                .filter(UserRecipeCollection.user_id == current_user.id)
                .subquery()
            )

            query = query.filter(
                db.or_(
                    Recipe.uploaded_by_id == current_user.id,  # User's uploaded recipes
                    Recipe.id.in_(
                        user_recipe_ids_subquery
                    ),  # Explicitly collected recipes
                )
            )
        elif filter_type == "discover":
            # All public recipes from other users (for discovery)
            query = query.filter(
                Recipe.is_public,
                Recipe.uploaded_by_id
                != current_user.id,  # Exclude recipes uploaded by user
            )
            if search and search.strip():
                # Debug logging
                current_app.logger.info(
                    f"Discover mode search '{search}' for user {current_user.id}: looking for public recipes from other users"
                )
            else:
                # No search term - show all recent public recipes
                current_app.logger.info(
                    f"Discover mode (no search) for user {current_user.id}: showing recent public recipes from other users"
                )
        # No default case needed - collection is the default
    else:
        # Admins see all recipes, but can still use filters
        if filter_type == "mine":
            query = query.filter(Recipe.uploaded_by_id == current_user.id)
        elif filter_type == "collection":
            # For admins, collection filter shows all recipes (could be refined)
            pass  # No additional filter needed
        elif filter_type == "discover":
            # All public recipes (for discovery)
            query = query.filter(Recipe.is_public)
            if search and search.strip():
                current_app.logger.info(
                    f"Admin discover mode search '{search}': looking for public recipes"
                )
            else:
                current_app.logger.info(
                    "Admin discover mode (no search): showing all recent public recipes"
                )

    # Apply filters
    if cookbook_id:
        query = query.filter_by(cookbook_id=cookbook_id)

    # Course type filtering
    course_type = request.args.get("course_type", "").strip()
    if course_type:
        query = query.filter(Recipe.course_type == course_type)

    if search:
        query = query.filter(
            db.or_(
                Recipe.title.ilike(f"%{search}%"),
                Recipe.description.ilike(f"%{search}%"),
            )
        )

    # Ingredient filtering
    ingredients_param = request.args.get("ingredients", "").strip()
    ingredient_match = request.args.get("ingredient_match", "any")

    if ingredients_param:
        ingredient_names = [
            name.strip().lower()
            for name in ingredients_param.split(",")
            if name.strip()
        ]

        if ingredient_names:
            if ingredient_match == "all":
                # ALL mode: must have every ingredient
                for ingredient_name in ingredient_names:
                    subquery = (
                        db.session.query(recipe_ingredients.c.recipe_id)
                        .join(
                            Ingredient,
                            Ingredient.id == recipe_ingredients.c.ingredient_id,
                        )
                        .filter(Ingredient.name.ilike(f"%{ingredient_name}%"))
                        .subquery()
                    )
                    query = query.filter(Recipe.id.in_(subquery))
            else:
                # ANY mode: has at least one ingredient
                subquery = (
                    db.session.query(recipe_ingredients.c.recipe_id)
                    .join(
                        Ingredient, Ingredient.id == recipe_ingredients.c.ingredient_id
                    )
                    .filter(
                        db.or_(
                            *[
                                Ingredient.name.ilike(f"%{name}%")
                                for name in ingredient_names
                            ]
                        )
                    )
                    .distinct()
                    .subquery()
                )
                query = query.filter(Recipe.id.in_(subquery))

    # Order by creation date (newest first)
    query = query.order_by(Recipe.created_at.desc())

    recipes = query.paginate(page=page, per_page=per_page, error_out=False)

    # Debug logging - show what recipes are being returned
    if should_apply_user_filter(current_user):
        recipe_debug = [(r.id, r.title, r.user_id, r.is_public) for r in recipes.items]
        current_app.logger.info(
            f"Filter: {filter_type}, Search: '{search}', Returning {len(recipes.items)} recipes for user {current_user.id}: {recipe_debug}"
        )

        # If in discover mode and no results, let's check what public recipes exist
        if filter_type == "discover" and len(recipes.items) == 0 and search:
            all_public = Recipe.query.filter(Recipe.is_public).all()
            public_debug = [(r.id, r.title, r.user_id, r.is_public) for r in all_public]
            current_app.logger.info(f"All public recipes in database: {public_debug}")

    return jsonify(
        {
            "recipes": [
                recipe.to_dict(
                    include_user=True,
                    current_user_id=current_user.id,
                    is_admin=not should_apply_user_filter(current_user),
                )
                for recipe in recipes.items
            ],
            "total": recipes.total,
            "pages": recipes.pages,
            "current_page": page,
            "per_page": per_page,
            "has_next": recipes.has_next,
            "has_prev": recipes.has_prev,
        }
    )


@bp.route("/recipes", methods=["POST"])
@require_auth
def create_empty_recipe(current_user) -> Tuple[Response, int]:
    """Create a new empty recipe."""
    try:
        # Check upload limit for free users
        subscription = current_user.get_or_create_subscription()
        current_app.logger.info(
            f"Upload check for user {current_user.id} ({current_user.username}): "
            f"tier={subscription.tier.value}, status={subscription.status.value}, "
            f"monthly_uploads={subscription.monthly_upload_count}, "
            f"is_premium={subscription.is_premium()}, "
            f"can_upload={current_user.can_upload_recipe()}"
        )

        if not current_user.can_upload_recipe():
            current_app.logger.warning(
                f"User {current_user.id} ({current_user.username}) reached upload limit: "
                f"{subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
            )
            return jsonify(
                {
                    "error": "Upload limit reached",
                    "message": f"You've used all {subscription.monthly_upload_count} of your free uploads this month. Upgrade to Premium for unlimited uploads.",
                    "remaining_uploads": 0,
                    "monthly_upload_count": subscription.monthly_upload_count,
                    "is_premium": False,
                    "upgrade_required": True,
                }
            ), 403

        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        title = data.get("title", "").strip()
        if not title:
            return jsonify({"error": "Recipe title is required"}), 400

        cookbook_id = data.get("cookbook_id")

        # Validate cookbook access if cookbook_id is provided
        if cookbook_id:
            cookbook = Cookbook.query.get(cookbook_id)
            if not cookbook:
                return jsonify({"error": "Cookbook not found"}), 404
            # Allow access if: user owns the cookbook OR it's a global cookbook (Google Books)
            is_global_cookbook = cookbook.user_id is None
            is_own_cookbook = cookbook.user_id == current_user.id
            if not is_global_cookbook and not is_own_cookbook:
                return jsonify({"error": "Cookbook not found or access denied"}), 404

        # Create new recipe
        recipe = Recipe(
            title=title,
            user_id=current_user.id,
            uploaded_by_id=current_user.id,
            cookbook_id=cookbook_id,
            description="",
            prep_time=0,
            cook_time=0,
            servings=1,
            difficulty="",
            is_public=False,
        )

        db.session.add(recipe)
        db.session.commit()

        # Increment upload count for free users after successful upload
        if not current_user.is_premium():
            subscription = current_user.get_or_create_subscription()
            subscription.increment_upload_count()
            db.session.commit()
            current_app.logger.info(
                f"Upload count incremented for user {current_user.id}: {subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
            )

        current_app.logger.info(
            f"Created empty recipe {recipe.id} for user {current_user.id}"
        )

        return (
            jsonify(
                {"message": "Recipe created successfully", "recipe": recipe.to_dict()}
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating empty recipe: {str(e)}")
        return jsonify({"error": "Failed to create recipe"}), 500


@bp.route("/recipes/<int:recipe_id>", methods=["GET"])
@optional_auth
def get_recipe(current_user, recipe_id: int) -> Response:
    # Check if recipe exists and user can access it
    recipe = Recipe.query.options(db.joinedload(Recipe.images)).get(recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    # Check access permissions: owner, admin, or public recipe
    # current_user may be None for unauthenticated requests
    user_id = current_user.id if current_user else None
    is_admin = current_user and not should_apply_user_filter(current_user)
    can_view = recipe.can_be_viewed_by(user_id, is_admin)

    if not can_view:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    return jsonify(
        recipe.to_dict(include_user=True, current_user_id=user_id, is_admin=is_admin)
    )


@bp.route("/recipes/<int:recipe_id>", methods=["DELETE"])
@require_auth
def delete_recipe(current_user, recipe_id: int) -> Response:
    """Delete a recipe and all associated data."""
    try:
        # Get the recipe and verify ownership/permissions
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404

        # Check if user can delete this recipe (only owner, uploader, or admin)
        is_admin = not should_apply_user_filter(current_user)
        if (
            not is_admin
            and recipe.user_id != current_user.id
            and recipe.uploaded_by_id != current_user.id
        ):
            return jsonify({"error": "Access denied"}), 403

        current_app.logger.info(
            f"Deleting recipe {recipe_id} by user {current_user.id}"
        )

        # Delete associated images from Cloudinary and local storage
        for image in recipe.images:
            try:
                # Delete from Cloudinary if exists
                if image.cloudinary_public_id and cloudinary_service.is_enabled():
                    cloudinary_service.delete_image(image.cloudinary_public_id)
                    current_app.logger.info(
                        f"Deleted Cloudinary image: {image.cloudinary_public_id}"
                    )

                # Delete local file if exists
                if image.file_path:
                    file_path = Path(image.file_path)
                    if file_path.exists():
                        file_path.unlink()
                        current_app.logger.info(
                            f"Deleted local image file: {file_path}"
                        )

            except Exception as e:
                current_app.logger.error(f"Error deleting image {image.id}: {e}")
                # Continue with deletion even if image cleanup fails

        # Delete recipe (cascade will handle related data like ingredients, instructions, etc.)
        db.session.delete(recipe)
        db.session.commit()

        current_app.logger.info(f"Successfully deleted recipe {recipe_id}")
        return jsonify({"message": "Recipe deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to delete recipe"}), 500


@bp.route("/admin/recipes/<int:recipe_id>/feature", methods=["POST"])
@require_admin
def feature_recipe(current_user, recipe_id: int) -> Response:
    """Feature a recipe (admin only). Max 3 featured recipes allowed."""
    try:
        # Get the recipe
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404

        # Check if recipe is already featured
        if recipe.is_featured:
            return jsonify({"error": "Recipe is already featured"}), 400

        # Check featured recipe limit (max 3)
        featured_count = Recipe.query.filter_by(is_featured=True).count()
        if featured_count >= 3:
            # Find the oldest featured recipe and unfeature it
            oldest_featured = (
                Recipe.query.filter_by(is_featured=True)
                .order_by(Recipe.featured_at)
                .first()
            )
            if oldest_featured:
                oldest_featured.is_featured = False
                oldest_featured.featured_at = None
                current_app.logger.info(
                    f"Auto-unfeatured oldest recipe {oldest_featured.id} to make room"
                )

        # Feature the recipe
        recipe.is_featured = True
        recipe.featured_at = datetime.utcnow()
        db.session.commit()

        current_app.logger.info(
            f"Recipe {recipe_id} featured by admin {current_user.id}"
        )
        return jsonify(
            {"message": "Recipe featured successfully", "recipe": recipe.to_dict()}
        ), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error featuring recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to feature recipe"}), 500


@bp.route("/admin/recipes/<int:recipe_id>/feature", methods=["DELETE"])
@require_admin
def unfeature_recipe(current_user, recipe_id: int) -> Response:
    """Unfeature a recipe (admin only)."""
    try:
        # Get the recipe
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404

        # Check if recipe is featured
        if not recipe.is_featured:
            return jsonify({"error": "Recipe is not featured"}), 400

        # Unfeature the recipe
        recipe.is_featured = False
        recipe.featured_at = None
        db.session.commit()

        current_app.logger.info(
            f"Recipe {recipe_id} unfeatured by admin {current_user.id}"
        )
        return jsonify(
            {"message": "Recipe unfeatured successfully", "recipe": recipe.to_dict()}
        ), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error unfeaturing recipe {recipe_id}: {e}")
        return jsonify({"error": "Failed to unfeature recipe"}), 500


@bp.route("/recipes/upload", methods=["POST"])
@require_auth
@rate_limit_upload
def upload_recipe(current_user) -> Tuple[Response, int]:
    """Upload a recipe image and process it into a recipe."""
    current_app.logger.info(f"Recipe upload from user {current_user.id}")

    # Check for cache bypass header (used during load testing)
    skip_cache = request.headers.get("X-Skip-Cache", "").lower() == "true"
    if skip_cache:
        current_app.logger.info("Cache bypass enabled via X-Skip-Cache header")

    # Check upload limit for free users
    subscription = current_user.get_or_create_subscription()
    current_app.logger.info(
        f"Upload check for user {current_user.id} ({current_user.username}): "
        f"tier={subscription.tier.value}, status={subscription.status.value}, "
        f"monthly_uploads={subscription.monthly_upload_count}, "
        f"is_premium={subscription.is_premium()}, "
        f"can_upload={current_user.can_upload_recipe()}"
    )

    if not current_user.can_upload_recipe():
        current_app.logger.warning(
            f"User {current_user.id} ({current_user.username}) reached upload limit: "
            f"{subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
        )
        return jsonify(
            {
                "error": "Upload limit reached",
                "message": f"You've used all {subscription.monthly_upload_count} of your free uploads this month. Upgrade to Premium for unlimited uploads.",
                "remaining_uploads": 0,
                "monthly_upload_count": subscription.monthly_upload_count,
                "is_premium": False,
                "upgrade_required": True,
            }
        ), 403

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    # Check file size to prevent memory issues (limit to 8MB for optimal memory usage)
    file.seek(0, 2)  # Seek to end of file
    file_size = file.tell()
    file.seek(0)  # Reset file pointer
    file_size_mb = file_size / (1024 * 1024)

    max_upload_size = current_app.config.get("MAX_UPLOAD_SIZE", 8)  # Default 8MB
    if file_size_mb > max_upload_size:
        return (
            jsonify(
                {
                    "error": f"File too large ({file_size_mb:.1f}MB). Please use files smaller than {max_upload_size}MB."
                }
            ),
            400,
        )

    current_app.logger.info(f"Uploading file: {file.filename} ({file_size_mb:.1f}MB)")

    # Get cookbook information from form data
    cookbook_id = request.form.get("cookbook_id")
    create_new_cookbook = request.form.get("create_new_cookbook") == "true"

    # Get recipe source information (is_original_recipe)
    is_original_recipe_str = request.form.get("is_original_recipe")
    is_original_recipe = None
    if is_original_recipe_str is not None:
        is_original_recipe = is_original_recipe_str.lower() == "true"

    # Get translation option
    translate_to_english = (
        request.form.get("translate_to_english", "").lower() == "true"
    )

    # Handle new cookbook creation
    cookbook = None
    if create_new_cookbook:
        # Validate required fields for new cookbook
        new_cookbook_title = request.form.get("new_cookbook_title", "").strip()
        if not new_cookbook_title:
            return (
                jsonify(
                    {"error": "Cookbook title is required when creating a new cookbook"}
                ),
                400,
            )

        # Create new cookbook
        try:
            from datetime import datetime

            cookbook = Cookbook(
                title=new_cookbook_title,
                author=request.form.get("new_cookbook_author", "").strip() or None,
                description=request.form.get("new_cookbook_description", "").strip()
                or None,
                publisher=request.form.get("new_cookbook_publisher", "").strip()
                or None,
                isbn=request.form.get("new_cookbook_isbn", "").strip() or None,
                user_id=current_user.id,
            )

            # Handle publication date if provided
            publication_date = request.form.get(
                "new_cookbook_publication_date", ""
            ).strip()
            if publication_date:
                try:
                    cookbook.publication_date = datetime.fromisoformat(publication_date)
                except ValueError:
                    return jsonify({"error": "Invalid publication date format"}), 400

            db.session.add(cookbook)
            db.session.flush()  # Get the cookbook ID
            cookbook_id = cookbook.id

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Cookbook creation failed: {str(e)}")
            return jsonify({"error": "Failed to create cookbook"}), 500

    elif cookbook_id:
        # Validate existing cookbook_id
        try:
            cookbook_id = int(cookbook_id)
            cookbook = Cookbook.query.get(cookbook_id)
            if not cookbook:
                return jsonify({"error": "Cookbook not found"}), 400
            # Note: We allow adding recipes to any existing cookbook for sharing

            # If cookbook is from Google Books, force is_original_recipe = False
            # (recipes from published cookbooks cannot be made public)
            if cookbook.google_books_id:
                is_original_recipe = False
        except ValueError:
            return jsonify({"error": "Invalid cookbook_id"}), 400

    try:
        # Use the new helper function to handle image processing
        recipe_image = process_and_save_image(file, file.filename, folder="recipes")

        db.session.add(recipe_image)
        db.session.flush()

        processing_job = ProcessingJob(
            image_id=recipe_image.id,
            cookbook_id=cookbook_id,
            user_id=current_user.id,
            skip_cache=skip_cache,
            is_original_recipe=is_original_recipe,
            translate_to_english=translate_to_english,
        )

        db.session.add(processing_job)
        db.session.commit()

        # Increment upload count for free users after successful upload
        if not current_user.is_premium():
            subscription = current_user.get_or_create_subscription()
            subscription.increment_upload_count()
            db.session.commit()
            current_app.logger.info(
                f"Upload count incremented for user {current_user.id}: {subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
            )

        # Queue background processing via Celery task queue
        # This ensures sequential processing to prevent memory spikes
        from app.tasks.recipe_tasks import process_single_recipe_task

        current_app.logger.info(f"Queuing Celery task for job {processing_job.id}")

        # Dispatch the task to Celery worker
        process_single_recipe_task.delay(processing_job.id, current_user.id)

        return (
            jsonify(
                {
                    "message": "Image uploaded successfully. Recipe extraction is processing in the background.",
                    "job_id": processing_job.id,
                    "image_id": recipe_image.id,
                    "image": recipe_image.to_dict(),  # Include image data for immediate preview
                    "cookbook": cookbook.to_dict() if cookbook else None,
                    "status": "processing",
                    "processing_info": "Your recipe is being extracted and parsed. Check back in a few moments.",
                    "status_url": f"/api/recipes/job-status/{processing_job.id}",
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Upload failed: {str(e)}")
        # Force garbage collection on error to clean up any allocated memory
        import gc

        gc.collect()
        return jsonify({"error": "Upload failed"}), 500
    finally:
        # Always force garbage collection at the end of upload to free memory
        import gc

        gc.collect()


@bp.route("/recipes/<int:recipe_id>", methods=["PUT"])
@require_auth
def update_recipe(current_user, recipe_id: int) -> Response:
    """Update recipe metadata (title, description, timing, etc.)."""

    # Verify recipe exists and user has permission (owner or uploader)
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter(
            Recipe.id == recipe_id,
            db.or_(
                Recipe.user_id == current_user.id,
                Recipe.uploaded_by_id == current_user.id,
            ),
        ).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Update allowed fields
        if "title" in data:
            if not data["title"].strip():
                return jsonify({"error": "Title cannot be empty"}), 400
            recipe.title = data["title"].strip()

        if "description" in data:
            recipe.description = (
                data["description"].strip() if data["description"] else None
            )

        if "prep_time" in data:
            recipe.prep_time = (
                safe_int_conversion(data["prep_time"]) if data["prep_time"] else None
            )

        if "cook_time" in data:
            recipe.cook_time = (
                safe_int_conversion(data["cook_time"]) if data["cook_time"] else None
            )

        if "servings" in data:
            recipe.servings = (
                safe_int_conversion(data["servings"]) if data["servings"] else None
            )

        if "difficulty" in data:
            recipe.difficulty = data["difficulty"] if data["difficulty"] else None

        db.session.commit()
        current_app.logger.info(f"Recipe {recipe_id} updated by user {current_user.id}")

        is_admin = current_user.role.value == "admin" if current_user.role else False
        return jsonify(
            {
                "message": "Recipe updated successfully",
                "recipe": recipe.to_dict(
                    current_user_id=current_user.id, is_admin=is_admin
                ),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Recipe update failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Recipe update failed"}), 500


@bp.route("/recipes/<int:recipe_id>/cookbook", methods=["PUT"])
@require_auth
def link_recipe_to_cookbook(current_user, recipe_id: int) -> Response:
    """Link an existing recipe to a cookbook."""

    # Verify recipe exists and user has permission
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        cookbook_id = data.get("cookbook_id")

        # Allow unlinking from cookbook by setting cookbook_id to null
        if cookbook_id is not None:
            # Get the cookbook first
            cookbook = Cookbook.query.get(cookbook_id)
            if not cookbook:
                return jsonify({"error": "Cookbook not found"}), 404

            # Permission check: allow if any of these conditions are met:
            # 1. Admin user (no restrictions)
            # 2. Global cookbook (user_id=NULL) - any authenticated user can add recipes
            # 3. User-owned cookbook - user must be the owner
            is_global_cookbook = cookbook.user_id is None
            is_own_cookbook = cookbook.user_id == current_user.id

            if should_apply_user_filter(current_user):
                if not is_global_cookbook and not is_own_cookbook:
                    return jsonify(
                        {"error": "Cookbook not found or access denied"}
                    ), 404

        # Update recipe's cookbook association
        recipe.cookbook_id = cookbook_id

        db.session.commit()
        current_app.logger.info(
            f"Recipe {recipe_id} {'linked to' if cookbook_id else 'unlinked from'} cookbook {cookbook_id} by user {current_user.id}"
        )

        is_admin = current_user.role.value == "admin" if current_user.role else False
        return jsonify(
            {
                "message": "Recipe cookbook updated successfully",
                "recipe": recipe.to_dict(
                    current_user_id=current_user.id, is_admin=is_admin
                ),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to link recipe {recipe_id} to cookbook: {str(e)}"
        )
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Failed to update recipe cookbook"}), 500


@bp.route("/recipes/<int:recipe_id>/ingredients", methods=["PUT"])
@require_auth
def update_recipe_ingredients(current_user, recipe_id: int) -> Response:
    """Update recipe ingredients list."""

    # Verify recipe exists and user has permission (owner or uploader)
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter(
            Recipe.id == recipe_id,
            db.or_(
                Recipe.user_id == current_user.id,
                Recipe.uploaded_by_id == current_user.id,
            ),
        ).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    try:
        data = request.get_json()
        if not data or "ingredients" not in data:
            return jsonify({"error": "No ingredients data provided"}), 400

        ingredients_data = data["ingredients"]
        if not isinstance(ingredients_data, list):
            return jsonify({"error": "Ingredients must be a list"}), 400

        # Remove existing recipe-ingredient associations
        db.session.execute(
            recipe_ingredients.delete().where(
                recipe_ingredients.c.recipe_id == recipe_id
            )
        )

        # Add new ingredients
        for order, ingredient_data in enumerate(ingredients_data, 1):
            if not isinstance(ingredient_data, dict):
                return jsonify({"error": "Invalid ingredient data"}), 400

            ingredient_name = ingredient_data.get("name", "").strip()
            if not ingredient_name:
                return jsonify({"error": "Ingredient name is required"}), 400

            # Find or create ingredient
            ingredient = Ingredient.query.filter_by(name=ingredient_name).first()
            if not ingredient:
                ingredient = Ingredient(
                    name=ingredient_name, category=ingredient_data.get("category")
                )
                db.session.add(ingredient)
                db.session.flush()

            # Create recipe-ingredient association
            db.session.execute(
                recipe_ingredients.insert().values(
                    recipe_id=recipe_id,
                    ingredient_id=ingredient.id,
                    quantity=ingredient_data.get("quantity"),
                    unit=ingredient_data.get("unit"),
                    preparation=ingredient_data.get("preparation"),
                    optional=ingredient_data.get("optional", False),
                    order=order,
                )
            )

        db.session.commit()
        current_app.logger.info(
            f"Ingredients updated for recipe {recipe_id} by user {current_user.id}"
        )

        is_admin = current_user.role.value == "admin" if current_user.role else False
        return jsonify(
            {
                "message": "Ingredients updated successfully",
                "recipe": recipe.to_dict(
                    current_user_id=current_user.id, is_admin=is_admin
                ),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Ingredients update failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Ingredients update failed"}), 500


@bp.route("/recipes/<int:recipe_id>/instructions", methods=["PUT"])
@require_auth
def update_recipe_instructions(current_user, recipe_id: int) -> Response:
    """Update recipe instructions list."""

    # Verify recipe exists and user has permission (owner or uploader)
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter(
            Recipe.id == recipe_id,
            db.or_(
                Recipe.user_id == current_user.id,
                Recipe.uploaded_by_id == current_user.id,
            ),
        ).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    try:
        data = request.get_json()
        if not data or "instructions" not in data:
            return jsonify({"error": "No instructions data provided"}), 400

        instructions_data = data["instructions"]
        if not isinstance(instructions_data, list):
            return jsonify({"error": "Instructions must be a list"}), 400

        # Get existing instructions to preserve their IDs and image data
        existing_instructions = (
            Instruction.query.filter_by(recipe_id=recipe_id)
            .order_by(Instruction.step_number)
            .all()
        )

        # Create a mapping of current instructions for efficient lookup
        existing_by_step = {inst.step_number: inst for inst in existing_instructions}

        # Update or create instructions while preserving image data
        updated_instructions = []
        for step_number, instruction_text in enumerate(instructions_data, 1):
            if not isinstance(instruction_text, str):
                return jsonify({"error": "Invalid instruction data"}), 400

            instruction_text = instruction_text.strip()
            if not instruction_text:
                return jsonify({"error": "Instruction text cannot be empty"}), 400

            # Check if instruction exists at this step number
            if step_number in existing_by_step:
                # Update existing instruction (preserves ID and image data)
                instruction = existing_by_step[step_number]
                instruction.text = instruction_text
                instruction.step_number = step_number
            else:
                # Create new instruction
                instruction = Instruction(
                    recipe_id=recipe_id, step_number=step_number, text=instruction_text
                )
                db.session.add(instruction)

            updated_instructions.append(instruction)

        # Remove any instructions that are no longer needed (step numbers beyond the new list)
        for step_number in existing_by_step:
            if step_number > len(instructions_data):
                db.session.delete(existing_by_step[step_number])

        db.session.commit()
        current_app.logger.info(
            f"Instructions updated for recipe {recipe_id} by user {current_user.id}"
        )

        is_admin = current_user.role.value == "admin" if current_user.role else False
        return jsonify(
            {
                "message": "Instructions updated successfully",
                "recipe": recipe.to_dict(
                    current_user_id=current_user.id, is_admin=is_admin
                ),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Instructions update failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Instructions update failed"}), 500


@bp.route("/recipes/<int:recipe_id>/tags", methods=["PUT"])
@require_auth
def update_recipe_tags(current_user, recipe_id: int) -> Response:
    """Update recipe tags list."""

    # Verify recipe exists and user has permission (owner or uploader)
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter(
            Recipe.id == recipe_id,
            db.or_(
                Recipe.user_id == current_user.id,
                Recipe.uploaded_by_id == current_user.id,
            ),
        ).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    try:
        data = request.get_json()
        if not data or "tags" not in data:
            return jsonify({"error": "No tags data provided"}), 400

        tags_data = data["tags"]
        if not isinstance(tags_data, list):
            return jsonify({"error": "Tags must be a list"}), 400

        # Remove existing tags
        Tag.query.filter_by(recipe_id=recipe_id).delete()

        # Add new tags
        for tag_name in tags_data:
            if not isinstance(tag_name, str):
                return jsonify({"error": "Invalid tag data"}), 400

            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag(recipe_id=recipe_id, name=tag_name)
                db.session.add(tag)

        db.session.commit()
        current_app.logger.info(
            f"Tags updated for recipe {recipe_id} by user {current_user.id}"
        )

        is_admin = current_user.role.value == "admin" if current_user.role else False
        return jsonify(
            {
                "message": "Tags updated successfully",
                "recipe": recipe.to_dict(
                    current_user_id=current_user.id, is_admin=is_admin
                ),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Tags update failed for recipe {recipe_id}: {str(e)}")
        return jsonify({"error": "Tags update failed"}), 500


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


@bp.route("/jobs/<int:job_id>", methods=["GET"])
@require_auth
def get_processing_job(current_user, job_id: int):
    job = ProcessingJob.query.get_or_404(job_id)
    # Verify job belongs to user (through cookbook ownership or direct ownership)
    if job.cookbook_id:
        cookbook = Cookbook.query.get(job.cookbook_id)
        if not cookbook:
            return jsonify({"error": "Job not found"}), 404
        # Allow access if: user owns cookbook OR it's a global cookbook (Google Books)
        is_global = cookbook.user_id is None
        is_owner = cookbook.user_id == current_user.id
        if not is_global and not is_owner:
            return jsonify({"error": "Job not found"}), 404

    return jsonify(job.to_dict())


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
                from flask import redirect

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


def _process_recipe_image(job_id: int, user_id: int = None) -> None:
    """Main function to process a recipe image through OCR and parsing."""
    job = ProcessingJob.query.get(job_id)
    if not job:
        return

    try:
        job.status = ProcessingStatus.PROCESSING
        db.session.commit()

        # Use single-pass LLM processing (extract + parse in one call for memory efficiency)
        recipe_image = RecipeImage.query.get(job.image_id)
        if not recipe_image:
            raise Exception("Recipe image not found")

        from app.services.llm_ocr_service import LLMOCRService

        llm_ocr_service = LLMOCRService()

        # Get image data (handles both Cloudinary and local images)
        try:
            image_data = get_image_data_for_ocr(recipe_image)
            source_info = f"job_{job.id}_image_{recipe_image.id}"
        except Exception as e:
            current_app.logger.error(f"Failed to get image data for OCR: {e}")
            raise

        current_app.logger.info(
            f"Starting single-pass extract+parse for image {job.image_id}"
        )

        # Check if caching should be bypassed (for load testing)
        use_cache = not getattr(job, "skip_cache", False)
        if not use_cache:
            current_app.logger.info("Cache bypass enabled for this job")

        # Single LLM call for both extraction and parsing - with timeout monitoring
        import time

        start_time = time.time()

        try:
            # Get translate option from job
            translate_to_english = getattr(job, "translate_to_english", False)
            comprehensive_result = llm_ocr_service.extract_and_parse_recipe(
                image_data,
                source_info,
                use_cache=use_cache,
                translate_to_english=translate_to_english,
            )
            processing_time = time.time() - start_time
            current_app.logger.info(
                f"LLM processing completed in {processing_time:.1f}s"
            )
        except Exception as e:
            processing_time = time.time() - start_time
            current_app.logger.error(
                f"LLM processing failed after {processing_time:.1f}s: {str(e)}"
            )
            raise

        extracted_text = comprehensive_result["text"]

        if comprehensive_result["success"] and comprehensive_result["parsed_recipe"]:
            # Use the parsed recipe from LLM
            parsed_recipe = comprehensive_result["parsed_recipe"]
            current_app.logger.info("Using LLM-parsed recipe data")
            current_app.logger.debug(
                f"LLM parsed recipe keys: {list(parsed_recipe.keys())}"
            )
            current_app.logger.debug(
                f"Number of ingredients: {len(parsed_recipe.get('ingredients', []))}"
            )
            current_app.logger.debug(
                f"Number of instructions: {len(parsed_recipe.get('instructions', []))}"
            )
        else:
            # Fallback to traditional parsing if LLM parsing failed
            current_app.logger.warning(
                "LLM parsing failed, falling back to traditional parsing"
            )
            current_app.logger.debug(
                f"LLM error: {comprehensive_result.get('error', 'Unknown error')}"
            )
            parsed_recipe = _parse_extracted_text(extracted_text)

        # Force garbage collection after LLM processing to free memory
        import gc

        gc.collect()

        # Create recipe and related records
        recipe = _create_recipe_from_parsed_data(
            parsed_recipe, extracted_text, job, user_id
        )

        # Associate recipe with job and image
        _associate_recipe_with_job(job, recipe)

        # Automatically add user's own recipe to their collection
        if recipe.user_id:
            collection_item = UserRecipeCollection(
                user_id=recipe.user_id, recipe_id=recipe.id
            )
            db.session.add(collection_item)

        job.status = ProcessingStatus.COMPLETED
        db.session.commit()

    except Exception as e:
        current_app.logger.error(
            f"Processing failed for job {job_id}: {str(e)}", exc_info=True
        )

        # Handle database session rollback properly
        try:
            db.session.rollback()
            current_app.logger.info("Database session rolled back successfully")

            # Re-fetch the job in a clean session to update status
            job = ProcessingJob.query.get(job_id)
            if job:
                job.status = ProcessingStatus.FAILED
                job.error_message = str(e)[:500]  # Limit error message length
                db.session.commit()
                current_app.logger.info(f"Job {job_id} status updated to FAILED")
            else:
                current_app.logger.error(
                    f"Could not find job {job_id} to update status"
                )

        except Exception as rollback_error:
            current_app.logger.error(
                f"Failed to rollback and update job status: {str(rollback_error)}",
                exc_info=True,
            )
            # As a last resort, try to create a new session
            try:
                from app import db as fresh_db

                fresh_db.session.rollback()
                fresh_db.session.close()
                current_app.logger.info(
                    "Created fresh database session after rollback failure"
                )
            except Exception as fresh_error:
                current_app.logger.critical(
                    f"Complete database session failure: {str(fresh_error)}"
                )


def _extract_text_from_image(image_id: int) -> str:
    """Extract text from recipe image using LLM-only OCR (eliminates pytesseract for memory efficiency)."""
    recipe_image = RecipeImage.query.get(image_id)
    if not recipe_image:
        raise Exception("Recipe image not found")

    # Use LLM-only extraction for better quality and lower memory usage
    from app.services.llm_ocr_service import LLMOCRService

    llm_ocr_service = LLMOCRService()

    # Get image data (handles both Cloudinary and local images)
    try:
        image_data = get_image_data_for_ocr(recipe_image)
        source_info = f"image_{recipe_image.id}"
    except Exception as e:
        current_app.logger.error(f"Failed to get image data for OCR: {e}")
        raise

    current_app.logger.info(f"Starting LLM-only OCR extraction for image {image_id}")

    # Direct LLM extraction (bypasses traditional OCR completely)
    extracted_text = llm_ocr_service.extract_text_from_image(image_data, source_info)

    # Create extraction result in same format for compatibility
    extraction_result = {
        "text": extracted_text,
        "method": "llm_only",
        "quality_score": 10,  # LLM extraction is always high quality
        "fallback_used": False,
        "quality_reasoning": "LLM-only extraction for optimal memory efficiency",
    }

    # Log extraction details for monitoring
    current_app.logger.info(
        f"OCR extraction completed for image {image_id}: "
        f"method={extraction_result['method']}, "
        f"quality_score={extraction_result.get('quality_score', 'N/A')}, "
        f"fallback_used={extraction_result['fallback_used']}"
    )

    # Update processing job with OCR metadata if available
    try:
        # Find the processing job for this image
        job = ProcessingJob.query.filter_by(image_id=image_id).first()
        if job:
            # Store OCR metadata for analytics
            job.ocr_method = extraction_result["method"]
            job.ocr_quality_score = extraction_result.get("quality_score")
            job.ocr_fallback_used = extraction_result["fallback_used"]
            db.session.commit()
    except Exception as e:
        current_app.logger.warning(f"Failed to update OCR metadata: {str(e)}")

    return extraction_result["text"]


def _parse_extracted_text(extracted_text: str) -> Dict[str, Any]:
    """Parse extracted text into structured recipe data."""
    recipe_parser = RecipeParser()
    return recipe_parser.parse_recipe_text(extracted_text)


def _generate_recipe_title(
    parsed_recipe: Dict[str, Any], extracted_text: str, job: ProcessingJob
) -> str:
    """Generate a robust title with smart fallbacks to ensure never null."""
    # Try to get title from parsed recipe
    title = parsed_recipe.get("title")
    if title and title.strip():
        current_app.logger.info(f"Using parsed title: {title}")
        return title.strip()

    # Fallback 1: Extract first line/sentence from extracted text
    if extracted_text and extracted_text.strip():
        lines = [line.strip() for line in extracted_text.split("\n") if line.strip()]
        if lines:
            # Take first non-empty line, limit to reasonable title length
            first_line = lines[0][:100]  # Limit to 100 characters
            current_app.logger.warning(
                f"Title was null, using first line as fallback: {first_line}"
            )
            return first_line

    # Fallback 2: Try to get filename from job's associated image
    try:
        if job and job.images:
            image = job.images[0]  # Get first image
            filename = image.original_filename
            if filename:
                # Remove extension and create readable title
                name_without_ext = filename.rsplit(".", 1)[0]
                title = f"Recipe from {name_without_ext}"
                current_app.logger.warning(f"Using filename-based fallback: {title}")
                return title
    except (AttributeError, IndexError):
        pass

    # Fallback 3: Use timestamp-based title
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"Recipe from {timestamp}"
    current_app.logger.error(
        f"All title extraction failed, using timestamp fallback: {title}"
    )
    return title


def _create_recipe_from_parsed_data(
    parsed_recipe: Dict[str, Any],
    extracted_text: str,
    job: ProcessingJob,
    upload_user_id: int = None,
) -> Recipe:
    """Create recipe and all related records from parsed data."""
    # The uploader is always the upload_user_id (tracks who actually uploaded)
    uploaded_by_id = upload_user_id

    # Get user_id from cookbook if it exists, otherwise use the upload user_id
    # user_id = cookbook owner (for shared cookbooks) or uploader (for own cookbooks)
    user_id = upload_user_id  # Default to the user who uploaded the image
    if job.cookbook_id:
        cookbook = Cookbook.query.get(job.cookbook_id)
        # Only use cookbook.user_id if it's not None (i.e., not a global cookbook)
        if cookbook and cookbook.user_id is not None:
            user_id = cookbook.user_id

    # Generate robust title with smart fallbacks
    title = _generate_recipe_title(parsed_recipe, extracted_text, job)

    # Extract translation metadata
    is_translated = parsed_recipe.get("is_translated", False)
    source_language = parsed_recipe.get("source_language")
    source_language_name = parsed_recipe.get("source_language_name")
    original_title = parsed_recipe.get("original_title") if is_translated else None
    original_description = (
        parsed_recipe.get("original_description") if is_translated else None
    )

    # Update job with detected language
    if source_language:
        job.detected_language = source_language
        job.detected_language_name = source_language_name

    # Create base recipe
    recipe = Recipe(
        title=title,
        description=parsed_recipe.get("description"),
        cookbook_id=job.cookbook_id,
        prep_time=safe_int_conversion(parsed_recipe.get("prep_time")),
        cook_time=safe_int_conversion(parsed_recipe.get("cook_time")),
        servings=safe_int_conversion(parsed_recipe.get("servings")),
        difficulty=parsed_recipe.get("difficulty"),
        course_type=parsed_recipe.get("course_type"),
        user_id=user_id,
        uploaded_by_id=uploaded_by_id,  # Track the actual uploader
        is_public=False,  # New recipes are private by default
        is_original_recipe=job.is_original_recipe,  # Track recipe source for copyright protection
        # Translation fields
        source_language=source_language,
        source_language_name=source_language_name,
        is_translated=is_translated,
        original_title=original_title,
        original_description=original_description,
    )

    db.session.add(recipe)
    db.session.flush()

    # Create related records (pass original instructions for translation support)
    original_instructions = (
        parsed_recipe.get("original_instructions") if is_translated else None
    )
    _create_instructions(
        recipe.id, parsed_recipe, extracted_text, original_instructions
    )
    _create_tags(recipe.id, parsed_recipe)
    _create_ingredients(recipe.id, parsed_recipe)

    return recipe


def _create_instructions(
    recipe_id: int,
    parsed_recipe: Dict[str, Any],
    fallback_text: str,
    original_instructions: list = None,
) -> None:
    """Create instruction records for the recipe, with optional original text for translations."""
    instructions = parsed_recipe.get("instructions", [])
    if isinstance(instructions, str):
        instructions = [instructions]
    elif not isinstance(instructions, list):
        instructions = [fallback_text]

    # Ensure original_instructions is a list if provided
    if original_instructions and not isinstance(original_instructions, list):
        original_instructions = None

    for i, instruction_text in enumerate(instructions, 1):
        # Get corresponding original text if available
        original_text = None
        if original_instructions and i <= len(original_instructions):
            original_text = original_instructions[i - 1]
            if isinstance(original_text, str):
                original_text = original_text.strip()

        instruction = Instruction(
            recipe_id=recipe_id,
            step_number=i,
            text=instruction_text.strip(),
            original_text=original_text,
        )
        db.session.add(instruction)


def _create_tags(recipe_id: int, parsed_recipe: Dict[str, Any]) -> None:
    """Create tag records for the recipe."""
    tags = parsed_recipe.get("tags", [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",")]
    elif not isinstance(tags, list):
        tags = []

    for tag_name in tags:
        if tag_name.strip():
            tag = Tag(recipe_id=recipe_id, name=tag_name.strip())
            db.session.add(tag)


def _create_ingredients(recipe_id: int, parsed_recipe: Dict[str, Any]) -> None:
    """Create ingredient records and associations for the recipe."""

    ingredients = parsed_recipe.get("ingredients", [])
    if isinstance(ingredients, str):
        ingredients = [ingredients]
    elif not isinstance(ingredients, list):
        ingredients = []

    current_app.logger.info(
        f"Creating {len(ingredients)} ingredients for recipe {recipe_id}"
    )
    current_app.logger.debug(f"Ingredients data: {ingredients}")

    for order, ingredient_data in enumerate(ingredients, 1):
        # Use a savepoint to allow rolling back individual ingredient failures
        savepoint = db.session.begin_nested()
        try:
            # Handle both old format (strings) and new LLM format (objects)
            if isinstance(ingredient_data, str):
                # Old format: ingredient as string
                if ingredient_data.strip():
                    parsed_ingredient = _parse_ingredient_text(ingredient_data.strip())
                    ingredient = _find_or_create_ingredient(parsed_ingredient)
                    _create_recipe_ingredient_association(
                        recipe_id, ingredient.id, parsed_ingredient, order
                    )
            elif isinstance(ingredient_data, dict):
                # New LLM format: ingredient as structured object
                ingredient_name = ingredient_data.get("name", "").strip()
                if ingredient_name:
                    # Create parsed ingredient from LLM structure
                    parsed_ingredient = {
                        "name": ingredient_name,
                        "quantity": ingredient_data.get("quantity"),
                        "unit": ingredient_data.get("unit"),
                        "preparation": ingredient_data.get("preparation"),
                        "optional": bool(ingredient_data.get("optional", False)),
                        "category": None,  # Can be added later if needed
                    }

                    current_app.logger.debug(
                        f"Processing LLM ingredient: {parsed_ingredient}"
                    )

                    ingredient = _find_or_create_ingredient(parsed_ingredient)
                    _create_recipe_ingredient_association(
                        recipe_id, ingredient.id, parsed_ingredient, order
                    )
            else:
                current_app.logger.warning(
                    f"Unknown ingredient format: {type(ingredient_data)} - {ingredient_data}"
                )

            # Commit the savepoint if successful
            savepoint.commit()

        except Exception as e:
            # Rollback this ingredient's changes but continue with others
            savepoint.rollback()
            current_app.logger.error(
                f"Failed to create ingredient {order}: {str(e)}", exc_info=True
            )
            # Continue with other ingredients rather than failing completely


def _find_or_create_ingredient(parsed_ingredient: Dict[str, Any]) -> Ingredient:
    """Find existing ingredient or create new one."""
    ingredient = Ingredient.query.filter_by(name=parsed_ingredient["name"]).first()
    if not ingredient:
        ingredient = Ingredient(
            name=parsed_ingredient["name"], category=parsed_ingredient.get("category")
        )
        db.session.add(ingredient)
        db.session.flush()
    return ingredient


def _create_recipe_ingredient_association(
    recipe_id: int, ingredient_id: int, parsed_ingredient: Dict[str, Any], order: int
) -> None:
    """Create association between recipe and ingredient with quantities."""
    # Check if association already exists (prevents duplicate constraint errors)
    existing = db.session.execute(
        select(recipe_ingredients).where(
            recipe_ingredients.c.recipe_id == recipe_id,
            recipe_ingredients.c.ingredient_id == ingredient_id,
        )
    ).first()

    if existing:
        # Already exists, skip insertion
        return

    # Insert into the association table using ORM
    stmt = recipe_ingredients.insert().values(
        recipe_id=recipe_id,
        ingredient_id=ingredient_id,
        quantity=parsed_ingredient.get("quantity"),
        unit=parsed_ingredient.get("unit"),
        preparation=parsed_ingredient.get("preparation"),
        optional=parsed_ingredient.get("optional", False),
        order=order,
    )
    db.session.execute(stmt)


def _associate_recipe_with_job(job: ProcessingJob, recipe: Recipe) -> None:
    """Associate the created recipe with the processing job and image."""
    job.recipe_id = recipe.id
    recipe_image = RecipeImage.query.get(job.image_id)
    if recipe_image:
        recipe_image.recipe_id = recipe.id


def _parse_ingredient_text(ingredient_text: str) -> Dict[str, Any]:
    """Parse ingredient text to extract name, quantity, unit, and preparation."""
    import re

    # Common units pattern
    units = r"\b(?:cups?|cup|tbsp|tsp|teaspoons?|tablespoons?|oz|ounces?|lbs?|pounds?|g|grams?|kg|kilograms?|ml|milliliters?|l|liters?|pint|pints|quart|quarts|gallon|gallons|inch|inches|cloves?|pieces?|slices?|whole|medium|large|small)\b"

    # Pattern to match quantity + unit + ingredient
    pattern = (
        r"^(\d+(?:\.\d+)?(?:/\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*("
        + units
        + r")?\s*(.+)$"
    )

    match = re.match(pattern, ingredient_text.strip(), re.IGNORECASE)

    if match:
        quantity_str = match.group(1)
        unit = match.group(2)
        remaining = match.group(3)

        # Convert quantity to float
        try:
            if "/" in quantity_str:
                # Handle fractions like "1/2" or "1 1/2"
                parts = quantity_str.split()
                if len(parts) == 2:  # "1 1/2"
                    whole, fraction = parts
                    num, denom = fraction.split("/")
                    quantity = float(whole) + float(num) / float(denom)
                else:  # "1/2"
                    num, denom = quantity_str.split("/")
                    quantity = float(num) / float(denom)
            elif "-" in quantity_str:
                # Handle ranges like "2-3"
                quantity = float(quantity_str.split("-")[0])
            else:
                quantity = float(quantity_str)
        except ValueError:
            quantity = None
    else:
        # No quantity/unit found, treat entire text as ingredient name
        quantity = None
        unit = None
        remaining = ingredient_text

    # Split remaining text to separate ingredient from preparation
    # Look for common preparation indicators
    prep_indicators = [
        "chopped",
        "diced",
        "sliced",
        "minced",
        "grated",
        "peeled",
        "cooked",
        "fresh",
        "dried",
        "ground",
        "whole",
        "crushed",
        "beaten",
        "melted",
    ]

    name = remaining.strip()
    preparation = None

    # Look for preparation at the end
    for prep in prep_indicators:
        if prep in name.lower():
            # Try to split on the preparation word
            parts = name.lower().split(prep)
            if len(parts) == 2 and parts[1].strip() == "":
                # Preparation is at the end
                name = parts[0].strip()
                preparation = prep
                break
            elif len(parts) == 2 and parts[0].strip():
                # Preparation is in the middle/end
                name = parts[0].strip()
                preparation = prep + parts[1].strip()
                break

    # Clean up the name
    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(",")

    return {
        "name": name,
        "quantity": quantity,
        "unit": unit.lower() if unit else None,
        "preparation": preparation,
        "optional": "optional" in ingredient_text.lower(),
        "category": None,  # Could be enhanced with ingredient categorization
    }


@bp.route("/recipes/<int:recipe_id>/privacy", methods=["PUT"])
@require_auth
def toggle_recipe_privacy(current_user, recipe_id: int) -> Response:
    """Toggle recipe privacy (public/private)."""

    # Verify recipe exists and user has permission
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    try:
        data = request.get_json()
        if not data or "is_public" not in data:
            return jsonify({"error": "is_public field is required"}), 400

        is_public = data["is_public"]
        if not isinstance(is_public, bool):
            return jsonify({"error": "is_public must be a boolean"}), 400

        # Prevent making public recipes private
        if not is_public and recipe.is_public:
            return (
                jsonify(
                    {
                        "error": "Cannot make public recipes private. Once a recipe is public, it cannot be made private again. You can only delete it."
                    }
                ),
                400,
            )

        # Check if recipe can be published (copyright protection)
        if is_public and not recipe.is_public:
            can_publish, restriction_reason = recipe.can_be_published()
            if not can_publish:
                return (
                    jsonify(
                        {
                            "error": restriction_reason,
                            "can_be_published": False,
                            "is_original_recipe": recipe.is_original_recipe,
                        }
                    ),
                    403,
                )

        # When making recipe public, require copyright consent
        if is_public and not recipe.is_public:
            copyright_consent = data.get("copyright_consent", {})

            # Validate all required consents are present and true
            required_consents = [
                "rightsToShare",
                "understandsPublic",
                "personalUseOnly",
                "noCopyrightViolation",
            ]

            for consent in required_consents:
                if not copyright_consent.get(consent):
                    return (
                        jsonify(
                            {
                                "error": f"Copyright consent required: {consent} must be acknowledged"
                            }
                        ),
                        400,
                    )

            # Record copyright consent
            consent_record = CopyrightConsent(
                user_id=current_user.id,
                recipe_id=recipe.id,
                consent_data=copyright_consent,
                consent_type="publish",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
            )
            db.session.add(consent_record)

        # Update privacy status
        if is_public:
            recipe.publish()
            message = "Recipe published successfully"
        else:
            recipe.unpublish()
            message = "Recipe made private successfully"

        db.session.commit()
        current_app.logger.info(
            f"Recipe {recipe_id} privacy changed to {'public' if is_public else 'private'} by user {current_user.id}"
        )

        return jsonify(
            {
                "message": message,
                "recipe": recipe.to_dict(
                    current_user_id=current_user.id,
                    is_admin=not should_apply_user_filter(current_user),
                ),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Privacy toggle failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Privacy update failed"}), 500


@bp.route("/recipes/<int:recipe_id>/publish", methods=["POST"])
@require_auth
def publish_recipe(current_user, recipe_id: int) -> Response:
    """Publish a recipe to make it public."""

    # Verify recipe exists and user has permission
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    try:
        if recipe.is_public:
            return jsonify({"message": "Recipe is already public"}), 200

        recipe.publish()
        db.session.commit()

        current_app.logger.info(
            f"Recipe {recipe_id} published by user {current_user.id}"
        )

        return jsonify(
            {"message": "Recipe published successfully", "recipe": recipe.to_dict()}
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Recipe publish failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Recipe publish failed"}), 500


@bp.route("/recipes/<int:recipe_id>/unpublish", methods=["POST"])
@require_auth
def unpublish_recipe(current_user, recipe_id: int) -> Response:
    """Unpublish a recipe to make it private."""

    # Verify recipe exists and user has permission
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    else:
        recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    try:
        if not recipe.is_public:
            return jsonify({"message": "Recipe is already private"}), 200

        recipe.unpublish()
        db.session.commit()

        current_app.logger.info(
            f"Recipe {recipe_id} unpublished by user {current_user.id}"
        )

        return jsonify(
            {"message": "Recipe made private successfully", "recipe": recipe.to_dict()}
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Recipe unpublish failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Recipe unpublish failed"}), 500


@bp.route("/recipes/<int:recipe_id>/add-to-collection", methods=["POST"])
@require_auth
def add_to_collection(current_user, recipe_id: int) -> Response:
    """Add a recipe to user's collection."""

    # Check if recipe exists and is accessible
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    # Check if user can access this recipe (public or own recipe)
    is_admin = not should_apply_user_filter(current_user)
    can_view = recipe.can_be_viewed_by(current_user.id, is_admin)

    if not can_view:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    # Check if already in collection
    existing = UserRecipeCollection.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()

    if existing:
        return jsonify({"message": "Recipe already in collection"}), 200

    try:
        # Add to collection
        collection_item = UserRecipeCollection(
            user_id=current_user.id, recipe_id=recipe_id
        )
        db.session.add(collection_item)
        db.session.commit()

        current_app.logger.info(
            f"Recipe {recipe_id} added to collection by user {current_user.id}"
        )

        return (
            jsonify(
                {
                    "message": "Recipe added to collection successfully",
                    "collection_item": collection_item.to_dict(),
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Add to collection failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Failed to add recipe to collection"}), 500


@bp.route("/recipes/<int:recipe_id>/remove-from-collection", methods=["DELETE"])
@require_auth
def remove_from_collection(current_user, recipe_id: int) -> Response:
    """Remove a recipe from user's collection."""

    # Find the collection item
    collection_item = UserRecipeCollection.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()

    if not collection_item:
        return jsonify({"error": "Recipe not in collection"}), 404

    try:
        db.session.delete(collection_item)
        db.session.commit()

        current_app.logger.info(
            f"Recipe {recipe_id} removed from collection by user {current_user.id}"
        )

        return jsonify({"message": "Recipe removed from collection successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Remove from collection failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Failed to remove recipe from collection"}), 500


@bp.route("/recipes/discover", methods=["GET"])
@require_auth
def discover_recipes(current_user) -> Response:
    """Browse public recipes that are not in user's collection."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "")

    # Get IDs of recipes already in user's collection
    user_collection_ids = db.session.execute(
        text("SELECT recipe_id FROM user_recipe_collections WHERE user_id = :user_id"),
        {"user_id": current_user.id},
    ).fetchall()

    collected_recipe_ids = [row.recipe_id for row in user_collection_ids]

    # Base query for public recipes not in collection and not owned by user
    query = Recipe.query.options(db.joinedload(Recipe.images)).filter(
        Recipe.is_public, Recipe.user_id != current_user.id
    )

    # Exclude recipes already in collection
    if collected_recipe_ids:
        query = query.filter(~Recipe.id.in_(collected_recipe_ids))

    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                Recipe.title.ilike(f"%{search}%"),
                Recipe.description.ilike(f"%{search}%"),
            )
        )

    # Course type filtering
    course_type = request.args.get("course_type", "").strip()
    if course_type:
        query = query.filter(Recipe.course_type == course_type)

    # Ingredient filtering
    ingredients_param = request.args.get("ingredients", "").strip()
    ingredient_match = request.args.get("ingredient_match", "any")

    if ingredients_param:
        ingredient_names = [
            name.strip().lower()
            for name in ingredients_param.split(",")
            if name.strip()
        ]

        if ingredient_names:
            if ingredient_match == "all":
                # ALL mode: must have every ingredient
                for ingredient_name in ingredient_names:
                    subquery = (
                        db.session.query(recipe_ingredients.c.recipe_id)
                        .join(
                            Ingredient,
                            Ingredient.id == recipe_ingredients.c.ingredient_id,
                        )
                        .filter(Ingredient.name.ilike(f"%{ingredient_name}%"))
                        .subquery()
                    )
                    query = query.filter(Recipe.id.in_(subquery))
            else:
                # ANY mode: has at least one ingredient
                subquery = (
                    db.session.query(recipe_ingredients.c.recipe_id)
                    .join(
                        Ingredient, Ingredient.id == recipe_ingredients.c.ingredient_id
                    )
                    .filter(
                        db.or_(
                            *[
                                Ingredient.name.ilike(f"%{name}%")
                                for name in ingredient_names
                            ]
                        )
                    )
                    .distinct()
                    .subquery()
                )
                query = query.filter(Recipe.id.in_(subquery))

    # Order by publication date (newest first)
    query = query.order_by(Recipe.published_at.desc())

    recipes = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "recipes": [
                recipe.to_dict(
                    include_user=True,
                    current_user_id=current_user.id,
                    is_admin=not should_apply_user_filter(current_user),
                )
                for recipe in recipes.items
            ],
            "total": recipes.total,
            "pages": recipes.pages,
            "current_page": page,
            "per_page": per_page,
            "has_next": recipes.has_next,
            "has_prev": recipes.has_prev,
        }
    )


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


@bp.route("/recipes/<int:recipe_id>/copy", methods=["POST"])
@require_auth
def copy_recipe(current_user, recipe_id: int) -> Response:
    """Create a copy of a public recipe for the current user."""
    # Check if recipe exists and is public
    recipe = Recipe.query.options(
        db.joinedload(Recipe.images),
        db.joinedload(Recipe.ingredients),
        db.joinedload(Recipe.recipe_instructions),
        db.joinedload(Recipe.recipe_tags),
    ).get(recipe_id)

    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    # Only public recipes can be copied
    if not recipe.is_public:
        return jsonify({"error": "Only public recipes can be copied"}), 403

    # Users cannot copy their own recipes
    if recipe.user_id == current_user.id:
        return jsonify({"error": "You cannot copy your own recipe"}), 400

    try:
        # Create new recipe with copied data
        new_recipe = Recipe(
            title=f"{recipe.title} (Copy)",
            description=recipe.description,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            servings=recipe.servings,
            difficulty=recipe.difficulty,
            source=recipe.source,
            user_id=current_user.id,
            uploaded_by_id=current_user.id,
            is_public=False,  # Copied recipes are private by default
            cookbook_id=None,  # Remove cookbook association
        )

        db.session.add(new_recipe)
        db.session.flush()  # Get the new recipe ID

        # Copy ingredients
        for ingredient in recipe.ingredients:
            # Get the association data from the recipe_ingredients table
            association = db.session.execute(
                recipe_ingredients.select().where(
                    recipe_ingredients.c.recipe_id == recipe_id,
                    recipe_ingredients.c.ingredient_id == ingredient.id,
                )
            ).first()

            if association:
                # Create new association for the copied recipe
                new_association = recipe_ingredients.insert().values(
                    recipe_id=new_recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=association.quantity,
                    unit=association.unit,
                    preparation=association.preparation,
                    optional=association.optional,
                    order=association.order,
                )
                db.session.execute(new_association)

        # Copy instructions
        for instruction in recipe.recipe_instructions:
            new_instruction = Instruction(
                recipe_id=new_recipe.id,
                step_number=instruction.step_number,
                text=instruction.text,
            )
            db.session.add(new_instruction)

        # Copy tags
        for tag in recipe.recipe_tags:
            new_recipe.recipe_tags.append(tag)

        # Copy images
        for image in recipe.images:
            # Copy the image file
            original_path = Path(image.file_path)
            if original_path.exists():
                # Generate new filename
                new_filename = f"{uuid.uuid4()}.{image.filename.split('.')[-1]}"
                new_path = original_path.parent / new_filename

                # Copy the file
                import shutil

                shutil.copy2(original_path, new_path)

                # Create new image record
                new_image = RecipeImage(
                    recipe_id=new_recipe.id,
                    filename=new_filename,
                    original_filename=image.original_filename,
                    file_path=str(new_path),
                    file_size=image.file_size,
                    content_type=image.content_type,
                )
                db.session.add(new_image)

        db.session.commit()

        # Return the copied recipe
        return (
            jsonify(
                {
                    "recipe": new_recipe.to_dict(include_user=True),
                    "message": "Recipe copied successfully",
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error copying recipe: {e}")
        return jsonify({"error": "Failed to copy recipe"}), 500


@bp.route("/recipes/upload-multi", methods=["POST"])
@require_auth
@rate_limit_upload
def upload_multi_recipe(current_user):
    """Upload multiple images for a single recipe"""
    try:
        # Check for cache bypass header (used during load testing)
        skip_cache = request.headers.get("X-Skip-Cache", "").lower() == "true"
        if skip_cache:
            current_app.logger.info("Cache bypass enabled via X-Skip-Cache header")

        # Check upload limit for free users
        subscription = current_user.get_or_create_subscription()
        current_app.logger.info(
            f"Upload check for user {current_user.id} ({current_user.username}): "
            f"tier={subscription.tier.value}, status={subscription.status.value}, "
            f"monthly_uploads={subscription.monthly_upload_count}, "
            f"is_premium={subscription.is_premium()}, "
            f"can_upload={current_user.can_upload_recipe()}"
        )

        if not current_user.can_upload_recipe():
            current_app.logger.warning(
                f"User {current_user.id} ({current_user.username}) reached upload limit: "
                f"{subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
            )
            return jsonify(
                {
                    "error": "Upload limit reached",
                    "message": f"You've used all {subscription.monthly_upload_count} of your free uploads this month. Upgrade to Premium for unlimited uploads.",
                    "remaining_uploads": 0,
                    "monthly_upload_count": subscription.monthly_upload_count,
                    "is_premium": False,
                    "upgrade_required": True,
                }
            ), 403

        user_id = current_user.id

        # Check if files are present
        if "images" not in request.files:
            return jsonify({"error": "No images provided"}), 400

        files = request.files.getlist("images")
        if not files or len(files) == 0:
            return jsonify({"error": "No images provided"}), 400

        # Validate maximum number of images
        max_images = current_app.config.get("MAX_IMAGES_PER_RECIPE", 10)
        if len(files) > max_images:
            return (
                jsonify({"error": f"Maximum {max_images} images allowed per recipe"}),
                400,
            )

        # Validate total file size
        total_size = 0
        max_total_size = current_app.config.get(
            "MAX_TOTAL_UPLOAD_SIZE", 50 * 1024 * 1024
        )  # 50MB default

        validated_files = []
        for i, file in enumerate(files):
            if file.filename == "":
                return jsonify({"error": f"Image {i + 1} has no filename"}), 400

            if not allowed_file(file.filename):
                return (
                    jsonify(
                        {
                            "error": f"Image {i + 1} has invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                        }
                    ),
                    400,
                )

            # Seek to end to get file size, then reset
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning

            total_size += file_size
            validated_files.append((file, file_size))

        if total_size > max_total_size:
            return (
                jsonify(
                    {
                        "error": f"Total file size exceeds {max_total_size // (1024 * 1024)}MB limit"
                    }
                ),
                400,
            )

        # Get optional cookbook information
        cookbook_id = request.form.get("cookbook_id")

        # Get recipe source information (is_original_recipe)
        is_original_recipe_str = request.form.get("is_original_recipe")
        is_original_recipe = None
        if is_original_recipe_str is not None:
            is_original_recipe = is_original_recipe_str.lower() == "true"

        # Get translation option
        translate_to_english = (
            request.form.get("translate_to_english", "").lower() == "true"
        )

        # Validate cookbook if provided
        cookbook = None
        if cookbook_id:
            try:
                cookbook_id = int(cookbook_id)
                # Check if cookbook exists
                cookbook = Cookbook.query.get(cookbook_id)
                if not cookbook:
                    current_app.logger.error(f"Cookbook {cookbook_id} does not exist")
                    return jsonify(
                        {"error": f"Cookbook with ID {cookbook_id} not found"}
                    ), 404

                # Allow access if: user owns cookbook OR it's a global cookbook (Google Books)
                is_global_cookbook = cookbook.user_id is None
                is_own_cookbook = cookbook.user_id == user_id
                if not is_global_cookbook and not is_own_cookbook:
                    current_app.logger.error(
                        f"User {user_id} cannot add to cookbook {cookbook_id}. "
                        f"Owner is {cookbook.user_id}"
                    )
                    return jsonify(
                        {
                            "error": "You don't have permission to add recipes to this cookbook"
                        }
                    ), 403

                # If cookbook is from Google Books, force is_original_recipe = False
                # (recipes from published cookbooks cannot be made public)
                if cookbook.google_books_id:
                    is_original_recipe = False
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid cookbook ID"}), 400

        # Create MultiRecipeJob
        multi_job = MultiRecipeJob(
            user_id=user_id,
            total_images=len(validated_files),
            status=ProcessingStatus.PENDING,
            skip_cache=skip_cache,
            is_original_recipe=is_original_recipe,
            translate_to_english=translate_to_english,
        )
        db.session.add(multi_job)
        db.session.flush()  # Get the ID

        # Save images and create processing jobs
        processing_jobs = []

        for i, (file, file_size) in enumerate(validated_files):
            # Use the same image processing function as single upload (includes Cloudinary)
            file.seek(0)  # Reset file pointer
            recipe_image = process_and_save_image(
                file, file.filename, folder="recipes/multi"
            )

            # Set multi-image specific fields
            recipe_image.image_order = i  # Set order based on upload sequence

            db.session.add(recipe_image)
            db.session.flush()  # Get the ID

            # Create processing job
            processing_job = ProcessingJob(
                image_id=recipe_image.id,
                cookbook_id=cookbook_id,
                user_id=current_user.id,
                is_multi_image=True,
                multi_job_id=multi_job.id,
                image_order=i,
                status=ProcessingStatus.PENDING,
                translate_to_english=translate_to_english,
            )
            db.session.add(processing_job)
            processing_jobs.append(processing_job)

        db.session.commit()

        # Increment upload count for free users after successful upload
        if not current_user.is_premium():
            subscription = current_user.get_or_create_subscription()
            subscription.increment_upload_count()
            db.session.commit()
            current_app.logger.info(
                f"Upload count incremented for user {current_user.id}: {subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
            )

        # Queue background processing via Celery task queue
        # This ensures sequential processing to prevent memory spikes
        from app.tasks.recipe_tasks import process_multi_recipe_task

        current_app.logger.info(
            f"Queuing Celery multi-image task for job {multi_job.id}"
        )

        # Dispatch the task to Celery worker (returns immediately)
        process_multi_recipe_task.delay(multi_job.id)

        current_app.logger.info(
            f"Created multi-image job {multi_job.id} with {len(processing_jobs)} images for user {user_id}"
        )

        # Collect image data for immediate preview
        images_data = []
        for processing_job in processing_jobs:
            recipe_image = RecipeImage.query.get(processing_job.image_id)
            if recipe_image:
                images_data.append(recipe_image.to_dict())

        return (
            jsonify(
                {
                    "multi_job_id": multi_job.id,
                    "total_images": len(processing_jobs),
                    "images": images_data,  # Include image data for immediate preview
                    "message": f"Multi-image upload started with {len(processing_jobs)} images",
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in multi-image upload: {e}")
        return jsonify({"error": "Failed to process multi-image upload"}), 500


@bp.route("/recipes/upload-text", methods=["POST"])
@require_auth
def upload_recipe_text(current_user) -> Tuple[Response, int]:
    """Upload recipe text directly for processing (bypassing OCR)."""
    current_app.logger.info(
        f"Text recipe upload request from user {current_user.id} ({current_user.username})"
    )

    try:
        # Check upload limit for free users
        subscription = current_user.get_or_create_subscription()
        current_app.logger.info(
            f"Upload check for user {current_user.id} ({current_user.username}): "
            f"tier={subscription.tier.value}, status={subscription.status.value}, "
            f"monthly_uploads={subscription.monthly_upload_count}, "
            f"is_premium={subscription.is_premium()}, "
            f"can_upload={current_user.can_upload_recipe()}"
        )

        if not current_user.can_upload_recipe():
            current_app.logger.warning(
                f"User {current_user.id} ({current_user.username}) reached upload limit: "
                f"{subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
            )
            return jsonify(
                {
                    "error": "Upload limit reached",
                    "message": f"You've used all {subscription.monthly_upload_count} of your free uploads this month. Upgrade to Premium for unlimited uploads.",
                    "remaining_uploads": 0,
                    "monthly_upload_count": subscription.monthly_upload_count,
                    "is_premium": False,
                    "upgrade_required": True,
                }
            ), 403
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Extract text content
        recipe_text = data.get("text", "").strip()
        if not recipe_text:
            return jsonify({"error": "No recipe text provided"}), 400

        # Validate text length (reasonable limits)
        max_text_length = current_app.config.get(
            "MAX_RECIPE_TEXT_LENGTH", 50000
        )  # 50KB default
        if len(recipe_text) > max_text_length:
            return (
                jsonify(
                    {
                        "error": f"Recipe text too long ({len(recipe_text)} characters). Maximum {max_text_length} characters allowed."
                    }
                ),
                400,
            )

        current_app.logger.info(
            f"Processing recipe text: {len(recipe_text)} characters"
        )

        # Get optional cookbook information
        cookbook_id = data.get("cookbook_id")
        create_new_cookbook = data.get("create_new_cookbook", False)

        # Get recipe source information (is_original_recipe)
        is_original_recipe = data.get("is_original_recipe")
        # is_original_recipe can be True, False, or None (not specified)

        # Get translation option
        translate_to_english = data.get("translate_to_english", False)

        # Handle new cookbook creation (same logic as image upload)
        cookbook = None
        if create_new_cookbook:
            new_cookbook_title = data.get("new_cookbook_title", "").strip()
            if not new_cookbook_title:
                return (
                    jsonify(
                        {
                            "error": "Cookbook title is required when creating a new cookbook"
                        }
                    ),
                    400,
                )

            try:
                cookbook = Cookbook(
                    title=new_cookbook_title,
                    author=data.get("new_cookbook_author", "").strip() or None,
                    description=data.get("new_cookbook_description", "").strip()
                    or None,
                    publisher=data.get("new_cookbook_publisher", "").strip() or None,
                    isbn=data.get("new_cookbook_isbn", "").strip() or None,
                    user_id=current_user.id,
                )

                publication_date = data.get("new_cookbook_publication_date", "").strip()
                if publication_date:
                    try:
                        from datetime import datetime

                        cookbook.publication_date = datetime.fromisoformat(
                            publication_date
                        )
                    except ValueError:
                        return (
                            jsonify({"error": "Invalid publication date format"}),
                            400,
                        )

                db.session.add(cookbook)
                db.session.flush()
                cookbook_id = cookbook.id

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Cookbook creation failed: {str(e)}")
                return jsonify({"error": "Failed to create cookbook"}), 500

        elif cookbook_id:
            try:
                cookbook_id = int(cookbook_id)
                cookbook = Cookbook.query.get(cookbook_id)
                if not cookbook:
                    return jsonify({"error": "Cookbook not found"}), 400

                # If cookbook is from Google Books, force is_original_recipe = False
                # (recipes from published cookbooks cannot be made public)
                if cookbook.google_books_id:
                    is_original_recipe = False
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid cookbook_id"}), 400

        # Process the text directly using the recipe parser
        recipe_parser = RecipeParser()
        parsed_recipe = recipe_parser.parse_recipe_text(
            recipe_text, translate_to_english=translate_to_english
        )

        current_app.logger.info(f"Parsed recipe: {parsed_recipe}")

        # Create the recipe directly (no background processing needed for text)
        # Handle None or empty title - ensure we always have a valid title
        recipe_title = parsed_recipe.get("title")
        if not recipe_title or not recipe_title.strip():
            recipe_title = "Untitled Recipe"

        recipe = Recipe(
            title=recipe_title,
            description=parsed_recipe.get("description"),
            cookbook_id=cookbook_id,
            user_id=current_user.id,
            uploaded_by_id=current_user.id,
            is_public=False,  # Default to private
            is_original_recipe=is_original_recipe,  # Track recipe source for copyright protection
            prep_time=safe_int_conversion(parsed_recipe.get("prep_time")),
            cook_time=safe_int_conversion(parsed_recipe.get("cook_time")),
            servings=safe_int_conversion(parsed_recipe.get("servings")),
            difficulty=parsed_recipe.get("difficulty"),
            course_type=parsed_recipe.get("course_type"),
            # Translation fields
            source_language=parsed_recipe.get("source_language"),
            source_language_name=parsed_recipe.get("source_language_name"),
            is_translated=parsed_recipe.get("is_translated", False),
            original_title=parsed_recipe.get("original_title"),
            original_description=parsed_recipe.get("original_description"),
        )

        db.session.add(recipe)
        db.session.flush()  # Get recipe ID

        # Add ingredients
        if parsed_recipe.get("ingredients"):
            _create_ingredients(recipe.id, parsed_recipe)

        # Add instructions (with original text if translated)
        if parsed_recipe.get("instructions"):
            original_instructions = (
                parsed_recipe.get("original_instructions")
                if parsed_recipe.get("is_translated")
                else None
            )
            _create_instructions(
                recipe.id,
                parsed_recipe,
                recipe_text,
                original_instructions=original_instructions,
            )

        # Add tags
        if parsed_recipe.get("tags"):
            _create_tags(recipe.id, parsed_recipe)

        db.session.commit()

        # Increment upload count for free users after successful upload
        if not current_user.is_premium():
            subscription = current_user.get_or_create_subscription()
            subscription.increment_upload_count()
            db.session.commit()
            current_app.logger.info(
                f"Upload count incremented for user {current_user.id}: {subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
            )

        current_app.logger.info(
            f"Successfully created recipe {recipe.id} from text: '{recipe.title}'"
        )

        return (
            jsonify(
                {
                    "message": "Recipe created successfully from text",
                    "recipe_id": recipe.id,
                    "recipe": {
                        "id": recipe.id,
                        "title": recipe.title,
                        "description": recipe.description,
                        "cookbook_id": recipe.cookbook_id,
                        "prep_time": recipe.prep_time,
                        "cook_time": recipe.cook_time,
                        "servings": recipe.servings,
                        "difficulty": recipe.difficulty,
                    },
                    "cookbook": cookbook.to_dict() if cookbook else None,
                    "parsing_info": {
                        "confidence": parsed_recipe.get(
                            "parsing_confidence", "unknown"
                        ),
                        "notes": parsed_recipe.get("parsing_notes", ""),
                    },
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Text upload failed: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to process recipe text"}), 500


@bp.route("/recipes/upload-url", methods=["POST"])
@require_auth
def upload_recipe_url(current_user) -> Tuple[Response, int]:
    """Import a recipe from a URL."""
    from app.services.url_recipe_service import (
        UrlRecipeService,
        UrlValidationError,
        UrlFetchError,
        BotProtectionError,
        RecipeNotFoundError,
    )

    current_app.logger.info(
        f"URL recipe import request from user {current_user.id} ({current_user.username})"
    )

    try:
        # Check upload limit for free users
        subscription = current_user.get_or_create_subscription()
        current_app.logger.info(
            f"Upload check for user {current_user.id} ({current_user.username}): "
            f"tier={subscription.tier.value}, status={subscription.status.value}, "
            f"monthly_uploads={subscription.monthly_upload_count}, "
            f"is_premium={subscription.is_premium()}, "
            f"can_upload={current_user.can_upload_recipe()}"
        )

        if not current_user.can_upload_recipe():
            current_app.logger.warning(
                f"User {current_user.id} ({current_user.username}) reached upload limit: "
                f"{subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
            )
            return jsonify(
                {
                    "error": "Upload limit reached",
                    "message": f"You've used all {subscription.monthly_upload_count} of your free uploads this month. Upgrade to Premium for unlimited uploads.",
                    "remaining_uploads": 0,
                    "monthly_upload_count": subscription.monthly_upload_count,
                    "is_premium": False,
                    "upgrade_required": True,
                }
            ), 403

        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Extract URL
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "No URL provided"}), 400

        current_app.logger.info(f"Importing recipe from URL: {url}")

        # Get optional parameters
        cookbook_id = data.get("cookbook_id")
        create_new_cookbook = data.get("create_new_cookbook", False)
        translate_to_english = data.get("translate_to_english", False)

        # URL imports are always marked as not original (from external source)
        is_original_recipe = False

        # Handle new cookbook creation (same logic as other upload endpoints)
        cookbook = None
        if create_new_cookbook:
            new_cookbook_title = data.get("new_cookbook_title", "").strip()
            if not new_cookbook_title:
                return (
                    jsonify(
                        {
                            "error": "Cookbook title is required when creating a new cookbook"
                        }
                    ),
                    400,
                )

            try:
                cookbook = Cookbook(
                    title=new_cookbook_title,
                    author=data.get("new_cookbook_author", "").strip() or None,
                    description=data.get("new_cookbook_description", "").strip()
                    or None,
                    publisher=data.get("new_cookbook_publisher", "").strip() or None,
                    isbn=data.get("new_cookbook_isbn", "").strip() or None,
                    user_id=current_user.id,
                )

                publication_date = data.get("new_cookbook_publication_date", "").strip()
                if publication_date:
                    try:
                        cookbook.publication_date = datetime.fromisoformat(
                            publication_date
                        )
                    except ValueError:
                        return (
                            jsonify({"error": "Invalid publication date format"}),
                            400,
                        )

                db.session.add(cookbook)
                db.session.flush()
                cookbook_id = cookbook.id

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Cookbook creation failed: {str(e)}")
                return jsonify({"error": "Failed to create cookbook"}), 500

        elif cookbook_id:
            try:
                cookbook_id = int(cookbook_id)
                cookbook = Cookbook.query.get(cookbook_id)
                if not cookbook:
                    return jsonify({"error": "Cookbook not found"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid cookbook_id"}), 400

        # Import recipe from URL
        url_service = UrlRecipeService()

        try:
            result = url_service.import_from_url(
                url, translate_to_english=translate_to_english
            )
        except UrlValidationError as e:
            return jsonify({"error": str(e)}), 400
        except UrlFetchError as e:
            return jsonify({"error": str(e)}), 400
        except BotProtectionError as e:
            return jsonify({"error": str(e)}), 403
        except RecipeNotFoundError as e:
            return jsonify({"error": str(e)}), 404

        parsed_recipe = result["recipe_data"]
        extraction_method = result["extraction_method"]
        source_url = result["source_url"]

        current_app.logger.info(
            f"Extracted recipe via {extraction_method}: {parsed_recipe.get('title')}"
        )

        # Create the recipe
        recipe_title = parsed_recipe.get("title")
        if not recipe_title or not recipe_title.strip():
            recipe_title = "Untitled Recipe"

        recipe = Recipe(
            title=recipe_title,
            description=parsed_recipe.get("description"),
            cookbook_id=cookbook_id,
            user_id=current_user.id,
            uploaded_by_id=current_user.id,
            is_public=False,  # URL imports are always private
            is_original_recipe=is_original_recipe,
            source=source_url,  # Store the source URL
            prep_time=safe_int_conversion(parsed_recipe.get("prep_time")),
            cook_time=safe_int_conversion(parsed_recipe.get("cook_time")),
            servings=safe_int_conversion(parsed_recipe.get("servings")),
            difficulty=parsed_recipe.get("difficulty"),
            course_type=parsed_recipe.get("course_type"),
            # Translation fields (from Claude fallback)
            source_language=parsed_recipe.get("source_language"),
            source_language_name=parsed_recipe.get("source_language_name"),
            is_translated=parsed_recipe.get("is_translated", False),
            original_title=parsed_recipe.get("original_title"),
            original_description=parsed_recipe.get("original_description"),
        )

        db.session.add(recipe)
        db.session.flush()  # Get recipe ID

        # Link source (auto-created based on URL domain)
        from app.services.source_service import SourceService

        source = SourceService.get_or_create_source(current_user.id, source_url)
        if source:
            recipe.source_id = source.id
            current_app.logger.info(
                f"Linked recipe {recipe.id} to source {source.id} (domain: {source.domain})"
            )

        # Add ingredients
        if parsed_recipe.get("ingredients"):
            _create_ingredients(recipe.id, parsed_recipe)

        # Add instructions (with original text if translated)
        if parsed_recipe.get("instructions"):
            original_instructions = (
                parsed_recipe.get("original_instructions")
                if parsed_recipe.get("is_translated")
                else None
            )
            _create_instructions(
                recipe.id,
                parsed_recipe,
                "",  # No fallback text needed
                original_instructions=original_instructions,
            )

        # Add tags
        if parsed_recipe.get("tags"):
            _create_tags(recipe.id, parsed_recipe)

        db.session.commit()

        # Increment upload count for free users after successful upload
        if not current_user.is_premium():
            subscription = current_user.get_or_create_subscription()
            subscription.increment_upload_count()
            db.session.commit()
            current_app.logger.info(
                f"Upload count incremented for user {current_user.id}: {subscription.monthly_upload_count}/{current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)}"
            )

        current_app.logger.info(
            f"Successfully created recipe {recipe.id} from URL: '{recipe.title}'"
        )

        return (
            jsonify(
                {
                    "message": "Recipe imported successfully",
                    "recipe_id": recipe.id,
                    "recipe": {
                        "id": recipe.id,
                        "title": recipe.title,
                        "description": recipe.description,
                        "cookbook_id": recipe.cookbook_id,
                        "prep_time": recipe.prep_time,
                        "cook_time": recipe.cook_time,
                        "servings": recipe.servings,
                        "difficulty": recipe.difficulty,
                        "source": recipe.source,
                        "source_id": recipe.source_id,
                    },
                    "cookbook": cookbook.to_dict() if cookbook else None,
                    "source": source.to_dict() if source else None,
                    "extraction_method": extraction_method,
                    "source_url": source_url,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"URL import failed: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to import recipe from URL"}), 500


@bp.route("/recipes/job-status/<int:job_id>", methods=["GET"])
@require_auth
def get_job_status(current_user, job_id: int):
    """Get the processing status of a single recipe upload job."""
    try:
        job = ProcessingJob.query.get_or_404(job_id)

        # Check if job belongs to the current user or user is admin
        if should_apply_user_filter(current_user):
            can_access = False

            # Check if user initiated this job
            if job.user_id == current_user.id:
                can_access = True
            # If job has a recipe, check recipe ownership or uploader
            elif job.recipe_id:
                recipe = Recipe.query.get(job.recipe_id)
                if recipe and (
                    recipe.user_id == current_user.id
                    or recipe.uploaded_by_id == current_user.id
                ):
                    can_access = True
            # For jobs without recipe, also allow cookbook owner
            elif job.cookbook_id:
                cookbook = Cookbook.query.get(job.cookbook_id)
                if cookbook and cookbook.user_id == current_user.id:
                    can_access = True

            if not can_access:
                return jsonify({"error": "Access denied"}), 403

        response = {
            "job_id": job.id,
            "status": job.status.value if job.status else "unknown",
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "recipe_id": job.recipe_id,
        }

        # If job is completed, include recipe information
        if job.status == ProcessingStatus.COMPLETED and job.recipe_id:
            recipe = Recipe.query.get(job.recipe_id)
            if recipe:
                response["recipe"] = {
                    "id": recipe.id,
                    "title": recipe.title,
                    "url": f"/recipes/{recipe.id}",
                }

        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"Error getting job status for job {job_id}: {e}")
        import traceback

        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to get job status"}), 500


@bp.route("/recipes/multi-job-status/<int:job_id>", methods=["GET"])
@require_auth
def get_multi_job_status(current_user, job_id: int):
    """Get status of a multi-image processing job"""
    try:
        user_id = current_user.id

        # Find the multi-image job
        multi_job = MultiRecipeJob.query.filter_by(id=job_id, user_id=user_id).first()
        if not multi_job:
            return jsonify({"error": "Multi-image job not found"}), 404

        # Get all processing jobs for this multi-job
        processing_jobs = (
            ProcessingJob.query.filter_by(multi_job_id=job_id)
            .order_by(ProcessingJob.image_order)
            .all()
        )

        # Build detailed status
        job_details = []
        for job in processing_jobs:
            job_detail = job.to_dict()
            if job.image:
                job_detail["image"] = job.image.to_dict()
            job_details.append(job_detail)

        response_data = multi_job.to_dict()
        response_data["processing_jobs"] = job_details

        # If completed and recipe created, include recipe info
        if multi_job.status == ProcessingStatus.COMPLETED and multi_job.recipe_id:
            recipe = Recipe.query.get(multi_job.recipe_id)
            if recipe:
                response_data["recipe"] = recipe.to_dict(
                    current_user_id=user_id, is_admin=False
                )

        return jsonify(response_data), 200

    except Exception as e:
        current_app.logger.error(f"Error getting multi-job status: {e}")
        return jsonify({"error": "Failed to get job status"}), 500


def process_multi_image_job(multi_job_id: int):
    """Process all images in a multi-image job and combine results into a single recipe."""
    # Initialize ocr_texts at function start to prevent NoneType errors
    ocr_texts = []
    successful_jobs = []

    try:
        # Get the multi-image job
        multi_job = MultiRecipeJob.query.get(multi_job_id)
        if not multi_job:
            current_app.logger.error(f"MultiRecipeJob {multi_job_id} not found")
            return

        multi_job.status = ProcessingStatus.PROCESSING
        db.session.commit()

        # Check if caching should be bypassed (for load testing)
        use_cache = not getattr(multi_job, "skip_cache", False)
        if not use_cache:
            current_app.logger.info("Cache bypass enabled for multi-job")

        # Get all processing jobs for this multi-image job, ordered by image_order
        processing_jobs = (
            ProcessingJob.query.filter_by(multi_job_id=multi_job_id)
            .order_by(ProcessingJob.image_order)
            .all()
        )

        if not processing_jobs:
            multi_job.status = ProcessingStatus.FAILED
            multi_job.error_message = "No processing jobs found"
            db.session.commit()
            return

        current_app.logger.info(
            f"Processing {len(processing_jobs)} images for multi-job {multi_job_id}"
        )

        # Collect image paths for batch processing (use no_autoflush to prevent premature flush)
        image_paths = []
        processing_job_map = {}

        with db.session.no_autoflush:
            for processing_job in processing_jobs:
                recipe_image = RecipeImage.query.get(processing_job.image_id)
                if recipe_image:
                    image_path = Path(recipe_image.file_path)
                    image_paths.append(image_path)
                    processing_job_map[str(image_path)] = processing_job

        if not image_paths:
            multi_job.status = ProcessingStatus.FAILED
            multi_job.error_message = "No valid image paths found"
            db.session.commit()
            return

        # Use LLM-only multi-image OCR processing for memory efficiency
        try:
            from app.services.llm_ocr_service import LLMOCRService

            llm_ocr_service = LLMOCRService()

            current_app.logger.info(
                f"Starting LLM-only multi-image OCR for job {multi_job_id}"
            )

            # Process images one by one with LLM for memory efficiency
            combined_text = ""
            successful_extractions = 0
            for i, image_path in enumerate(image_paths):
                try:
                    current_app.logger.info(
                        f"Processing image {i + 1}/{len(image_paths)}: {image_path}"
                    )

                    # Get the RecipeImage object from the processing job map
                    processing_job = processing_job_map.get(str(image_path))
                    recipe_image = None
                    if processing_job:
                        recipe_image = RecipeImage.query.get(processing_job.image_id)

                    if recipe_image:
                        # Use helper function to get image data (handles both Cloudinary and local)
                        image_data = get_image_data_for_ocr(recipe_image)
                        source_info = recipe_image.file_path
                    else:
                        # Fallback: treat as local file path (legacy behavior)
                        try:
                            with open(image_path, "rb") as f:
                                image_data = f.read()
                            source_info = str(image_path)
                        except Exception as read_error:
                            current_app.logger.error(
                                f"Failed to read local image file {image_path}: {str(read_error)}"
                            )
                            raise

                    extracted_text = llm_ocr_service.extract_text_from_image(
                        image_data, source_info, use_cache=use_cache
                    )
                    combined_text += f"\n--- Page {i + 1} ---\n{extracted_text}\n"
                    successful_extractions += 1

                    # Force garbage collection after each image to free memory
                    import gc

                    gc.collect()

                except Exception as img_error:
                    current_app.logger.error(
                        f"Failed to process image {image_path}: {str(img_error)}"
                    )
                    combined_text += (
                        f"\n--- Page {i + 1} (FAILED) ---\n[Error processing image]\n"
                    )

            # Create result structure compatible with existing code
            multi_image_result = {
                "combined_text": combined_text.strip(),
                "overall_quality": 10,  # LLM is always high quality
                "completeness_score": 10,
                "processing_summary": f"Successfully processed {successful_extractions}/{len(image_paths)} images with LLM-only OCR",
            }

            current_app.logger.info(
                f"Multi-image OCR completed. Quality: {multi_image_result['overall_quality']:.1f}, Completeness: {multi_image_result['completeness_score']}/10"
            )

            # Update individual processing jobs with results

            # Check if enhanced multi-image result has the expected structure
            if "results" in multi_image_result and isinstance(
                multi_image_result["results"], list
            ):
                for result in multi_image_result["results"]:
                    image_path = result["image_path"]
                    processing_job = processing_job_map.get(image_path)

                    if processing_job:
                        if result.get("error"):
                            processing_job.status = ProcessingStatus.FAILED
                            processing_job.error_message = result["error"]
                        else:
                            processing_job.ocr_text = result["text"]
                            processing_job.ocr_confidence = result.get(
                                "quality_score", 0.0
                            )
                            processing_job.ocr_method = result.get("method", "unknown")
                            processing_job.status = ProcessingStatus.COMPLETED

                            if result["text"].strip():
                                ocr_texts.append(result["text"])
                                successful_jobs.append(processing_job)

                            multi_job.processed_images += 1

                        db.session.commit()
            else:
                # Fallback: if multi_image_result doesn't have expected structure,
                # assume it contains combined text directly
                current_app.logger.warning(
                    "Multi-image result missing 'results' key, falling back to combined text processing"
                )

                # Check for combined_text key (from LLM OCR service)
                combined_text_key = (
                    "combined_text" if "combined_text" in multi_image_result else "text"
                )

                if (
                    combined_text_key in multi_image_result
                    and multi_image_result[combined_text_key].strip()
                ):
                    # Split the combined text and assign to jobs
                    combined_text = multi_image_result[combined_text_key]
                    current_app.logger.info(
                        f"Processing combined text of length: {len(combined_text)}"
                    )

                    # Split by page markers
                    if "--- Page " in combined_text:
                        # Split by --- Page X --- markers
                        import re

                        text_parts = re.split(r"--- Page \d+ ---", combined_text)
                        # Remove empty parts
                        text_parts = [
                            part.strip() for part in text_parts if part.strip()
                        ]
                    elif "--- PAGE BREAK ---" in combined_text:
                        text_parts = combined_text.split("--- PAGE BREAK ---")
                        text_parts = [
                            part.strip() for part in text_parts if part.strip()
                        ]
                    else:
                        text_parts = [combined_text.strip()]

                    current_app.logger.info(
                        f"Split combined text into {len(text_parts)} parts"
                    )

                    for i, processing_job in enumerate(processing_jobs):
                        if i < len(text_parts) and text_parts[i].strip():
                            processing_job.ocr_text = text_parts[i].strip()
                            processing_job.ocr_confidence = (
                                multi_image_result.get("overall_quality", 10.0) / 10.0
                            )  # Convert to 0-1 scale
                            processing_job.ocr_method = "llm"
                            processing_job.status = ProcessingStatus.COMPLETED

                            ocr_texts.append(processing_job.ocr_text)
                            successful_jobs.append(processing_job)
                            multi_job.processed_images += 1

                            current_app.logger.info(
                                f"Successfully processed text for job {processing_job.id}: {len(processing_job.ocr_text)} characters"
                            )
                        else:
                            current_app.logger.warning(
                                f"No text available for processing job {processing_job.id} (part {i})"
                            )

                        db.session.commit()
                else:
                    current_app.logger.error(
                        f"Multi-image result missing both 'results' and '{combined_text_key}' keys. Available keys: {list(multi_image_result.keys())}"
                    )

        except Exception as e:
            current_app.logger.error(
                f"Enhanced multi-image OCR failed, falling back to individual processing: {e}"
            )

            # Fallback to individual processing with original retry logic
            # Reset the lists for fallback processing
            ocr_texts = []
            successful_jobs = []

            for processing_job in processing_jobs:
                max_retries = 2
                retry_count = 0
                timeout_seconds = 180  # 3 minutes per image (match Gunicorn timeout)

                while retry_count <= max_retries:
                    try:
                        processing_job.status = ProcessingStatus.PROCESSING
                        db.session.commit()

                        # Use threading timeout instead of signal (works in background threads)
                        import time
                        from concurrent.futures import (
                            ThreadPoolExecutor,
                            TimeoutError as FutureTimeoutError,
                        )

                        def ocr_task():
                            return extract_recipe_text(processing_job.image_id)

                        # Use ThreadPoolExecutor with timeout for thread-safe timeout handling
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(ocr_task)
                            ocr_result = future.result(timeout=timeout_seconds)

                        ocr_texts.append(ocr_result["text"])

                        processing_job.ocr_text = ocr_result["text"]
                        processing_job.ocr_confidence = ocr_result.get(
                            "confidence", 0.0
                        )
                        processing_job.ocr_method = ocr_result.get("method", "unknown")
                        processing_job.status = ProcessingStatus.COMPLETED

                        successful_jobs.append(processing_job)
                        multi_job.processed_images += 1

                        current_app.logger.info(
                            f"Completed OCR for image {processing_job.image_id} (job {processing_job.id})"
                        )
                        db.session.commit()
                        break  # Success, exit retry loop

                    except (FutureTimeoutError, TimeoutError, Exception) as e:
                        retry_count += 1
                        error_msg = f"Error processing image {processing_job.image_id} (attempt {retry_count}/{max_retries + 1}): {e}"
                        current_app.logger.error(error_msg, exc_info=True)

                        if retry_count > max_retries:
                            # Final failure after all retries
                            processing_job.status = ProcessingStatus.FAILED
                            processing_job.error_message = (
                                f"Failed after {max_retries + 1} attempts: {str(e)}"
                            )
                            db.session.commit()
                        else:
                            # Wait before retry (exponential backoff)
                            import time

                            wait_time = 2**retry_count  # 2, 4, 8 seconds
                            current_app.logger.info(
                                f"Retrying in {wait_time} seconds..."
                            )
                            time.sleep(wait_time)

        # Check if we have any successful OCR results
        if not ocr_texts:
            multi_job.status = ProcessingStatus.FAILED
            multi_job.error_message = "No images could be processed successfully"
            db.session.commit()
            return

        # Validate ocr_texts before proceeding
        if ocr_texts is None:
            current_app.logger.error("ocr_texts is None, initializing as empty list")
            ocr_texts = []

        if not isinstance(ocr_texts, list):
            current_app.logger.error(
                f"ocr_texts is not a list, got {type(ocr_texts)}: {ocr_texts}"
            )
            ocr_texts = []

        # Filter out None/empty entries
        ocr_texts = [
            text
            for text in ocr_texts
            if text and isinstance(text, str) and text.strip()
        ]

        current_app.logger.info(f"Final ocr_texts validation: {len(ocr_texts)} texts")
        for i, text in enumerate(ocr_texts):
            current_app.logger.info(f"  Text {i + 1}: {len(text)} characters")

        # Check if we have any valid OCR texts
        if not ocr_texts:
            current_app.logger.error("No valid OCR texts available for parsing")
            multi_job.status = ProcessingStatus.FAILED
            multi_job.error_message = "No valid OCR text extracted from images"
            db.session.commit()
            return

        # Combine OCR texts for storage
        combined_ocr_text = "\n--- PAGE BREAK ---\n".join(ocr_texts)
        multi_job.combined_ocr_text = combined_ocr_text

        try:
            # Parse the multi-image recipe with quality information
            recipe_parser = RecipeParser()

            # Pass quality information if available from enhanced processing
            quality_info = None
            try:
                if "multi_image_result" in locals():
                    current_app.logger.info(
                        f"multi_image_result type: {type(multi_image_result)}, value: {multi_image_result}"
                    )
                    if isinstance(multi_image_result, dict):
                        # Only use multi_image_result if it's a dictionary with expected structure
                        quality_info = multi_image_result
                        current_app.logger.info(
                            f"Using multi_image_result as quality_info: {quality_info}"
                        )
                    elif isinstance(multi_image_result, (int, float)):
                        # If multi_image_result is a numeric quality score, wrap it in expected structure
                        quality_info = {
                            "overall_quality": multi_image_result,
                            "completeness_score": {"score": "Unknown"},
                            "processing_summary": {"success_rate": "Unknown"},
                        }
                        current_app.logger.info(
                            f"Wrapped numeric multi_image_result as quality_info: {quality_info}"
                        )
                    else:
                        current_app.logger.warning(
                            f"multi_image_result has unexpected type: {type(multi_image_result)}"
                        )
                else:
                    current_app.logger.info("multi_image_result not found in locals()")
            except Exception as e:
                current_app.logger.error(f"Error setting up quality_info: {e}")
                quality_info = None

            # Get translation option from multi_job
            translate_to_english = getattr(multi_job, "translate_to_english", False)

            parsed_recipe = recipe_parser.parse_multi_image_recipe(
                ocr_texts,
                use_cache=use_cache,
                quality_info=quality_info,
                translate_to_english=translate_to_english,
            )
            current_app.logger.info(f"Parsed recipe result: {parsed_recipe}")

            # Log what we're about to use for recipe creation
            current_app.logger.info(
                f"Recipe title: {parsed_recipe.get('title', 'Untitled Recipe')}"
            )
            current_app.logger.info(
                f"Recipe description: {parsed_recipe.get('description')}"
            )
            current_app.logger.info(
                f"Recipe ingredients count: {len(parsed_recipe.get('ingredients', []))}"
            )
            current_app.logger.info(
                f"Recipe instructions count: {len(parsed_recipe.get('instructions', []))}"
            )

            # Get cookbook_id from processing jobs if available
            cookbook_id = None
            if successful_jobs:
                cookbook_id = successful_jobs[0].cookbook_id
                current_app.logger.info(f"Setting recipe cookbook_id to: {cookbook_id}")

            # Ensure we have a valid title
            recipe_title = parsed_recipe.get("title")
            if not recipe_title or recipe_title.strip() == "":
                recipe_title = "Untitled Recipe"
                current_app.logger.warning(
                    f"Recipe title was empty, using default: {recipe_title}"
                )

            # Create the recipe
            recipe = Recipe(
                title=recipe_title,
                description=parsed_recipe.get("description"),
                cookbook_id=cookbook_id,
                user_id=multi_job.user_id,
                uploaded_by_id=multi_job.user_id,
                is_public=False,  # Default to private
                is_original_recipe=multi_job.is_original_recipe,  # Track recipe source for copyright protection
                # Translation fields
                source_language=parsed_recipe.get("source_language"),
                source_language_name=parsed_recipe.get("source_language_name"),
                is_translated=parsed_recipe.get("is_translated", False),
                original_title=parsed_recipe.get("original_title"),
                original_description=parsed_recipe.get("original_description"),
            )
            db.session.add(recipe)
            db.session.flush()  # Get recipe ID

            # Add ingredients if any
            if parsed_recipe.get("ingredients"):
                _create_ingredients(recipe.id, parsed_recipe)

            # Add instructions if any
            if parsed_recipe.get("instructions"):
                original_instructions = parsed_recipe.get("original_instructions", [])
                for i, instruction_text in enumerate(parsed_recipe["instructions"]):
                    # Get original text if available (for translations)
                    original_text = None
                    if original_instructions and i < len(original_instructions):
                        original_text = original_instructions[i]

                    instruction = Instruction(
                        recipe_id=recipe.id,
                        step_number=i + 1,
                        text=instruction_text,
                        original_text=original_text,
                    )
                    db.session.add(instruction)

            # Set recipe metadata
            if parsed_recipe.get("prep_time"):
                recipe.prep_time = safe_int_conversion(parsed_recipe["prep_time"])
            if parsed_recipe.get("cook_time"):
                recipe.cook_time = safe_int_conversion(parsed_recipe["cook_time"])
            if parsed_recipe.get("servings"):
                recipe.servings = safe_int_conversion(parsed_recipe["servings"])
            if parsed_recipe.get("difficulty"):
                recipe.difficulty = parsed_recipe["difficulty"]

            # Link all images to the recipe (use no_autoflush to prevent premature flush)
            with db.session.no_autoflush:
                for processing_job in successful_jobs:
                    recipe_image = RecipeImage.query.get(processing_job.image_id)
                    if recipe_image:
                        recipe_image.recipe_id = recipe.id

            # Update multi-job with recipe reference
            multi_job.recipe_id = recipe.id
            multi_job.status = ProcessingStatus.COMPLETED
            multi_job.completed_at = datetime.utcnow()

            db.session.commit()
            current_app.logger.info(
                f"Successfully created recipe {recipe.id} from multi-job {multi_job_id}"
            )

        except Exception as e:
            current_app.logger.error(
                f"Error parsing multi-image recipe for job {multi_job_id}: {e}",
                exc_info=True,
            )
            # Rollback any pending changes before updating status
            db.session.rollback()
            multi_job = MultiRecipeJob.query.get(multi_job_id)
            if multi_job:
                multi_job.status = ProcessingStatus.FAILED
                multi_job.error_message = f"Recipe parsing failed: {str(e)}"
                db.session.commit()
            # Cleanup orphaned images for failed parsing
            cleanup_failed_multi_job(multi_job_id)

    except Exception as e:
        current_app.logger.error(
            f"Error in process_multi_image_job {multi_job_id}: {e}", exc_info=True
        )
        try:
            # Rollback any pending changes before updating status
            db.session.rollback()
            multi_job = MultiRecipeJob.query.get(multi_job_id)
            if multi_job:
                multi_job.status = ProcessingStatus.FAILED
                multi_job.error_message = f"Processing failed: {str(e)}"
                db.session.commit()
                # Cleanup orphaned images for completely failed job
                cleanup_failed_multi_job(multi_job_id)
        except Exception as commit_error:
            current_app.logger.error(f"Error updating job status: {commit_error}")
            # Final rollback to ensure clean state
            try:
                db.session.rollback()
            except Exception:
                pass


def cleanup_failed_multi_job(multi_job_id: int):
    """Clean up files and database records for a failed multi-image job."""
    try:
        # Get all processing jobs for this multi-image job
        processing_jobs = ProcessingJob.query.filter_by(multi_job_id=multi_job_id).all()

        for processing_job in processing_jobs:
            try:
                # Get the associated image (use no_autoflush for safety)
                with db.session.no_autoflush:
                    recipe_image = RecipeImage.query.get(processing_job.image_id)
                if recipe_image and recipe_image.recipe_id is None:
                    # Only cleanup orphaned images (not linked to a recipe)
                    file_path = Path(recipe_image.file_path)
                    if file_path.exists():
                        file_path.unlink()
                        current_app.logger.info(
                            f"Deleted orphaned image file: {file_path}"
                        )

                    # Delete the image record
                    db.session.delete(recipe_image)
                    current_app.logger.info(
                        f"Deleted orphaned image record: {recipe_image.id}"
                    )

                # Delete the processing job
                db.session.delete(processing_job)

            except Exception as e:
                current_app.logger.error(
                    f"Error cleaning up processing job {processing_job.id}: {e}"
                )

        db.session.commit()
        current_app.logger.info(
            f"Cleanup completed for failed multi-job {multi_job_id}"
        )

    except Exception as e:
        current_app.logger.error(
            f"Error in cleanup_failed_multi_job {multi_job_id}: {e}"
        )
        db.session.rollback()


# Instruction Image Endpoints


@bp.route(
    "/recipes/<int:recipe_id>/instructions/<int:instruction_id>/image", methods=["POST"]
)
@require_auth
def upload_instruction_image(
    current_user, recipe_id: int, instruction_id: int
) -> Response:
    """Upload an image for a specific instruction step."""
    # Verify recipe exists and user has edit permission
    recipe = Recipe.query.get_or_404(recipe_id)

    # Check if user can edit this recipe (only owner or admin)
    is_admin = current_user.role.value == "admin"
    if not is_admin and recipe.user_id != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    # Verify instruction exists and belongs to recipe
    instruction = Instruction.query.filter_by(
        id=instruction_id, recipe_id=recipe_id
    ).first()

    if not instruction:
        return jsonify({"error": "Instruction not found"}), 404

    # Check if file is provided
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No image selected"}), 400

    if not allowed_file(file.filename):
        return (
            jsonify({"error": "Invalid file type. Only images are allowed"}),
            400,
        )

    try:
        # Process and upload image (similar to recipe images)
        image_record = process_and_save_image(
            file, file.filename, folder="instructions"
        )

        # Update instruction with image information
        instruction.image_filename = image_record.filename
        instruction.image_url = image_record.file_path
        instruction.cloudinary_public_id = image_record.cloudinary_public_id
        instruction.cloudinary_url = image_record.cloudinary_url
        instruction.cloudinary_thumbnail_url = image_record.cloudinary_thumbnail_url

        db.session.commit()

        return jsonify(
            {
                "message": "Instruction image uploaded successfully",
                "instruction": instruction.to_dict(),
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading instruction image: {e}")
        return jsonify({"error": "Failed to upload image"}), 500


@bp.route(
    "/recipes/<int:recipe_id>/instructions/<int:instruction_id>/image",
    methods=["DELETE"],
)
@require_auth
def remove_instruction_image(
    current_user, recipe_id: int, instruction_id: int
) -> Response:
    """Remove image from a specific instruction step."""
    # Verify recipe exists and user has edit permission
    recipe = Recipe.query.get_or_404(recipe_id)

    # Check if user can edit this recipe (only owner or admin)
    is_admin = current_user.role.value == "admin"
    if not is_admin and recipe.user_id != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    # Verify instruction exists and belongs to recipe
    instruction = Instruction.query.filter_by(
        id=instruction_id, recipe_id=recipe_id
    ).first()

    if not instruction:
        return jsonify({"error": "Instruction not found"}), 404

    if not instruction.image_filename:
        return jsonify({"error": "No image to remove"}), 400

    try:
        # Clean up Cloudinary image if it exists
        if instruction.cloudinary_public_id:
            try:
                cloudinary_service.delete_image(instruction.cloudinary_public_id)
            except Exception as e:
                current_app.logger.warning(f"Failed to delete Cloudinary image: {e}")

        # Clear image fields
        instruction.image_filename = None
        instruction.image_url = None
        instruction.cloudinary_public_id = None
        instruction.cloudinary_url = None
        instruction.cloudinary_thumbnail_url = None

        db.session.commit()

        return jsonify(
            {
                "message": "Instruction image removed successfully",
                "instruction": instruction.to_dict(),
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing instruction image: {e}")
        return jsonify({"error": "Failed to remove image"}), 500


# =============================================================================
# Video Recipe Import Endpoints
# =============================================================================

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "avi"}
ALLOWED_VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
}


def allowed_video_file(filename: str) -> bool:
    """Check if a video file has an allowed extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS
    )


@bp.route("/recipes/upload-video", methods=["POST"])
@require_auth
@rate_limit_upload
def upload_recipe_video(current_user) -> Tuple[Response, int]:
    """
    Upload a video file for recipe extraction.

    Accepts video uploads (MP4, MOV, WebM), creates a VideoProcessingJob,
    and queues async processing via Celery.
    """
    from app.models.video_job import VideoProcessingJob, VideoProcessingStatus

    current_app.logger.info(
        f"Video recipe upload request from user {current_user.id} ({current_user.username})"
    )

    try:
        # Check upload limit for free users
        subscription = current_user.get_or_create_subscription()
        if not current_user.can_upload_recipe():
            current_app.logger.warning(
                f"User {current_user.id} ({current_user.username}) reached upload limit"
            )
            return jsonify(
                {
                    "error": "Upload limit reached",
                    "message": f"You've used all {subscription.monthly_upload_count} of your free uploads this month. Upgrade to Premium for unlimited uploads.",
                    "remaining_uploads": 0,
                    "upgrade_required": True,
                }
            ), 403

        # Check for video file in request
        if "video" not in request.files:
            return jsonify({"error": "No video file provided"}), 400

        video_file = request.files["video"]
        if not video_file or video_file.filename == "":
            return jsonify({"error": "No video file selected"}), 400

        # Validate file extension
        if not allowed_video_file(video_file.filename):
            return jsonify(
                {
                    "error": f"Invalid video format. Supported formats: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
                }
            ), 400

        # Validate content type
        content_type = video_file.content_type or ""
        if content_type and content_type not in ALLOWED_VIDEO_CONTENT_TYPES:
            current_app.logger.warning(f"Invalid video content type: {content_type}")
            return jsonify(
                {"error": f"Invalid video content type: {content_type}"}
            ), 400

        # Check file size
        video_file.seek(0, 2)  # Seek to end
        file_size = video_file.tell()
        video_file.seek(0)  # Reset to beginning

        max_size_mb = current_app.config.get("VIDEO_MAX_SIZE_MB", 100)
        max_size_bytes = max_size_mb * 1024 * 1024

        if file_size > max_size_bytes:
            return jsonify(
                {
                    "error": f"Video too large. Maximum size: {max_size_mb}MB, your file: {file_size / (1024 * 1024):.1f}MB"
                }
            ), 400

        # Get optional parameters
        cookbook_id = request.form.get("cookbook_id", type=int)
        is_original_recipe = (
            request.form.get("is_original_recipe", "false").lower() == "true"
        )
        translate_to_english = (
            request.form.get("translate_to_english", "false").lower() == "true"
        )

        # Handle cookbook creation if requested
        create_new_cookbook = (
            request.form.get("create_new_cookbook", "false").lower() == "true"
        )
        if create_new_cookbook:
            new_cookbook_title = request.form.get("new_cookbook_title", "").strip()
            if not new_cookbook_title:
                return jsonify(
                    {"error": "Cookbook title required when creating new cookbook"}
                ), 400

            cookbook = Cookbook(
                title=new_cookbook_title,
                author=request.form.get("new_cookbook_author", "").strip() or None,
                description=request.form.get("new_cookbook_description", "").strip()
                or None,
                publisher=request.form.get("new_cookbook_publisher", "").strip()
                or None,
                isbn=request.form.get("new_cookbook_isbn", "").strip() or None,
                user_id=current_user.id,
            )
            db.session.add(cookbook)
            db.session.flush()
            cookbook_id = cookbook.id

        # Upload video to Cloudinary for cross-service access
        import cloudinary
        import cloudinary.uploader

        original_filename = secure_filename(video_file.filename)
        video_filename = f"{uuid.uuid4().hex}_{original_filename}"

        current_app.logger.info(
            f"Uploading video to Cloudinary: {video_filename} ({file_size / (1024 * 1024):.1f}MB)"
        )

        # Upload to Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(
                video_file,
                resource_type="video",
                public_id=f"cookle-videos/{video_filename}",
                folder="cookle-videos",
            )
            cloudinary_url = upload_result.get("secure_url")
            cloudinary_public_id = upload_result.get("public_id")
            current_app.logger.info(
                f"Video uploaded to Cloudinary: {cloudinary_public_id}"
            )
        except Exception as cloud_err:
            current_app.logger.error(f"Cloudinary upload failed: {str(cloud_err)}")
            return jsonify({"error": f"Failed to upload video: {str(cloud_err)}"}), 500

        # Create VideoProcessingJob
        video_job = VideoProcessingJob(
            user_id=current_user.id,
            video_filename=video_filename,
            video_original_filename=original_filename,
            video_path=None,  # No local path - using Cloudinary
            video_size_bytes=file_size,
            video_content_type=content_type or "video/mp4",
            cloudinary_public_id=cloudinary_public_id,
            cloudinary_url=cloudinary_url,
            status=VideoProcessingStatus.PENDING,
            progress_message="Queued for processing",
            progress_percentage=0,
            is_original_recipe=is_original_recipe,
            translate_to_english=translate_to_english,
            cookbook_id=cookbook_id,
        )

        db.session.add(video_job)
        db.session.commit()

        current_app.logger.info(
            f"Created VideoProcessingJob {video_job.id} for user {current_user.id}"
        )

        # Queue Celery task
        from app.tasks.recipe_tasks import process_video_recipe_task

        process_video_recipe_task.delay(video_job.id)

        return jsonify(
            {
                "message": "Video uploaded successfully. Processing will begin shortly.",
                "video_job_id": video_job.id,
                "status": video_job.status.value,
            }
        ), 202

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Video upload error: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Video upload failed: {str(e)}"}), 500


@bp.route("/recipes/video-job-status/<int:job_id>", methods=["GET"])
@require_auth
def get_video_job_status(current_user, job_id: int) -> Tuple[Response, int]:
    """
    Get the status of a video processing job.

    Returns detailed progress information including current step,
    progress percentage, and the resulting recipe when complete.
    """
    from app.models.video_job import VideoProcessingJob, VideoProcessingStatus

    try:
        # Find the video job belonging to this user
        video_job = VideoProcessingJob.query.filter_by(
            id=job_id, user_id=current_user.id
        ).first()

        if not video_job:
            return jsonify({"error": "Video processing job not found"}), 404

        response_data = video_job.to_dict()

        # If completed and recipe created, include recipe info
        if video_job.status == VideoProcessingStatus.COMPLETED and video_job.recipe_id:
            recipe = Recipe.query.get(video_job.recipe_id)
            if recipe:
                response_data["recipe"] = recipe.to_dict(
                    current_user_id=current_user.id, is_admin=False
                )

        return jsonify(response_data), 200

    except Exception as e:
        current_app.logger.error(f"Error getting video job status: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Failed to get job status"}), 500


@bp.route("/recipes/job/<int:job_id>/cancel", methods=["POST"])
@require_auth
def cancel_processing_job(current_user, job_id: int) -> Tuple[Response, int]:
    """
    Cancel a single-image recipe processing job.

    Only jobs in PENDING or PROCESSING state can be cancelled.
    """
    try:
        job = ProcessingJob.query.filter_by(
            id=job_id, user_id=current_user.id
        ).first()

        if not job:
            return jsonify({"error": "Processing job not found"}), 404

        # Check if job can be cancelled
        if job.status not in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]:
            return jsonify({
                "error": f"Cannot cancel job with status: {job.status.value}"
            }), 400

        # Mark as cancelled
        job.status = ProcessingStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        db.session.commit()

        current_app.logger.info(f"Processing job {job_id} cancelled by user {current_user.id}")

        return jsonify({"message": "Job cancelled successfully", "status": "cancelled"}), 200

    except Exception as e:
        current_app.logger.error(f"Error cancelling processing job: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to cancel job"}), 500


@bp.route("/recipes/multi-job/<int:job_id>/cancel", methods=["POST"])
@require_auth
def cancel_multi_job(current_user, job_id: int) -> Tuple[Response, int]:
    """
    Cancel a multi-image recipe processing job.

    Cancels the parent job and all child processing jobs.
    Only jobs in PENDING or PROCESSING state can be cancelled.
    """
    try:
        multi_job = MultiRecipeJob.query.filter_by(
            id=job_id, user_id=current_user.id
        ).first()

        if not multi_job:
            return jsonify({"error": "Multi-recipe job not found"}), 404

        # Check if job can be cancelled
        if multi_job.status not in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]:
            return jsonify({
                "error": f"Cannot cancel job with status: {multi_job.status.value}"
            }), 400

        # Mark parent job as cancelled
        multi_job.status = ProcessingStatus.CANCELLED
        multi_job.completed_at = datetime.utcnow()

        # Cancel all child processing jobs that are still pending/processing
        child_jobs = ProcessingJob.query.filter_by(multi_job_id=job_id).all()
        for child in child_jobs:
            if child.status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]:
                child.status = ProcessingStatus.CANCELLED
                child.completed_at = datetime.utcnow()

        db.session.commit()

        current_app.logger.info(f"Multi-recipe job {job_id} cancelled by user {current_user.id}")

        return jsonify({"message": "Job cancelled successfully", "status": "cancelled"}), 200

    except Exception as e:
        current_app.logger.error(f"Error cancelling multi-recipe job: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to cancel job"}), 500


@bp.route("/recipes/video-job/<int:job_id>/cancel", methods=["POST"])
@require_auth
def cancel_video_job(current_user, job_id: int) -> Tuple[Response, int]:
    """
    Cancel a video recipe processing job.

    Only jobs that haven't completed or failed can be cancelled.
    """
    from app.models.video_job import VideoProcessingJob, VideoProcessingStatus

    try:
        video_job = VideoProcessingJob.query.filter_by(
            id=job_id, user_id=current_user.id
        ).first()

        if not video_job:
            return jsonify({"error": "Video processing job not found"}), 404

        # Check if job can be cancelled (not already completed or failed)
        terminal_states = [
            VideoProcessingStatus.COMPLETED,
            VideoProcessingStatus.FAILED,
            VideoProcessingStatus.CANCELLED
        ]
        if video_job.status in terminal_states:
            return jsonify({
                "error": f"Cannot cancel job with status: {video_job.status.value}"
            }), 400

        # Mark as cancelled
        video_job.status = VideoProcessingStatus.CANCELLED
        video_job.progress_message = "Cancelled by user"
        video_job.completed_at = datetime.utcnow()
        db.session.commit()

        current_app.logger.info(f"Video job {job_id} cancelled by user {current_user.id}")

        return jsonify({"message": "Job cancelled successfully", "status": "cancelled"}), 200

    except Exception as e:
        current_app.logger.error(f"Error cancelling video job: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to cancel job"}), 500


@bp.route("/recipes/upload-youtube", methods=["POST"])
@require_auth
@rate_limit_upload
def upload_recipe_youtube(current_user) -> Tuple[Response, int]:
    """
    Import a recipe from a YouTube video URL.

    Accepts JSON with a YouTube URL, creates a VideoProcessingJob,
    and queues async processing via Celery (yt-dlp + captions/audio).
    """
    from app.models.video_job import VideoProcessingJob, VideoProcessingStatus
    from app.services.youtube_recipe_service import (
        YouTubeRecipeService,
        YouTubeValidationError,
    )

    current_app.logger.info(
        f"YouTube recipe import request from user {current_user.id} "
        f"({current_user.username})"
    )

    try:
        # Check upload limit for free users
        subscription = current_user.get_or_create_subscription()
        if not current_user.can_upload_recipe():
            current_app.logger.warning(
                f"User {current_user.id} ({current_user.username}) reached upload limit"
            )
            return jsonify(
                {
                    "error": "Upload limit reached",
                    "message": (
                        f"You've used all {subscription.monthly_upload_count} "
                        f"of your free uploads this month. "
                        f"Upgrade to Premium for unlimited uploads."
                    ),
                    "remaining_uploads": 0,
                    "upgrade_required": True,
                }
            ), 403

        # Parse JSON body
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "YouTube URL is required"}), 400

        # Validate URL and extract video ID
        try:
            video_id = YouTubeRecipeService.validate_and_extract_video_id(url)
        except YouTubeValidationError as e:
            return jsonify({"error": str(e)}), 400

        # Get optional parameters
        cookbook_id = data.get("cookbook_id")
        if cookbook_id is not None:
            cookbook_id = int(cookbook_id)
        translate_to_english = bool(data.get("translate_to_english", False))
        is_original_recipe = bool(data.get("is_original_recipe", False))

        # Handle cookbook creation if requested
        create_new_cookbook = bool(data.get("create_new_cookbook", False))
        if create_new_cookbook:
            new_cookbook_title = (data.get("new_cookbook_title") or "").strip()
            if not new_cookbook_title:
                return jsonify(
                    {"error": "Cookbook title required when creating new cookbook"}
                ), 400

            cookbook = Cookbook(
                title=new_cookbook_title,
                author=(data.get("new_cookbook_author") or "").strip() or None,
                description=(
                    (data.get("new_cookbook_description") or "").strip() or None
                ),
                publisher=((data.get("new_cookbook_publisher") or "").strip() or None),
                isbn=(data.get("new_cookbook_isbn") or "").strip() or None,
                user_id=current_user.id,
            )
            db.session.add(cookbook)
            db.session.flush()
            cookbook_id = cookbook.id

        # Create VideoProcessingJob with synthetic file values for YouTube
        video_job = VideoProcessingJob(
            user_id=current_user.id,
            video_filename=f"youtube_{video_id}",
            video_original_filename=f"youtube_{video_id}",
            video_path="youtube",
            video_size_bytes=0,
            video_content_type="video/youtube",
            status=VideoProcessingStatus.PENDING,
            progress_message="Queued for processing",
            progress_percentage=0,
            is_original_recipe=is_original_recipe,
            translate_to_english=translate_to_english,
            cookbook_id=cookbook_id,
            youtube_url=url,
            youtube_video_id=video_id,
        )

        db.session.add(video_job)
        db.session.commit()

        current_app.logger.info(
            f"Created YouTube VideoProcessingJob {video_job.id} "
            f"for video {video_id}, user {current_user.id}"
        )

        # Queue Celery task
        from app.tasks.recipe_tasks import process_youtube_recipe_task

        process_youtube_recipe_task.delay(video_job.id)

        return jsonify(
            {
                "message": "YouTube video queued for processing.",
                "video_job_id": video_job.id,
                "status": video_job.status.value,
            }
        ), 202

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"YouTube upload error: {str(e)}\nTraceback: {traceback.format_exc()}"
        )
        return jsonify({"error": f"YouTube import failed: {str(e)}"}), 500

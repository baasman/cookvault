import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

from flask import Response, current_app, jsonify, request, send_file
from sqlalchemy import text
from werkzeug.utils import secure_filename

from app import db
from app.api import bp
from app.api.auth import require_auth, optional_auth, should_apply_user_filter
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
from app.services.ocr_service import OCRService
from app.services.recipe_parser import RecipeParser
from app.services.cloudinary_service import cloudinary_service
import requests

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tiff"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_and_save_image(file, original_filename: str, folder: str = "recipes") -> RecipeImage:
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
                file_data, 
                original_filename, 
                folder=folder,
                generate_thumbnail=True
            )
            
            # Store Cloudinary information
            recipe_image.cloudinary_public_id = cloudinary_result['public_id']
            recipe_image.cloudinary_url = cloudinary_result['url']
            recipe_image.cloudinary_thumbnail_url = cloudinary_result.get('thumbnail_url')
            recipe_image.cloudinary_width = cloudinary_result['width']
            recipe_image.cloudinary_height = cloudinary_result['height']
            recipe_image.cloudinary_format = cloudinary_result['format']
            recipe_image.cloudinary_bytes = cloudinary_result['bytes']
            
            # For Cloudinary images, we don't need local file path
            recipe_image.file_path = f"cloudinary:{cloudinary_result['public_id']}"
            
            current_app.logger.info(f"Successfully uploaded to Cloudinary: {cloudinary_result['public_id']}")
            
        except Exception as e:
            current_app.logger.error(f"Cloudinary upload failed, falling back to local storage: {str(e)}")
            # Fall through to local storage
    
    # Local storage fallback (or primary if Cloudinary not enabled)
    if not recipe_image.cloudinary_public_id:
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        file_path = upload_folder / filename
        
        # Save file locally
        with open(file_path, 'wb') as f:
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
    if recipe_image.file_path.startswith('cloudinary:'):
        if not recipe_image.cloudinary_url:
            raise Exception("Cloudinary image has no URL")
        
        current_app.logger.info(f"Downloading Cloudinary image for OCR: {recipe_image.cloudinary_url}")
        
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
        range_match = re.search(r'(\d+)\s*(?:[-–—]|to)\s*(\d+)', value_str)
        if range_match:
            start_val = int(range_match.group(1))
            end_val = int(range_match.group(2))
            # Take the average of the range, rounded down
            result = (start_val + end_val) // 2
            current_app.logger.info(f"Converted range '{value_str}' to {result} for servings field")
            return result
        
        # Look for single numbers (ignoring text like "servings", "minutes", etc.)
        number_match = re.search(r'(\d+)', value_str)
        if number_match:
            result = int(number_match.group(1))
            current_app.logger.debug(f"Extracted number {result} from '{value_str}' for servings field")
            return result

    try:
        return int(value)
    except (ValueError, TypeError):
        current_app.logger.warning(f"Could not convert '{value}' to integer for servings field")
        return None


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
            # Only user's own uploaded recipes
            query = query.filter(Recipe.user_id == current_user.id)
        elif filter_type == "collection":
            # Only recipes in user's collection (both own and added from others)
            # Include recipes that are either:
            # 1. Owned by the user (uploaded by them)
            # 2. Explicitly added to their collection via UserRecipeCollection
            user_recipe_ids_subquery = (
                db.session.query(UserRecipeCollection.recipe_id)
                .filter(UserRecipeCollection.user_id == current_user.id)
                .subquery()
            )

            query = query.filter(
                db.or_(
                    Recipe.user_id == current_user.id,  # User's own recipes
                    Recipe.id.in_(
                        user_recipe_ids_subquery
                    ),  # Explicitly collected recipes
                )
            )
        elif filter_type == "discover":
            # All public recipes from other users (for discovery)
            query = query.filter(
                Recipe.is_public == True,
                Recipe.user_id != current_user.id,  # Exclude user's own recipes
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
            query = query.filter(Recipe.user_id == current_user.id)
        elif filter_type == "collection":
            # For admins, collection filter shows all recipes (could be refined)
            pass  # No additional filter needed
        elif filter_type == "discover":
            # All public recipes (for discovery)
            query = query.filter(Recipe.is_public == True)
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

    if search:
        query = query.filter(
            db.or_(
                Recipe.title.ilike(f"%{search}%"),
                Recipe.description.ilike(f"%{search}%"),
            )
        )

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
            all_public = Recipe.query.filter(Recipe.is_public == True).all()
            public_debug = [(r.id, r.title, r.user_id, r.is_public) for r in all_public]
            current_app.logger.info(f"All public recipes in database: {public_debug}")

    return jsonify(
        {
            "recipes": [
                recipe.to_dict(current_user_id=current_user.id, is_admin=not should_apply_user_filter(current_user))
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
def create_empty_recipe(current_user) -> Response:
    """Create a new empty recipe."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        title = data.get("title", "").strip()
        if not title:
            return jsonify({"error": "Recipe title is required"}), 400

        cookbook_id = data.get("cookbook_id")

        # Validate cookbook ownership if cookbook_id is provided
        if cookbook_id:
            cookbook = Cookbook.query.filter_by(
                id=cookbook_id, user_id=current_user.id
            ).first()
            if not cookbook:
                return jsonify({"error": "Cookbook not found or access denied"}), 404

        # Create new recipe
        recipe = Recipe(
            title=title,
            user_id=current_user.id,
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
@require_auth
def get_recipe(current_user, recipe_id: int) -> Response:
    # Check if recipe exists and user can access it
    recipe = Recipe.query.options(db.joinedload(Recipe.images)).get(recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    # Check access permissions: owner, admin, or public recipe
    is_admin = not should_apply_user_filter(current_user)
    can_view = recipe.can_be_viewed_by(current_user.id, is_admin)

    if not can_view:
        return jsonify({"error": "Recipe not found or access denied"}), 404

    return jsonify(recipe.to_dict(include_user=True, current_user_id=current_user.id, is_admin=is_admin))


@bp.route("/recipes/<int:recipe_id>", methods=["DELETE"])
@require_auth
def delete_recipe(current_user, recipe_id: int) -> Response:
    """Delete a recipe and all associated data."""
    try:
        # Get the recipe and verify ownership/permissions
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404

        # Check if user can delete this recipe (only owner or admin)
        is_admin = not should_apply_user_filter(current_user)
        if not is_admin and recipe.user_id != current_user.id:
            return jsonify({"error": "Access denied"}), 403

        current_app.logger.info(f"Deleting recipe {recipe_id} by user {current_user.id}")

        # Delete associated images from Cloudinary and local storage
        for image in recipe.images:
            try:
                # Delete from Cloudinary if exists
                if image.cloudinary_public_id and cloudinary_service.is_enabled():
                    cloudinary_service.delete_image(image.cloudinary_public_id)
                    current_app.logger.info(f"Deleted Cloudinary image: {image.cloudinary_public_id}")
                
                # Delete local file if exists
                if image.file_path:
                    file_path = Path(image.file_path)
                    if file_path.exists():
                        file_path.unlink()
                        current_app.logger.info(f"Deleted local image file: {file_path}")
                
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


@bp.route("/recipes/upload", methods=["POST"])
@require_auth
def upload_recipe(current_user) -> Tuple[Response, int]:
    """Upload a recipe image and process it into a recipe."""
    current_app.logger.info(
        f"Recipe upload request from user {current_user.id} ({current_user.username})"
    )
    current_app.logger.info(f"Request headers: {dict(request.headers)}")
    current_app.logger.info(f"Form data keys: {list(request.form.keys())}")
    current_app.logger.info(f"Files: {list(request.files.keys())}")

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
    page_number = request.form.get("page_number")
    create_new_cookbook = request.form.get("create_new_cookbook") == "true"

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
        except ValueError:
            return jsonify({"error": "Invalid cookbook_id"}), 400

    # Validate page_number if provided
    if page_number:
        try:
            page_number = int(page_number)
        except ValueError:
            return jsonify({"error": "Invalid page_number"}), 400

    try:
        # Use the new helper function to handle image processing
        recipe_image = process_and_save_image(file, file.filename, folder="recipes")
        
        db.session.add(recipe_image)
        db.session.flush()

        processing_job = ProcessingJob(
            image_id=recipe_image.id,
            cookbook_id=cookbook_id,
            page_number=page_number,
        )

        db.session.add(processing_job)
        db.session.commit()

        # Queue background processing to prevent worker timeouts
        import threading

        current_app.logger.info(
            f"Starting background processing for job {processing_job.id}"
        )

        # Capture Flask app object and user ID for background thread
        app = current_app._get_current_object()
        user_id = current_user.id

        # Process in background thread to return immediately to user
        def background_process():
            # Use application context in background thread
            with app.app_context():
                try:
                    _process_recipe_image(processing_job.id, user_id)
                    app.logger.info(
                        f"Background processing completed for job {processing_job.id}"
                    )
                except Exception as e:
                    app.logger.error(
                        f"Background processing failed for job {processing_job.id}: {str(e)}"
                    )
                    # Update job status to failed
                    try:
                        job = ProcessingJob.query.get(processing_job.id)
                        if job:
                            job.status = ProcessingStatus.FAILED
                            job.error_message = str(e)
                            db.session.commit()
                    except Exception as db_error:
                        app.logger.error(
                            f"Failed to update job status: {str(db_error)}"
                        )

        # Start background processing
        thread = threading.Thread(target=background_process)
        thread.daemon = True  # Thread will die when main process dies
        thread.start()

        return (
            jsonify(
                {
                    "message": "Image uploaded successfully. Recipe extraction is processing in the background.",
                    "job_id": processing_job.id,
                    "image_id": recipe_image.id,
                    "image": recipe_image.to_dict(),  # Include image data for immediate preview
                    "cookbook": cookbook.to_dict() if cookbook else None,
                    "page_number": page_number,
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
            recipe.prep_time = safe_int_conversion(data["prep_time"]) if data["prep_time"] else None

        if "cook_time" in data:
            recipe.cook_time = safe_int_conversion(data["cook_time"]) if data["cook_time"] else None

        if "servings" in data:
            recipe.servings = safe_int_conversion(data["servings"]) if data["servings"] else None

        if "difficulty" in data:
            recipe.difficulty = data["difficulty"] if data["difficulty"] else None

        db.session.commit()
        current_app.logger.info(f"Recipe {recipe_id} updated by user {current_user.id}")

        return jsonify(
            {"message": "Recipe updated successfully", "recipe": recipe.to_dict()}
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Recipe update failed for recipe {recipe_id}: {str(e)}"
        )
        return jsonify({"error": "Recipe update failed"}), 500


@bp.route("/recipes/<int:recipe_id>/ingredients", methods=["PUT"])
@require_auth
def update_recipe_ingredients(current_user, recipe_id: int) -> Response:
    """Update recipe ingredients list."""

    # Verify recipe exists and user has permission
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
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

        return jsonify(
            {"message": "Ingredients updated successfully", "recipe": recipe.to_dict()}
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

    # Verify recipe exists and user has permission
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
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

        # Remove existing instructions
        Instruction.query.filter_by(recipe_id=recipe_id).delete()

        # Add new instructions
        for step_number, instruction_text in enumerate(instructions_data, 1):
            if not isinstance(instruction_text, str):
                return jsonify({"error": "Invalid instruction data"}), 400

            instruction_text = instruction_text.strip()
            if not instruction_text:
                return jsonify({"error": "Instruction text cannot be empty"}), 400

            instruction = Instruction(
                recipe_id=recipe_id, step_number=step_number, text=instruction_text
            )
            db.session.add(instruction)

        db.session.commit()
        current_app.logger.info(
            f"Instructions updated for recipe {recipe_id} by user {current_user.id}"
        )

        return jsonify(
            {"message": "Instructions updated successfully", "recipe": recipe.to_dict()}
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

    # Verify recipe exists and user has permission
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
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

        return jsonify(
            {"message": "Tags updated successfully", "recipe": recipe.to_dict()}
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


@bp.route("/jobs/<int:job_id>", methods=["GET"])
@require_auth
def get_processing_job(current_user, job_id: int):
    job = ProcessingJob.query.get_or_404(job_id)
    # Verify job belongs to user (through cookbook ownership or direct ownership)
    if job.cookbook_id:
        cookbook = Cookbook.query.filter_by(
            id=job.cookbook_id, user_id=current_user.id
        ).first()
        if not cookbook:
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
                    can_access = (
                        recipe.user_id == current_user.id
                        or (hasattr(current_user, 'role') and current_user.role == UserRole.ADMIN)
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
                        RecipeGroup.user_id == current_user.id
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
                has_public_recipes = Recipe.query.filter_by(
                    cookbook_id=cookbook.id,
                    is_public=True
                ).first() is not None
                
                if has_public_recipes:
                    # Cookbook with public recipes is accessible to everyone
                    can_access = True
                elif current_user:
                    # Private cookbooks only accessible to owner or admin
                    can_access = (
                        cookbook.user_id == current_user.id
                        or (hasattr(current_user, 'role') and current_user.role == UserRole.ADMIN)
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

        # Single LLM call for both extraction and parsing - with timeout monitoring
        import time

        start_time = time.time()

        try:
            comprehensive_result = llm_ocr_service.extract_and_parse_recipe(image_data, source_info)
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
        current_app.logger.error(f"Processing failed for job {job_id}: {str(e)}", exc_info=True)
        
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
                current_app.logger.error(f"Could not find job {job_id} to update status")
                
        except Exception as rollback_error:
            current_app.logger.error(f"Failed to rollback and update job status: {str(rollback_error)}", exc_info=True)
            # As a last resort, try to create a new session
            try:
                from app import db as fresh_db
                fresh_db.session.rollback()
                fresh_db.session.close()
                current_app.logger.info("Created fresh database session after rollback failure")
            except Exception as fresh_error:
                current_app.logger.critical(f"Complete database session failure: {str(fresh_error)}")


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


def _generate_recipe_title(parsed_recipe: Dict[str, Any], extracted_text: str, job: ProcessingJob) -> str:
    """Generate a robust title with smart fallbacks to ensure never null."""
    # Try to get title from parsed recipe
    title = parsed_recipe.get("title")
    if title and title.strip():
        current_app.logger.info(f"Using parsed title: {title}")
        return title.strip()
    
    # Fallback 1: Extract first line/sentence from extracted text
    if extracted_text and extracted_text.strip():
        lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
        if lines:
            # Take first non-empty line, limit to reasonable title length
            first_line = lines[0][:100]  # Limit to 100 characters
            current_app.logger.warning(f"Title was null, using first line as fallback: {first_line}")
            return first_line
    
    # Fallback 2: Try to get filename from job's associated image
    try:
        if job and job.images:
            image = job.images[0]  # Get first image
            filename = image.original_filename
            if filename:
                # Remove extension and create readable title
                name_without_ext = filename.rsplit('.', 1)[0]
                title = f"Recipe from {name_without_ext}"
                current_app.logger.warning(f"Using filename-based fallback: {title}")
                return title
    except (AttributeError, IndexError):
        pass
    
    # Fallback 3: Use timestamp-based title
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"Recipe from {timestamp}"
    current_app.logger.error(f"All title extraction failed, using timestamp fallback: {title}")
    return title


def _create_recipe_from_parsed_data(
    parsed_recipe: Dict[str, Any],
    extracted_text: str,
    job: ProcessingJob,
    upload_user_id: int = None,
) -> Recipe:
    """Create recipe and all related records from parsed data."""
    # Get user_id from cookbook if it exists, otherwise use the upload user_id
    user_id = upload_user_id  # Default to the user who uploaded the image
    if job.cookbook_id:
        cookbook = Cookbook.query.get(job.cookbook_id)
        if cookbook:
            user_id = cookbook.user_id

    # Generate robust title with smart fallbacks
    title = _generate_recipe_title(parsed_recipe, extracted_text, job)
    
    # Create base recipe
    recipe = Recipe(
        title=title,
        description=parsed_recipe.get("description"),
        cookbook_id=job.cookbook_id,
        page_number=job.page_number,
        prep_time=safe_int_conversion(parsed_recipe.get("prep_time")),
        cook_time=safe_int_conversion(parsed_recipe.get("cook_time")),
        servings=safe_int_conversion(parsed_recipe.get("servings")),
        difficulty=parsed_recipe.get("difficulty"),
        user_id=user_id,
        is_public=False,  # New recipes are private by default
    )

    db.session.add(recipe)
    db.session.flush()

    # Create related records
    _create_instructions(recipe.id, parsed_recipe, extracted_text)
    _create_tags(recipe.id, parsed_recipe)
    _create_ingredients(recipe.id, parsed_recipe)

    return recipe


def _create_instructions(
    recipe_id: int, parsed_recipe: Dict[str, Any], fallback_text: str
) -> None:
    """Create instruction records for the recipe."""
    instructions = parsed_recipe.get("instructions", [])
    if isinstance(instructions, str):
        instructions = [instructions]
    elif not isinstance(instructions, list):
        instructions = [fallback_text]

    for i, instruction_text in enumerate(instructions, 1):
        instruction = Instruction(
            recipe_id=recipe_id, step_number=i, text=instruction_text.strip()
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

        except Exception as e:
            current_app.logger.error(f"Failed to create ingredient {order}: {str(e)}")
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

        return jsonify({"message": message, "recipe": recipe.to_dict(current_user_id=current_user.id, is_admin=not should_apply_user_filter(current_user))})

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
        Recipe.is_public == True, Recipe.user_id != current_user.id
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

    # Order by publication date (newest first)
    query = query.order_by(Recipe.published_at.desc())

    recipes = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "recipes": [
                recipe.to_dict(include_user=True, current_user_id=current_user.id, is_admin=not should_apply_user_filter(current_user))
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

    if not recipe.can_be_viewed_by(current_user.id, current_user.role == "admin"):
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

    # Only recipe owners can create/edit notes
    if recipe.user_id != current_user.id:
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

    # Only recipe owners can delete notes
    if recipe.user_id != current_user.id:
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


# Recipe Comments Endpoints


@bp.route("/recipes/<int:recipe_id>/comments", methods=["GET"])
@require_auth
def get_recipe_comments(current_user, recipe_id: int) -> Response:
    """Get paginated comments for a recipe."""
    # Check if recipe exists and user can view it
    recipe = Recipe.query.get_or_404(recipe_id)

    if not recipe.can_be_viewed_by(current_user.id, current_user.role == "admin"):
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

    if not recipe.can_be_viewed_by(current_user.id, current_user.role == "admin"):
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

    if not recipe.can_be_viewed_by(current_user.id, current_user.role == "admin"):
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

    if not recipe.can_be_viewed_by(current_user.id, current_user.role == "admin"):
        return jsonify({"error": "Recipe not found"}), 404

    # Get the comment
    comment = RecipeComment.query.filter_by(id=comment_id, recipe_id=recipe_id).first()

    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    # Only comment author or admin can delete comment
    is_admin = current_user.role == "admin"
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
            is_public=False,  # Copied recipes are private by default
            cookbook_id=None,  # Remove cookbook association
            page_number=None,  # Remove page number
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
def upload_multi_recipe(current_user):
    """Upload multiple images for a single recipe"""
    try:
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
                return jsonify({"error": f"Image {i+1} has no filename"}), 400

            if not allowed_file(file.filename):
                return (
                    jsonify(
                        {
                            "error": f"Image {i+1} has invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
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
                        "error": f"Total file size exceeds {max_total_size // (1024*1024)}MB limit"
                    }
                ),
                400,
            )

        # Get optional cookbook information
        cookbook_id = request.form.get("cookbook_id")
        page_number = safe_int_conversion(request.form.get("page_number"))

        # Validate cookbook if provided
        cookbook = None
        if cookbook_id:
            try:
                cookbook_id = int(cookbook_id)
                cookbook = Cookbook.query.filter_by(
                    id=cookbook_id, user_id=user_id
                ).first()
                if not cookbook:
                    return jsonify({"error": "Cookbook not found"}), 404
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid cookbook ID"}), 400

        # Create MultiRecipeJob
        multi_job = MultiRecipeJob(
            user_id=user_id,
            total_images=len(validated_files),
            status=ProcessingStatus.PENDING,
        )
        db.session.add(multi_job)
        db.session.flush()  # Get the ID

        # Save images and create processing jobs
        processing_jobs = []

        for i, (file, file_size) in enumerate(validated_files):
            # Use the same image processing function as single upload (includes Cloudinary)
            file.seek(0)  # Reset file pointer
            recipe_image = process_and_save_image(file, file.filename, folder="recipes/multi")
            
            # Set multi-image specific fields
            recipe_image.image_order = i  # Set order based on upload sequence
            recipe_image.page_number = page_number + i if page_number else i + 1
            
            db.session.add(recipe_image)
            db.session.flush()  # Get the ID

            # Create processing job
            processing_job = ProcessingJob(
                image_id=recipe_image.id,
                cookbook_id=cookbook_id,
                page_number=recipe_image.page_number,
                is_multi_image=True,
                multi_job_id=multi_job.id,
                image_order=i,
                status=ProcessingStatus.PENDING,
            )
            db.session.add(processing_job)
            processing_jobs.append(processing_job)

        db.session.commit()

        # Start processing
        try:
            process_multi_image_job(multi_job.id)
        except Exception as e:
            current_app.logger.error(
                f"Error starting multi-image processing for job {multi_job.id}: {e}"
            )
            multi_job.status = ProcessingStatus.FAILED
            multi_job.error_message = f"Failed to start processing: {str(e)}"
            db.session.commit()

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
        page_number = data.get("page_number")
        create_new_cookbook = data.get("create_new_cookbook", False)

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
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid cookbook_id"}), 400

        # Validate page_number if provided
        if page_number:
            try:
                page_number = int(page_number)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid page_number"}), 400

        # Process the text directly using the recipe parser
        recipe_parser = RecipeParser()
        parsed_recipe = recipe_parser.parse_recipe_text(recipe_text)

        current_app.logger.info(f"Parsed recipe: {parsed_recipe}")

        # Create the recipe directly (no background processing needed for text)
        recipe = Recipe(
            title=parsed_recipe.get("title", "Untitled Recipe"),
            description=parsed_recipe.get("description"),
            cookbook_id=cookbook_id,
            page_number=page_number,
            user_id=current_user.id,
            is_public=False,  # Default to private
            prep_time=safe_int_conversion(parsed_recipe.get("prep_time")),
            cook_time=safe_int_conversion(parsed_recipe.get("cook_time")),
            servings=safe_int_conversion(parsed_recipe.get("servings")),
            difficulty=parsed_recipe.get("difficulty"),
        )

        db.session.add(recipe)
        db.session.flush()  # Get recipe ID

        # Add ingredients
        if parsed_recipe.get("ingredients"):
            _create_ingredients(recipe.id, parsed_recipe)

        # Add instructions
        if parsed_recipe.get("instructions"):
            _create_instructions(recipe.id, parsed_recipe, recipe_text)

        # Add tags
        if parsed_recipe.get("tags"):
            _create_tags(recipe.id, parsed_recipe)

        db.session.commit()

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
                        "page_number": recipe.page_number,
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


@bp.route("/recipes/job-status/<int:job_id>", methods=["GET"])
@require_auth
def get_job_status(current_user, job_id: int):
    """Get the processing status of a single recipe upload job."""
    try:
        job = ProcessingJob.query.get_or_404(job_id)

        # Check if job belongs to the current user or user is admin
        if should_apply_user_filter(current_user):
            can_access = False

            # If job has a recipe, check recipe ownership
            if job.recipe_id:
                recipe = Recipe.query.get(job.recipe_id)
                if recipe and recipe.user_id == current_user.id:
                    can_access = True
            else:
                # For jobs without recipe (pending/processing), check cookbook ownership
                if job.cookbook_id:
                    cookbook = Cookbook.query.get(job.cookbook_id)
                    if cookbook and cookbook.user_id == current_user.id:
                        can_access = True
                else:
                    # For jobs without cookbook (uploaded without cookbook), we check
                    # if the current user uploaded this. Currently relying on job_id being
                    # difficult to guess. Consider adding user_id field to ProcessingJob model
                    # in future migration for better security tracking
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
                response_data["recipe"] = recipe.to_dict(current_user_id=user_id, is_admin=False)

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
                        f"Processing image {i+1}/{len(image_paths)}: {image_path}"
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
                            with open(image_path, 'rb') as f:
                                image_data = f.read()
                            source_info = str(image_path)
                        except Exception as read_error:
                            current_app.logger.error(f"Failed to read local image file {image_path}: {str(read_error)}")
                            raise
                    
                    extracted_text = llm_ocr_service.extract_text_from_image(image_data, source_info)
                    combined_text += f"\n--- Page {i+1} ---\n{extracted_text}\n"
                    successful_extractions += 1

                    # Force garbage collection after each image to free memory
                    import gc

                    gc.collect()

                except Exception as img_error:
                    current_app.logger.error(
                        f"Failed to process image {image_path}: {str(img_error)}"
                    )
                    combined_text += (
                        f"\n--- Page {i+1} (FAILED) ---\n[Error processing image]\n"
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
                    f"Multi-image result missing 'results' key, falling back to combined text processing"
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
                timeout_seconds = 120  # 2 minutes per image

                while retry_count <= max_retries:
                    try:
                        processing_job.status = ProcessingStatus.PROCESSING
                        db.session.commit()

                        # Use threading timeout instead of signal (works in background threads)
                        import threading
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
            current_app.logger.info(f"  Text {i+1}: {len(text)} characters")

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

            parsed_recipe = recipe_parser.parse_multi_image_recipe(
                ocr_texts, quality_info=quality_info
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

            # Get cookbook_id and page_number from processing jobs if available
            cookbook_id = None
            page_number = None
            if successful_jobs:
                cookbook_id = successful_jobs[0].cookbook_id
                page_number = successful_jobs[0].page_number
                current_app.logger.info(
                    f"Setting recipe cookbook_id to: {cookbook_id}, page_number to: {page_number}"
                )

            # Ensure we have a valid title
            recipe_title = parsed_recipe.get("title")
            if not recipe_title or recipe_title.strip() == "":
                recipe_title = "Untitled Recipe"
                current_app.logger.warning(f"Recipe title was empty, using default: {recipe_title}")
            
            # Create the recipe
            recipe = Recipe(
                title=recipe_title,
                description=parsed_recipe.get("description"),
                cookbook_id=cookbook_id,
                page_number=page_number,
                user_id=multi_job.user_id,
                is_public=False,  # Default to private
            )
            db.session.add(recipe)
            db.session.flush()  # Get recipe ID

            # Add ingredients if any
            if parsed_recipe.get("ingredients"):
                _create_ingredients(recipe.id, parsed_recipe)

            # Add instructions if any
            if parsed_recipe.get("instructions"):
                for i, instruction_text in enumerate(parsed_recipe["instructions"]):
                    instruction = Instruction(
                        recipe_id=recipe.id, step_number=i + 1, text=instruction_text
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

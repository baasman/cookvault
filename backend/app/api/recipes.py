import os
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple

from flask import Response, current_app, jsonify, request, send_file
from sqlalchemy import text
from werkzeug.utils import secure_filename

from app import db
from app.api import bp
from app.api.auth import require_auth, should_apply_user_filter
from app.models import (
    Cookbook,
    Ingredient,
    Instruction,
    ProcessingJob,
    ProcessingStatus,
    Recipe,
    RecipeImage,
    Tag,
)
from app.models.recipe import recipe_ingredients
from app.services.ocr_service import OCRService
from app.services.recipe_parser import RecipeParser

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tiff"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/recipes", methods=["GET"])
@require_auth
def get_recipes(current_user) -> Response:
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "")
    cookbook_id = request.args.get("cookbook_id", type=int)

    # Base query - admins see all recipes, users see only their own
    query = Recipe.query.options(db.joinedload(Recipe.images))
    if should_apply_user_filter(current_user):
        query = query.filter_by(user_id=current_user.id)

    # Apply filters
    if cookbook_id:
        query = query.filter_by(cookbook_id=cookbook_id)

    if search:
        query = query.filter(
            db.or_(
                Recipe.title.ilike(f"%{search}%"),
                Recipe.description.ilike(f"%{search}%")
            )
        )

    # Order by creation date (newest first)
    query = query.order_by(Recipe.created_at.desc())

    recipes = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "recipes": [recipe.to_dict() for recipe in recipes.items],
            "total": recipes.total,
            "pages": recipes.pages,
            "current_page": page,
            "per_page": per_page,
            "has_next": recipes.has_next,
            "has_prev": recipes.has_prev
        }
    )


@bp.route("/recipes/<int:recipe_id>", methods=["GET"])
@require_auth
def get_recipe(current_user, recipe_id: int) -> Response:
    # Admin can access any recipe, users only their own
    if should_apply_user_filter(current_user):
        recipe = Recipe.query.options(db.joinedload(Recipe.images)).filter_by(id=recipe_id, user_id=current_user.id).first()
    else:
        recipe = Recipe.query.options(db.joinedload(Recipe.images)).get(recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    return jsonify(recipe.to_dict())


@bp.route("/recipes/upload", methods=["POST"])
@require_auth
def upload_recipe(current_user) -> Tuple[Response, int]:

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

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
            return jsonify({"error": "Cookbook title is required when creating a new cookbook"}), 400
        
        # Create new cookbook
        try:
            from datetime import datetime
            
            cookbook = Cookbook(
                title=new_cookbook_title,
                author=request.form.get("new_cookbook_author", "").strip() or None,
                description=request.form.get("new_cookbook_description", "").strip() or None,
                publisher=request.form.get("new_cookbook_publisher", "").strip() or None,
                isbn=request.form.get("new_cookbook_isbn", "").strip() or None,
                user_id=current_user.id
            )
            
            # Handle publication date if provided
            publication_date = request.form.get("new_cookbook_publication_date", "").strip()
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
        filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        file_path = upload_folder / filename

        file.save(file_path)

        recipe_image = RecipeImage(
            filename=filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            content_type=file.content_type or "image/jpeg",
        )

        db.session.add(recipe_image)
        db.session.flush()

        processing_job = ProcessingJob(
            image_id=recipe_image.id,
            cookbook_id=cookbook_id,
            page_number=page_number,
        )

        db.session.add(processing_job)
        db.session.commit()

        # TODO: Queue background processing job
        # For now, process synchronously
        _process_recipe_image(processing_job.id)

        return (
            jsonify(
                {
                    "message": "Image uploaded successfully",
                    "job_id": processing_job.id,
                    "image_id": recipe_image.id,
                    "cookbook": cookbook.to_dict() if cookbook else None,
                    "page_number": page_number,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Upload failed: {str(e)}")
        return jsonify({"error": "Upload failed"}), 500


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
            recipe.prep_time = data["prep_time"] if data["prep_time"] else None

        if "cook_time" in data:
            recipe.cook_time = data["cook_time"] if data["cook_time"] else None

        if "servings" in data:
            recipe.servings = data["servings"] if data["servings"] else None

        if "difficulty" in data:
            recipe.difficulty = data["difficulty"] if data["difficulty"] else None

        db.session.commit()
        current_app.logger.info(f"Recipe {recipe_id} updated by user {current_user.id}")

        return jsonify({
            "message": "Recipe updated successfully",
            "recipe": recipe.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Recipe update failed for recipe {recipe_id}: {str(e)}")
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
                    name=ingredient_name,
                    category=ingredient_data.get("category")
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
        current_app.logger.info(f"Ingredients updated for recipe {recipe_id} by user {current_user.id}")

        return jsonify({
            "message": "Ingredients updated successfully",
            "recipe": recipe.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ingredients update failed for recipe {recipe_id}: {str(e)}")
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
                recipe_id=recipe_id,
                step_number=step_number,
                text=instruction_text
            )
            db.session.add(instruction)

        db.session.commit()
        current_app.logger.info(f"Instructions updated for recipe {recipe_id} by user {current_user.id}")

        return jsonify({
            "message": "Instructions updated successfully",
            "recipe": recipe.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Instructions update failed for recipe {recipe_id}: {str(e)}")
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
        current_app.logger.info(f"Tags updated for recipe {recipe_id} by user {current_user.id}")

        return jsonify({
            "message": "Tags updated successfully",
            "recipe": recipe.to_dict()
        })

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
        # Generate secure filename
        filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        file_path = upload_folder / filename

        # Save the file
        file.save(file_path)

        # Create recipe image record
        recipe_image = RecipeImage(
            recipe_id=recipe.id,
            filename=filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            content_type=file.content_type or "image/jpeg",
        )

        db.session.add(recipe_image)
        db.session.commit()

        current_app.logger.info(f"Image uploaded for recipe {recipe_id} by user {current_user.id}")

        return (
            jsonify(
                {
                    "message": "Image uploaded successfully",
                    "image": {
                        "id": recipe_image.id,
                        "filename": recipe_image.filename,
                        "original_filename": recipe_image.original_filename,
                        "file_size": recipe_image.file_size,
                        "content_type": recipe_image.content_type,
                        "uploaded_at": recipe_image.uploaded_at.isoformat(),
                    },
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Image upload failed for recipe {recipe_id}: {str(e)}")
        return jsonify({"error": "Image upload failed"}), 500


@bp.route("/jobs/<int:job_id>", methods=["GET"])
@require_auth
def get_processing_job(current_user, job_id: int):
    job = ProcessingJob.query.get_or_404(job_id)
    # Verify job belongs to user (through cookbook ownership or direct ownership)
    if job.cookbook_id:
        cookbook = Cookbook.query.filter_by(id=job.cookbook_id, user_id=current_user.id).first()
        if not cookbook:
            return jsonify({"error": "Job not found"}), 404

    return jsonify(job.to_dict())


@bp.route("/images/<string:filename>", methods=["GET"])
@require_auth
def serve_image(current_user, filename: str) -> Response:
    """Serve uploaded images (recipe and cookbook images)."""
    try:
        # Check if it's a recipe image
        recipe_image = RecipeImage.query.filter_by(filename=filename).first()
        if recipe_image:
            # Check if user owns the recipe associated with this image (admins can access all)
            if recipe_image.recipe_id and should_apply_user_filter(current_user):
                recipe = Recipe.query.filter_by(id=recipe_image.recipe_id, user_id=current_user.id).first()
                if not recipe:
                    return jsonify({"error": "Access denied"}), 403
        else:
            # Check if it's a cookbook cover image
            cookbook = Cookbook.query.filter(Cookbook.cover_image_url.like(f"%{filename}")).first()
            if cookbook:
                # Check if user owns the cookbook (admins can access all)
                if should_apply_user_filter(current_user) and cookbook.user_id != current_user.id:
                    return jsonify({"error": "Access denied"}), 403
            else:
                return jsonify({"error": "Image not found"}), 404

        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        file_path = upload_folder / filename

        # Security check - ensure file is within upload folder
        if not str(file_path.resolve()).startswith(str(upload_folder.resolve())):
            return jsonify({"error": "Invalid file path"}), 400

        if not file_path.exists():
            return jsonify({"error": "Image not found"}), 404

        return send_file(file_path)

    except Exception as e:
        current_app.logger.error(f"Error serving image {filename}: {str(e)}")
        return jsonify({"error": "Error serving image"}), 500


def _process_recipe_image(job_id: int) -> None:
    """Main function to process a recipe image through OCR and parsing."""
    job = ProcessingJob.query.get(job_id)
    if not job:
        return

    try:
        job.status = ProcessingStatus.PROCESSING
        db.session.commit()

        # Extract text from image
        extracted_text = _extract_text_from_image(job.image_id)

        # Parse the extracted text
        parsed_recipe = _parse_extracted_text(extracted_text)

        # Create recipe and related records
        recipe = _create_recipe_from_parsed_data(parsed_recipe, extracted_text, job)

        # Associate recipe with job and image
        _associate_recipe_with_job(job, recipe)

        job.status = ProcessingStatus.COMPLETED
        db.session.commit()

    except Exception as e:
        job.status = ProcessingStatus.FAILED
        job.error_message = str(e)
        db.session.commit()
        current_app.logger.error(f"Processing failed for job {job_id}: {str(e)}")


def _extract_text_from_image(image_id: int) -> str:
    """Extract text from recipe image using OCR."""
    recipe_image = RecipeImage.query.get(image_id)
    if not recipe_image:
        raise Exception("Recipe image not found")

    ocr_service = OCRService()
    image_path = Path(recipe_image.file_path)
    return ocr_service.extract_text_from_image(image_path)


def _parse_extracted_text(extracted_text: str) -> Dict[str, Any]:
    """Parse extracted text into structured recipe data."""
    recipe_parser = RecipeParser()
    return recipe_parser.parse_recipe_text(extracted_text)


def _create_recipe_from_parsed_data(
    parsed_recipe: Dict[str, Any], extracted_text: str, job: ProcessingJob
) -> Recipe:
    """Create recipe and all related records from parsed data."""
    # Get user_id from cookbook if it exists
    user_id = None
    if job.cookbook_id:
        cookbook = Cookbook.query.get(job.cookbook_id)
        if cookbook:
            user_id = cookbook.user_id

    # Create base recipe
    recipe = Recipe(
        title=parsed_recipe.get("title", "Extracted Recipe"),
        description=parsed_recipe.get("description"),
        cookbook_id=job.cookbook_id,
        page_number=job.page_number,
        prep_time=parsed_recipe.get("prep_time"),
        cook_time=parsed_recipe.get("cook_time"),
        servings=parsed_recipe.get("servings"),
        difficulty=parsed_recipe.get("difficulty"),
        user_id=user_id,
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

    for order, ingredient_text in enumerate(ingredients, 1):
        if ingredient_text.strip():
            parsed_ingredient = _parse_ingredient_text(ingredient_text.strip())
            ingredient = _find_or_create_ingredient(parsed_ingredient)
            _create_recipe_ingredient_association(
                recipe_id, ingredient.id, parsed_ingredient, order
            )


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

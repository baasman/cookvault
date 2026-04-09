"""Service for importing recipes from JSON format."""

import logging
import traceback
from datetime import datetime

from app import db
from app.models.recipe import (
    Ingredient,
    Instruction,
    Recipe,
    RecipeImage,
    Tag,
    recipe_ingredients,
)

logger = logging.getLogger(__name__)

IMPORT_SCHEMA_VERSION = "1.0"
MAX_IMPORT_RECIPES = 200

REQUIRED_RECIPE_FIELDS = ["title"]


def validate_import_data(data: dict) -> list[str]:
    """Validate the top-level structure of import JSON. Returns list of errors."""
    errors = []

    if not isinstance(data, dict):
        return ["Import data must be a JSON object"]

    version = data.get("version")
    if version and version != IMPORT_SCHEMA_VERSION:
        errors.append(f"Unsupported schema version: {version}")

    recipes = data.get("recipes")
    if not isinstance(recipes, list):
        errors.append("'recipes' must be an array")
        return errors

    if len(recipes) == 0:
        errors.append("No recipes to import")
        return errors

    if len(recipes) > MAX_IMPORT_RECIPES:
        errors.append(f"Cannot import more than {MAX_IMPORT_RECIPES} recipes at once")

    for i, recipe in enumerate(recipes):
        if not isinstance(recipe, dict):
            errors.append(f"Recipe at index {i} must be an object")
            continue
        if not recipe.get("title"):
            errors.append(f"Recipe at index {i} is missing required field 'title'")

    return errors


def _get_or_create_ingredient(name: str) -> Ingredient:
    """Find an existing ingredient by name or create a new one."""
    normalized = name.strip().lower()
    ingredient = Ingredient.query.filter(
        db.func.lower(Ingredient.name) == normalized
    ).first()
    if not ingredient:
        ingredient = Ingredient(name=name.strip())
        db.session.add(ingredient)
        db.session.flush()  # Get the ID
    return ingredient


def import_single_recipe(recipe_data: dict, user_id: int) -> Recipe:
    """Import a single recipe from dict data. Raises on error."""
    recipe = Recipe(
        title=recipe_data["title"][:200],
        description=recipe_data.get("description"),
        prep_time=recipe_data.get("prep_time"),
        cook_time=recipe_data.get("cook_time"),
        servings=recipe_data.get("servings"),
        difficulty=recipe_data.get("difficulty"),
        course_type=recipe_data.get("course_type"),
        source=recipe_data.get("source"),
        user_id=user_id,
        uploaded_by_id=user_id,
        is_original_recipe=True,
        is_public=False,
    )
    db.session.add(recipe)
    db.session.flush()  # Get recipe.id

    # Ingredients
    ingredients_data = recipe_data.get("ingredients", [])
    for order, ing_data in enumerate(ingredients_data):
        if not isinstance(ing_data, dict) or not ing_data.get("name"):
            continue
        ingredient = _get_or_create_ingredient(ing_data["name"])
        db.session.execute(
            recipe_ingredients.insert().values(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=ing_data.get("quantity"),
                unit=ing_data.get("unit"),
                preparation=ing_data.get("preparation"),
                optional=ing_data.get("optional", False),
                order=ing_data.get("order", order),
            )
        )

    # Instructions
    instructions_data = recipe_data.get("instructions", [])
    for step_data in instructions_data:
        if not isinstance(step_data, dict) or not step_data.get("text"):
            continue
        instruction = Instruction(
            recipe_id=recipe.id,
            step_number=step_data.get("step_number", 1),
            text=step_data["text"],
        )
        db.session.add(instruction)

    # Tags
    tags_data = recipe_data.get("tags", [])
    for tag_name in tags_data:
        if isinstance(tag_name, str) and tag_name.strip():
            db.session.add(Tag(recipe_id=recipe.id, name=tag_name.strip()))

    # Images (store URLs as-is — no re-upload)
    images_data = recipe_data.get("images", [])
    for img_order, img_data in enumerate(images_data):
        if not isinstance(img_data, dict):
            continue
        url = img_data.get("url", "")
        if url:
            image = RecipeImage(
                recipe_id=recipe.id,
                cloudinary_url=url,
                image_order=img_data.get("order", img_order),
            )
            db.session.add(image)

    return recipe


def import_recipes(data: dict, user_id: int) -> dict:
    """Import recipes from validated JSON data.

    Returns:
        { "imported": count, "recipe_ids": [...], "errors": [...] }
    """
    recipes_data = data.get("recipes", [])
    imported_ids = []
    errors = []

    for i, recipe_data in enumerate(recipes_data):
        try:
            recipe = import_single_recipe(recipe_data, user_id)
            imported_ids.append(recipe.id)
        except Exception as e:
            title = recipe_data.get("title", f"Recipe {i}")
            logger.error(
                f"Failed to import recipe '{title}': {e}\n{traceback.format_exc()}"
            )
            errors.append(
                {
                    "index": i,
                    "title": title,
                    "reason": str(e),
                }
            )

    if imported_ids:
        db.session.commit()
        logger.info(f"Imported {len(imported_ids)} recipes for user {user_id}")

    return {
        "imported": len(imported_ids),
        "recipe_ids": imported_ids,
        "errors": errors,
    }


def export_recipe_to_dict(recipe: Recipe) -> dict:
    """Convert a recipe to the export JSON format."""
    ingredients = recipe.get_recipe_ingredients()
    instructions = [inst.to_dict() for inst in recipe.recipe_instructions]
    tags = [tag.name for tag in recipe.recipe_tags]
    images = [
        {
            "url": img.cloudinary_url or img.image_url or "",
            "order": img.image_order if hasattr(img, "image_order") else 0,
        }
        for img in recipe.images
        if img.cloudinary_url or img.image_url
    ]

    return {
        "title": recipe.title,
        "description": recipe.description,
        "prep_time": recipe.prep_time,
        "cook_time": recipe.cook_time,
        "servings": recipe.servings,
        "difficulty": recipe.difficulty,
        "course_type": recipe.course_type,
        "source": recipe.source,
        "tags": tags,
        "ingredients": [
            {
                "name": ing.get("name", ""),
                "quantity": ing.get("quantity"),
                "unit": ing.get("unit"),
                "preparation": ing.get("preparation"),
                "optional": ing.get("optional", False),
                "order": ing.get("order", 0),
            }
            for ing in ingredients
        ],
        "instructions": [
            {
                "step_number": inst.get("step_number", 1),
                "text": inst.get("text", ""),
            }
            for inst in instructions
        ],
        "images": images,
    }


def build_export_data(recipes: list[Recipe]) -> dict:
    """Build the full export JSON structure from a list of recipes."""
    return {
        "version": IMPORT_SCHEMA_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "source": "cookbook-creator",
        "recipes": [export_recipe_to_dict(r) for r in recipes],
    }

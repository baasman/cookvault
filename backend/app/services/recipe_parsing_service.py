"""Recipe parsing service.

Shared helpers for populating a Recipe with parsed data (ingredients, instructions, tags).
Extracted from app.api.recipes.routes so the same logic can be reused by guest BookProject
submission endpoints that bypass the standard authenticated upload flow.
"""

import re
from typing import Any, Dict, List, Optional

from flask import current_app
from sqlalchemy import select

from app import db
from app.models import Ingredient, Instruction, Tag
from app.models.recipe import recipe_ingredients


def create_recipe_ingredients(recipe_id: int, parsed_recipe: Dict[str, Any]) -> None:
    """Create Ingredient records and recipe_ingredients associations from parsed data.

    Each ingredient is committed in its own savepoint so a single failure doesn't take
    down the rest of the batch.
    """
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
        savepoint = db.session.begin_nested()
        try:
            if isinstance(ingredient_data, str):
                if ingredient_data.strip():
                    parsed_ingredient = _parse_ingredient_text(ingredient_data.strip())
                    ingredient = _find_or_create_ingredient(parsed_ingredient)
                    _create_recipe_ingredient_association(
                        recipe_id, ingredient.id, parsed_ingredient, order
                    )
            elif isinstance(ingredient_data, dict):
                ingredient_name = ingredient_data.get("name", "").strip()
                if ingredient_name:
                    parsed_ingredient = {
                        "name": ingredient_name,
                        "quantity": ingredient_data.get("quantity"),
                        "unit": ingredient_data.get("unit"),
                        "preparation": ingredient_data.get("preparation"),
                        "optional": bool(ingredient_data.get("optional", False)),
                        "category": None,
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

            savepoint.commit()

        except Exception as e:
            savepoint.rollback()
            current_app.logger.error(
                f"Failed to create ingredient {order}: {str(e)}", exc_info=True
            )


def create_recipe_instructions(
    recipe_id: int,
    parsed_recipe: Dict[str, Any],
    fallback_text: str = "",
    original_instructions: Optional[List[str]] = None,
) -> None:
    """Create Instruction records for the recipe, with optional original text for translations."""
    instructions = parsed_recipe.get("instructions", [])
    if isinstance(instructions, str):
        instructions = [instructions]
    elif not isinstance(instructions, list):
        instructions = [fallback_text]

    if original_instructions and not isinstance(original_instructions, list):
        original_instructions = None

    for i, instruction_text in enumerate(instructions, 1):
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


def create_recipe_tags(recipe_id: int, parsed_recipe: Dict[str, Any]) -> None:
    """Create Tag records for the recipe."""
    tags = parsed_recipe.get("tags", [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",")]
    elif not isinstance(tags, list):
        tags = []

    for tag_name in tags:
        if tag_name.strip():
            tag = Tag(recipe_id=recipe_id, name=tag_name.strip())
            db.session.add(tag)


def _find_or_create_ingredient(parsed_ingredient: Dict[str, Any]) -> Ingredient:
    """Find an existing Ingredient by name or create a new one."""
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
    """Insert into the recipe_ingredients association table with quantity / unit / etc."""
    existing = db.session.execute(
        select(recipe_ingredients).where(
            recipe_ingredients.c.recipe_id == recipe_id,
            recipe_ingredients.c.ingredient_id == ingredient_id,
        )
    ).first()

    if existing:
        return

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


_UNITS_PATTERN = (
    r"\b(?:cups?|cup|tbsp|tsp|teaspoons?|tablespoons?|oz|ounces?|lbs?|pounds?|"
    r"g|grams?|kg|kilograms?|ml|milliliters?|l|liters?|pint|pints|quart|quarts|"
    r"gallon|gallons|inch|inches|cloves?|pieces?|slices?|whole|medium|large|small)\b"
)

_QUANTITY_UNIT_PATTERN = (
    r"^(\d+(?:\.\d+)?(?:/\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*("
    + _UNITS_PATTERN
    + r")?\s*(.+)$"
)

_PREP_INDICATORS = [
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


def _parse_ingredient_text(ingredient_text: str) -> Dict[str, Any]:
    """Parse a free-form ingredient string into structured fields."""
    match = re.match(_QUANTITY_UNIT_PATTERN, ingredient_text.strip(), re.IGNORECASE)

    if match:
        quantity_str = match.group(1)
        unit = match.group(2)
        remaining = match.group(3)

        try:
            if "/" in quantity_str:
                parts = quantity_str.split()
                if len(parts) == 2:
                    whole, fraction = parts
                    num, denom = fraction.split("/")
                    quantity = float(whole) + float(num) / float(denom)
                else:
                    num, denom = quantity_str.split("/")
                    quantity = float(num) / float(denom)
            elif "-" in quantity_str:
                quantity = float(quantity_str.split("-")[0])
            else:
                quantity = float(quantity_str)
        except ValueError:
            quantity = None
    else:
        quantity = None
        unit = None
        remaining = ingredient_text

    name = remaining.strip()
    preparation = None

    for prep in _PREP_INDICATORS:
        if prep in name.lower():
            parts = name.lower().split(prep)
            if len(parts) == 2 and parts[1].strip() == "":
                name = parts[0].strip()
                preparation = prep
                break
            elif len(parts) == 2 and parts[0].strip():
                name = parts[0].strip()
                preparation = prep + parts[1].strip()
                break

    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(",")

    return {
        "name": name,
        "quantity": quantity,
        "unit": unit.lower() if unit else None,
        "preparation": preparation,
        "optional": "optional" in ingredient_text.lower(),
        "category": None,
    }

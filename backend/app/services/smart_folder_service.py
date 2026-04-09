"""Service for building SQLAlchemy queries from smart folder rules."""

import logging

from sqlalchemy import func

from app import db
from app.models.recipe import (
    Ingredient,
    Recipe,
    RecipeRating,
    Tag,
    recipe_ingredients,
)

logger = logging.getLogger(__name__)

# Supported fields and their valid operators
FIELD_OPERATORS = {
    "course_type": ["eq", "neq"],
    "difficulty": ["eq", "neq"],
    "cook_time": ["eq", "lte", "gte", "lt", "gt"],
    "prep_time": ["eq", "lte", "gte", "lt", "gt"],
    "servings": ["eq", "lte", "gte", "lt", "gt"],
    "tags": ["contains", "not_contains"],
    "min_rating": ["gte", "gt"],
    "is_public": ["eq"],
    "ingredients": ["contains_any", "contains_all"],
}


def validate_rules(rules: dict) -> list[str]:
    """Validate a rules JSON structure. Returns list of errors."""
    errors = []

    if not isinstance(rules, dict):
        return ["Rules must be a JSON object"]

    match = rules.get("match", "all")
    if match not in ("all", "any"):
        errors.append(f"'match' must be 'all' or 'any', got '{match}'")

    conditions = rules.get("conditions", [])
    if not isinstance(conditions, list):
        errors.append("'conditions' must be an array")
        return errors

    if len(conditions) == 0:
        errors.append("At least one condition is required")

    for i, cond in enumerate(conditions):
        if not isinstance(cond, dict):
            errors.append(f"Condition {i} must be an object")
            continue

        field = cond.get("field")
        if field not in FIELD_OPERATORS:
            errors.append(
                f"Condition {i}: unsupported field '{field}'. Supported: {list(FIELD_OPERATORS.keys())}"
            )
            continue

        operator = cond.get("operator")
        if operator not in FIELD_OPERATORS[field]:
            errors.append(
                f"Condition {i}: invalid operator '{operator}' for field '{field}'"
            )

        if "value" not in cond:
            errors.append(f"Condition {i}: 'value' is required")

    return errors


def _apply_comparison(column, operator: str, value):
    """Apply a comparison operator to a column."""
    if operator == "eq":
        return column == value
    elif operator == "neq":
        return column != value
    elif operator == "lt":
        return column < value
    elif operator == "lte":
        return column <= value
    elif operator == "gt":
        return column > value
    elif operator == "gte":
        return column >= value
    raise ValueError(f"Unknown operator: {operator}")


def build_query(rules: dict, user_id: int):
    """Build a SQLAlchemy query from smart folder rules.

    Returns a query for Recipe objects owned by user_id that match the rules.
    """
    match_mode = rules.get("match", "all")
    conditions = rules.get("conditions", [])

    # Base query: user's own recipes
    query = Recipe.query.filter(Recipe.user_id == user_id)

    filters = []
    for cond in conditions:
        field = cond["field"]
        operator = cond["operator"]
        value = cond["value"]

        if field == "course_type":
            filters.append(_apply_comparison(Recipe.course_type, operator, value))

        elif field == "difficulty":
            filters.append(_apply_comparison(Recipe.difficulty, operator, value))

        elif field == "cook_time":
            filters.append(_apply_comparison(Recipe.cook_time, operator, int(value)))

        elif field == "prep_time":
            filters.append(_apply_comparison(Recipe.prep_time, operator, int(value)))

        elif field == "servings":
            filters.append(_apply_comparison(Recipe.servings, operator, int(value)))

        elif field == "is_public":
            filters.append(Recipe.is_public == bool(value))

        elif field == "tags":
            tag_value = str(value).strip().lower()
            if operator == "contains":
                filters.append(
                    Recipe.id.in_(
                        db.session.query(Tag.recipe_id).filter(
                            func.lower(Tag.name) == tag_value
                        )
                    )
                )
            elif operator == "not_contains":
                filters.append(
                    ~Recipe.id.in_(
                        db.session.query(Tag.recipe_id).filter(
                            func.lower(Tag.name) == tag_value
                        )
                    )
                )

        elif field == "min_rating":
            threshold = float(value)
            # Subquery: recipes with average rating >= threshold
            rating_subq = (
                db.session.query(RecipeRating.recipe_id)
                .group_by(RecipeRating.recipe_id)
                .having(func.avg(RecipeRating.rating) >= threshold)
            )
            if operator == "gt":
                rating_subq = (
                    db.session.query(RecipeRating.recipe_id)
                    .group_by(RecipeRating.recipe_id)
                    .having(func.avg(RecipeRating.rating) > threshold)
                )
            filters.append(Recipe.id.in_(rating_subq))

        elif field == "ingredients":
            if not isinstance(value, list):
                value = [value]
            ingredient_names = [v.strip().lower() for v in value if isinstance(v, str)]

            if operator == "contains_any":
                filters.append(
                    Recipe.id.in_(
                        db.session.query(recipe_ingredients.c.recipe_id)
                        .join(
                            Ingredient,
                            Ingredient.id == recipe_ingredients.c.ingredient_id,
                        )
                        .filter(func.lower(Ingredient.name).in_(ingredient_names))
                    )
                )
            elif operator == "contains_all":
                for name in ingredient_names:
                    filters.append(
                        Recipe.id.in_(
                            db.session.query(recipe_ingredients.c.recipe_id)
                            .join(
                                Ingredient,
                                Ingredient.id == recipe_ingredients.c.ingredient_id,
                            )
                            .filter(func.lower(Ingredient.name) == name)
                        )
                    )

    if filters:
        if match_mode == "all":
            query = query.filter(db.and_(*filters))
        else:
            query = query.filter(db.or_(*filters))

    return query

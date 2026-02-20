"""
Rating service for recipe ratings with aggregation across users.

Ratings are stored per user per recipe and aggregated at query time
by matching normalized_title + cookbook_id for cookbook recipes,
or by canonical_source_url for URL-imported recipes.
"""

import logging
import re
import traceback
from typing import Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from sqlalchemy import func

from app import db
from app.models.recipe import Recipe, RecipeRating

logger = logging.getLogger(__name__)

# Common tracking parameters to remove from URLs for normalization
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "source",
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "_ga",
    "_gl",
    "yclid",
    "twclid",
    "igshid",
}


def normalize_url(url: str) -> Optional[str]:
    """
    Normalize URL for matching across users.

    Normalization rules:
    - Lowercase scheme and host
    - Remove 'www.' prefix from host
    - Remove tracking params (utm_*, fbclid, gclid, etc.)
    - Remove URL fragments (#...)
    - Remove trailing slashes from path
    - Sort remaining query parameters alphabetically

    Example:
        Input:  https://www.seriouseats.com/recipe/?utm_source=twitter#tips
        Output: https://seriouseats.com/recipe

    Args:
        url: The URL to normalize

    Returns:
        The normalized URL string, or None if URL is invalid/empty
    """
    if not url:
        return None

    try:
        # Parse the URL
        parsed = urlparse(url)

        # Must have a scheme and netloc (host)
        if not parsed.scheme or not parsed.netloc:
            return None

        # Normalize scheme to lowercase
        scheme = parsed.scheme.lower()

        # Normalize host: lowercase, remove www. prefix
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]

        # Normalize path: remove trailing slash (but keep '/' for root)
        path = parsed.path.rstrip("/") or "/"

        # Remove tracking params, sort remaining params
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMS
        }

        # Sort params and rebuild query string
        # Only include query string if there are non-tracking params
        if filtered_params:
            sorted_params = sorted(filtered_params.items())
            query = urlencode(sorted_params, doseq=True)
        else:
            query = ""

        # Rebuild URL without fragment
        normalized = urlunparse((scheme, host, path, "", query, ""))

        return normalized

    except Exception as e:
        logger.warning(f"Failed to normalize URL '{url}': {str(e)}")
        return None


def normalize_title(title: str) -> str:
    """
    Normalize a recipe title for matching.

    Normalization rules:
    - Convert to lowercase
    - Strip all punctuation
    - Collapse multiple spaces to single space
    - Strip leading/trailing whitespace

    Example: "Grandma's Chocolate Chip Cookies!" -> "grandmas chocolate chip cookies"

    Args:
        title: The recipe title to normalize

    Returns:
        The normalized title string
    """
    if not title:
        return ""

    # Convert to lowercase
    normalized = title.lower()

    # Remove all punctuation (keeping only alphanumeric and spaces)
    normalized = re.sub(r"[^\w\s]", "", normalized)

    # Collapse multiple spaces to single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Strip leading/trailing whitespace
    normalized = normalized.strip()

    return normalized


def update_normalized_title(recipe: Recipe) -> None:
    """
    Update the normalized_title field on a recipe.

    Call this when a recipe is created or its title changes.

    Args:
        recipe: The Recipe object to update
    """
    recipe.normalized_title = normalize_title(recipe.title)


def submit_rating(user_id: int, recipe_id: int, rating: int) -> RecipeRating:
    """
    Submit or update a rating for a recipe.

    If the user has already rated this recipe, their existing rating is updated.
    Otherwise, a new rating is created.

    Args:
        user_id: The ID of the user submitting the rating
        recipe_id: The ID of the recipe being rated
        rating: The rating value (1-5)

    Returns:
        The RecipeRating object (created or updated)

    Raises:
        ValueError: If rating is not between 1 and 5
        ValueError: If recipe doesn't exist
    """
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")

    # Verify recipe exists
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        raise ValueError("Recipe not found")

    try:
        # Check for existing rating
        existing_rating = RecipeRating.query.filter_by(
            user_id=user_id, recipe_id=recipe_id
        ).first()

        if existing_rating:
            # Update existing rating
            existing_rating.rating = rating
            db.session.commit()
            logger.info(
                f"User {user_id} updated rating for recipe {recipe_id} to {rating}"
            )
            return existing_rating
        else:
            # Create new rating
            new_rating = RecipeRating(
                user_id=user_id, recipe_id=recipe_id, rating=rating
            )
            db.session.add(new_rating)
            db.session.commit()
            logger.info(
                f"User {user_id} submitted rating {rating} for recipe {recipe_id}"
            )
            return new_rating

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Failed to submit rating for recipe {recipe_id} by user {user_id}: {str(e)}"
        )
        logger.error(traceback.format_exc())
        raise


def get_user_rating(user_id: int, recipe_id: int) -> Optional[RecipeRating]:
    """
    Get a user's rating for a specific recipe.

    Args:
        user_id: The ID of the user
        recipe_id: The ID of the recipe

    Returns:
        The RecipeRating if it exists, None otherwise
    """
    return RecipeRating.query.filter_by(user_id=user_id, recipe_id=recipe_id).first()


def delete_rating(user_id: int, recipe_id: int) -> bool:
    """
    Delete a user's rating for a recipe.

    Args:
        user_id: The ID of the user
        recipe_id: The ID of the recipe

    Returns:
        True if a rating was deleted, False if no rating existed
    """
    try:
        rating = RecipeRating.query.filter_by(
            user_id=user_id, recipe_id=recipe_id
        ).first()

        if rating:
            db.session.delete(rating)
            db.session.commit()
            logger.info(f"User {user_id} deleted rating for recipe {recipe_id}")
            return True

        return False

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Failed to delete rating for recipe {recipe_id} by user {user_id}: {str(e)}"
        )
        logger.error(traceback.format_exc())
        raise


def get_aggregate_rating_for_recipe(recipe_id: int) -> dict:
    """
    Get the aggregate rating for a recipe.

    Aggregation strategy (in order of priority):
    1. If recipe has cookbook_id: aggregate by normalized_title + cookbook_id
       (shared ratings across users with same cookbook recipe)
    2. If recipe has canonical_source_url (but no cookbook): aggregate by URL
       (shared ratings across URL-imported recipes from the same source)
    3. Otherwise: single recipe only (no cross-user matching)

    Args:
        recipe_id: The ID of the recipe

    Returns:
        dict with:
        - average_rating: float or None if no ratings
        - rating_count: int, number of ratings
        - normalized_title: str or None
        - cookbook_id: int or None
        - canonical_source_url: str or None (for URL-imported recipes)
        - matching_recipe_count: int, number of recipes matched for aggregation
    """
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return {
            "average_rating": None,
            "rating_count": 0,
            "normalized_title": None,
            "cookbook_id": None,
            "canonical_source_url": None,
            "matching_recipe_count": 0,
        }

    normalized_title = recipe.normalized_title
    cookbook_id = recipe.cookbook_id
    canonical_source_url = recipe.canonical_source_url

    # Strategy 1: Cookbook-based aggregation (highest priority)
    if cookbook_id is not None and normalized_title:
        # Find all recipes with matching normalized_title AND cookbook_id
        matching_recipes = (
            Recipe.query.filter(
                Recipe.normalized_title == normalized_title,
                Recipe.cookbook_id == cookbook_id,
            )
            .with_entities(Recipe.id)
            .all()
        )

        matching_recipe_ids = [r.id for r in matching_recipes]

        # Aggregate ratings across all matching recipes
        result = (
            db.session.query(
                func.avg(RecipeRating.rating).label("avg_rating"),
                func.count(RecipeRating.id).label("rating_count"),
            )
            .filter(RecipeRating.recipe_id.in_(matching_recipe_ids))
            .first()
        )

        avg_rating = float(result.avg_rating) if result.avg_rating else None
        rating_count = result.rating_count or 0

        return {
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "rating_count": rating_count,
            "normalized_title": normalized_title,
            "cookbook_id": cookbook_id,
            "canonical_source_url": None,
            "matching_recipe_count": len(matching_recipe_ids),
        }

    # Strategy 2: URL-based aggregation for URL-imported recipes (no cookbook)
    if canonical_source_url:
        # Find all recipes with matching canonical_source_url
        matching_recipes = (
            Recipe.query.filter(
                Recipe.canonical_source_url == canonical_source_url,
            )
            .with_entities(Recipe.id)
            .all()
        )

        matching_recipe_ids = [r.id for r in matching_recipes]

        # Aggregate ratings across all matching recipes
        result = (
            db.session.query(
                func.avg(RecipeRating.rating).label("avg_rating"),
                func.count(RecipeRating.id).label("rating_count"),
            )
            .filter(RecipeRating.recipe_id.in_(matching_recipe_ids))
            .first()
        )

        avg_rating = float(result.avg_rating) if result.avg_rating else None
        rating_count = result.rating_count or 0

        return {
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "rating_count": rating_count,
            "normalized_title": normalized_title,
            "cookbook_id": None,
            "canonical_source_url": canonical_source_url,
            "matching_recipe_count": len(matching_recipe_ids),
        }

    # Strategy 3: Single recipe fallback (no aggregation)
    result = (
        db.session.query(
            func.avg(RecipeRating.rating).label("avg_rating"),
            func.count(RecipeRating.id).label("rating_count"),
        )
        .filter(RecipeRating.recipe_id == recipe_id)
        .first()
    )

    avg_rating = float(result.avg_rating) if result.avg_rating else None
    rating_count = result.rating_count or 0

    return {
        "average_rating": round(avg_rating, 2) if avg_rating else None,
        "rating_count": rating_count,
        "normalized_title": normalized_title,
        "cookbook_id": cookbook_id,
        "canonical_source_url": None,
        "matching_recipe_count": 1,
    }


def backfill_normalized_titles() -> int:
    """
    Backfill normalized_title for all existing recipes that don't have one.

    This should be run during migration or as a one-time script.

    Returns:
        Number of recipes updated
    """
    try:
        recipes = Recipe.query.filter(Recipe.normalized_title.is_(None)).all()

        count = 0
        for recipe in recipes:
            if recipe.title:
                recipe.normalized_title = normalize_title(recipe.title)
                count += 1

        db.session.commit()
        logger.info(f"Backfilled normalized_title for {count} recipes")
        return count

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to backfill normalized titles: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def backfill_canonical_source_urls() -> int:
    """
    Backfill canonical_source_url for all existing recipes that have a source URL.

    This should be run during migration or as a one-time script.

    Returns:
        Number of recipes updated
    """
    try:
        # Find recipes with source URLs but no canonical_source_url
        recipes = Recipe.query.filter(
            Recipe.source.isnot(None),
            Recipe.canonical_source_url.is_(None),
        ).all()

        count = 0
        for recipe in recipes:
            if recipe.source and (
                recipe.source.startswith("http://")
                or recipe.source.startswith("https://")
            ):
                normalized = normalize_url(recipe.source)
                if normalized:
                    recipe.canonical_source_url = normalized
                    count += 1

        db.session.commit()
        logger.info(f"Backfilled canonical_source_url for {count} recipes")
        return count

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to backfill canonical source URLs: {str(e)}")
        logger.error(traceback.format_exc())
        raise

"""
Public API endpoints for browsing public recipes without authentication
"""

from flask import jsonify, request
from sqlalchemy import desc
from app.api import bp
from app.models.recipe import Recipe, Cookbook, Ingredient, recipe_ingredients
from app.models.user import User
from app import db


@bp.route("/public/recipes", methods=["GET"])
def get_public_recipes():
    """Get all public recipes with pagination and optional filtering."""
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(
            request.args.get("per_page", 20, type=int), 100
        )  # Max 100 per page

        # Get search parameters
        search = request.args.get("search", "").strip()
        difficulty = request.args.get("difficulty", "").strip()

        # Build query for public recipes only
        query = Recipe.query.filter(Recipe.is_public)

        # Apply search filter if provided
        if search:
            query = query.filter(
                Recipe.title.ilike(f"%{search}%")
                | Recipe.description.ilike(f"%{search}%")
            )

        # Apply difficulty filter if provided
        if difficulty:
            query = query.filter(Recipe.difficulty.ilike(f"%{difficulty}%"))

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
                            Ingredient,
                            Ingredient.id == recipe_ingredients.c.ingredient_id,
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

        # Course type filtering
        course_type = request.args.get("course_type", "").strip()
        if course_type:
            query = query.filter(Recipe.course_type.ilike(f"%{course_type}%"))

        # Order by published date (newest first)
        query = query.order_by(desc(Recipe.published_at))

        # Paginate results
        recipes_pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        recipes_data = []
        for recipe in recipes_pagination.items:
            recipe_dict = recipe.to_dict(include_user=True)
            recipes_data.append(recipe_dict)

        return jsonify(
            {
                "recipes": recipes_data,
                "pagination": {
                    "page": page,
                    "pages": recipes_pagination.pages,
                    "per_page": per_page,
                    "total": recipes_pagination.total,
                    "has_next": recipes_pagination.has_next,
                    "has_prev": recipes_pagination.has_prev,
                    "next_num": recipes_pagination.next_num,
                    "prev_num": recipes_pagination.prev_num,
                },
            }
        ), 200

    except Exception as e:
        return jsonify(
            {"error": "Failed to fetch public recipes", "details": str(e)}
        ), 500


@bp.route("/public/recipes/<int:recipe_id>", methods=["GET"])
def get_public_recipe(recipe_id):
    """Get a specific public recipe by ID."""
    try:
        recipe = Recipe.query.filter(Recipe.id == recipe_id, Recipe.is_public).first()

        if not recipe:
            return jsonify({"error": "Public recipe not found"}), 404

        return jsonify(recipe.to_dict(include_user=True)), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch recipe", "details": str(e)}), 500


@bp.route("/public/users/<int:user_id>/recipes", methods=["GET"])
def get_user_public_recipes(user_id):
    """Get all public recipes by a specific user."""
    try:
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        # Query user's public recipes
        query = Recipe.query.filter(
            Recipe.user_id == user_id, Recipe.is_public
        ).order_by(desc(Recipe.published_at))

        # Paginate results
        recipes_pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        recipes_data = []
        for recipe in recipes_pagination.items:
            recipe_dict = recipe.to_dict(include_user=True)
            recipes_data.append(recipe_dict)

        # Include user information
        user_info = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

        return jsonify(
            {
                "user": user_info,
                "recipes": recipes_data,
                "pagination": {
                    "page": page,
                    "pages": recipes_pagination.pages,
                    "per_page": per_page,
                    "total": recipes_pagination.total,
                    "has_next": recipes_pagination.has_next,
                    "has_prev": recipes_pagination.has_prev,
                    "next_num": recipes_pagination.next_num,
                    "prev_num": recipes_pagination.prev_num,
                },
            }
        ), 200

    except Exception as e:
        return jsonify(
            {"error": "Failed to fetch user recipes", "details": str(e)}
        ), 500


@bp.route("/public/recipes/featured", methods=["GET"])
def get_featured_recipes():
    """Get featured public recipes."""
    try:
        # Get actually featured recipes ordered by featured_at (most recent first)
        recipes = (
            Recipe.query.filter(Recipe.is_public, Recipe.is_featured)
            .order_by(desc(Recipe.featured_at))
            .all()
        )

        recipes_data = []
        for recipe in recipes:
            recipe_dict = recipe.to_dict(include_user=True)
            recipes_data.append(recipe_dict)

        return jsonify({"recipes": recipes_data}), 200

    except Exception as e:
        return jsonify(
            {"error": "Failed to fetch featured recipes", "details": str(e)}
        ), 500


@bp.route("/public/stats", methods=["GET"])
def get_public_stats():
    """Get public statistics about the platform."""
    try:
        # Count public recipes
        public_recipes_count = Recipe.query.filter(Recipe.is_public).count()

        # Count users with public recipes
        users_with_public_recipes = (
            db.session.query(Recipe.user_id).filter(Recipe.is_public).distinct().count()
        )

        # Get recent activity (last 30 days)
        from datetime import datetime, timedelta

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_recipes = Recipe.query.filter(
            Recipe.is_public, Recipe.published_at >= thirty_days_ago
        ).count()

        return jsonify(
            {
                "public_recipes": public_recipes_count,
                "contributing_users": users_with_public_recipes,
                "recent_recipes": recent_recipes,
            }
        ), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch statistics", "details": str(e)}), 500


@bp.route("/public/cookbooks", methods=["GET"])
def get_public_cookbooks():
    """Get all purchasable cookbooks and cookbooks with public recipes, with pagination and optional filtering."""
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(
            request.args.get("per_page", 20, type=int), 100
        )  # Max 100 per page

        # Get search and sort parameters
        search = request.args.get("search", "").strip()
        sort_by = request.args.get("sort_by", "title").strip()

        # Build query for cookbooks that are purchasable OR have at least one public recipe
        cookbooks_with_public_recipes = (
            db.session.query(Recipe.cookbook_id)
            .filter(Recipe.is_public, Recipe.cookbook_id.isnot(None))
            .distinct()
            .subquery()
        )

        query = db.session.query(Cookbook).filter(
            db.or_(
                Cookbook.is_purchasable.is_(True),
                Cookbook.id.in_(db.session.query(cookbooks_with_public_recipes)),
            )
        )

        # Apply search filter if provided
        if search:
            query = query.filter(
                Cookbook.title.ilike(f"%{search}%")
                | Cookbook.author.ilike(f"%{search}%")
                | Cookbook.description.ilike(f"%{search}%")
            )

        # Apply sorting
        if sort_by == "title":
            query = query.order_by(Cookbook.title)
        elif sort_by == "author":
            query = query.order_by(Cookbook.author)
        elif sort_by == "created_at":
            query = query.order_by(desc(Cookbook.created_at))
        elif sort_by == "recipe_count":
            # Sort by recipe count (requires a subquery)
            from sqlalchemy import func

            recipe_count_subquery = (
                db.session.query(
                    Recipe.cookbook_id.label("cookbook_id"),
                    func.count(Recipe.id).label("recipe_count"),
                )
                .filter(Recipe.is_public)
                .group_by(Recipe.cookbook_id)
                .subquery()
            )

            query = query.join(
                recipe_count_subquery,
                Cookbook.id == recipe_count_subquery.c.cookbook_id,
            ).order_by(desc(recipe_count_subquery.c.recipe_count))
        else:
            query = query.order_by(Cookbook.title)

        # Paginate results
        cookbooks_pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        cookbooks_data = []
        for cookbook in cookbooks_pagination.items:
            cookbook_dict = cookbook.to_dict()
            # Add public recipe count for this cookbook
            public_recipe_count = Recipe.query.filter(
                Recipe.cookbook_id == cookbook.id, Recipe.is_public
            ).count()
            cookbook_dict["public_recipe_count"] = public_recipe_count
            cookbooks_data.append(cookbook_dict)

        return jsonify(
            {
                "cookbooks": cookbooks_data,
                "total": cookbooks_pagination.total,
                "pages": cookbooks_pagination.pages,
                "current_page": page,
                "per_page": per_page,
                "has_next": cookbooks_pagination.has_next,
                "has_prev": cookbooks_pagination.has_prev,
            }
        ), 200

    except Exception as e:
        return jsonify(
            {"error": "Failed to fetch public cookbooks", "details": str(e)}
        ), 500


@bp.route("/public/cookbooks/<int:cookbook_id>", methods=["GET"])
def get_public_cookbook(cookbook_id):
    """Get a specific cookbook if it's purchasable or has public recipes."""
    try:
        # Check if cookbook exists
        cookbook = Cookbook.query.get(cookbook_id)
        if not cookbook:
            return jsonify({"error": "Cookbook not found"}), 404

        # Check if cookbook is purchasable or has any public recipes
        has_public_recipes = (
            Recipe.query.filter(
                Recipe.cookbook_id == cookbook_id, Recipe.is_public
            ).first()
            is not None
        )

        if not cookbook.is_purchasable and not has_public_recipes:
            return jsonify({"error": "This cookbook is not publicly available"}), 404

        cookbook_dict = cookbook.to_dict()

        # Add public recipe count
        public_recipe_count = Recipe.query.filter(
            Recipe.cookbook_id == cookbook.id, Recipe.is_public
        ).count()
        cookbook_dict["public_recipe_count"] = public_recipe_count

        return jsonify(cookbook_dict), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch cookbook", "details": str(e)}), 500


@bp.route("/public/cookbooks/<int:cookbook_id>/recipes", methods=["GET"])
def get_public_cookbook_recipes(cookbook_id):
    """Get recipes from a specific cookbook (previews for purchasable, full for public)."""
    try:
        # Check if cookbook exists
        cookbook = Cookbook.query.get(cookbook_id)
        if not cookbook:
            return jsonify({"error": "Cookbook not found"}), 404

        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)
        search = request.args.get("search", "").strip()

        # For purchasable cookbooks, show recipe previews (all recipes, limited info)
        # For non-purchasable cookbooks, show only public recipes with full info
        if cookbook.is_purchasable:
            # Show all recipes in the cookbook as previews
            query = Recipe.query.filter(Recipe.cookbook_id == cookbook_id)
        else:
            # Show only public recipes
            query = Recipe.query.filter(
                Recipe.cookbook_id == cookbook_id, Recipe.is_public
            )

        # Apply search filter if provided
        if search:
            query = query.filter(
                Recipe.title.ilike(f"%{search}%")
                | Recipe.description.ilike(f"%{search}%")
            )

        # Order by title
        query = query.order_by(Recipe.title)

        # Paginate results
        recipes_pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Check if any recipes found
        if recipes_pagination.total == 0:
            # Check if cookbook is purchasable but has no recipes yet
            if cookbook.is_purchasable:
                return jsonify({"error": "This cookbook has no recipes yet"}), 404
            return jsonify({"error": "This cookbook has no public recipes"}), 404

        recipes_data = []
        for recipe in recipes_pagination.items:
            if cookbook.is_purchasable:
                # Return preview only (limited info to entice purchase)
                recipe_dict = {
                    "id": recipe.id,
                    "title": recipe.title,
                    "description": recipe.description[:200] + "..."
                    if recipe.description and len(recipe.description) > 200
                    else recipe.description,
                    "image_url": recipe.image_url,
                    "course_type": recipe.course_type,
                    "prep_time": recipe.prep_time,
                    "cook_time": recipe.cook_time,
                    "servings": recipe.servings,
                    "is_preview": True,  # Flag to indicate this is a preview
                }
            else:
                recipe_dict = recipe.to_dict(include_user=True)
            recipes_data.append(recipe_dict)

        # Include cookbook information
        cookbook_info = {
            "id": cookbook.id,
            "title": cookbook.title,
            "author": cookbook.author,
            "description": cookbook.description,
            "is_purchasable": cookbook.is_purchasable,
            "price": cookbook.price,
        }

        return jsonify(
            {
                "cookbook": cookbook_info,
                "recipes": recipes_data,
                "pagination": {
                    "page": page,
                    "pages": recipes_pagination.pages,
                    "per_page": per_page,
                    "total": recipes_pagination.total,
                    "has_next": recipes_pagination.has_next,
                    "has_prev": recipes_pagination.has_prev,
                    "next_num": recipes_pagination.next_num,
                    "prev_num": recipes_pagination.prev_num,
                },
            }
        ), 200

    except Exception as e:
        return jsonify(
            {"error": "Failed to fetch cookbook recipes", "details": str(e)}
        ), 500

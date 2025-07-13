"""
Public API endpoints for browsing public recipes without authentication
"""
from flask import jsonify, request
from sqlalchemy import desc
from app.api import bp
from app.models.recipe import Recipe
from app.models.user import User
from app import db


@bp.route("/public/recipes", methods=["GET"])
def get_public_recipes():
    """Get all public recipes with pagination and optional filtering."""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 per page
        
        # Get search parameters
        search = request.args.get('search', '').strip()
        difficulty = request.args.get('difficulty', '').strip()
        
        # Build query for public recipes only
        query = Recipe.query.filter(Recipe.is_public == True)
        
        # Apply search filter if provided
        if search:
            query = query.filter(
                Recipe.title.ilike(f'%{search}%') | 
                Recipe.description.ilike(f'%{search}%')
            )
        
        # Apply difficulty filter if provided
        if difficulty:
            query = query.filter(Recipe.difficulty.ilike(f'%{difficulty}%'))
        
        # Order by published date (newest first)
        query = query.order_by(desc(Recipe.published_at))
        
        # Paginate results
        recipes_pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        recipes_data = []
        for recipe in recipes_pagination.items:
            recipe_dict = recipe.to_dict(include_user=True)
            recipes_data.append(recipe_dict)
        
        return jsonify({
            "recipes": recipes_data,
            "pagination": {
                "page": page,
                "pages": recipes_pagination.pages,
                "per_page": per_page,
                "total": recipes_pagination.total,
                "has_next": recipes_pagination.has_next,
                "has_prev": recipes_pagination.has_prev,
                "next_num": recipes_pagination.next_num,
                "prev_num": recipes_pagination.prev_num
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch public recipes", "details": str(e)}), 500


@bp.route("/public/recipes/<int:recipe_id>", methods=["GET"])
def get_public_recipe(recipe_id):
    """Get a specific public recipe by ID."""
    try:
        recipe = Recipe.query.filter(
            Recipe.id == recipe_id,
            Recipe.is_public == True
        ).first()
        
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
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Query user's public recipes
        query = Recipe.query.filter(
            Recipe.user_id == user_id,
            Recipe.is_public == True
        ).order_by(desc(Recipe.published_at))
        
        # Paginate results
        recipes_pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
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
        
        return jsonify({
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
                "prev_num": recipes_pagination.prev_num
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch user recipes", "details": str(e)}), 500


@bp.route("/public/recipes/featured", methods=["GET"])
def get_featured_recipes():
    """Get featured public recipes (most recently published)."""
    try:
        limit = min(request.args.get('limit', 10, type=int), 50)  # Max 50 featured
        
        # Get most recently published recipes
        recipes = Recipe.query.filter(
            Recipe.is_public == True
        ).order_by(desc(Recipe.published_at)).limit(limit).all()
        
        recipes_data = []
        for recipe in recipes:
            recipe_dict = recipe.to_dict(include_user=True)
            recipes_data.append(recipe_dict)
        
        return jsonify({"recipes": recipes_data}), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch featured recipes", "details": str(e)}), 500


@bp.route("/public/stats", methods=["GET"])
def get_public_stats():
    """Get public statistics about the platform."""
    try:
        # Count public recipes
        public_recipes_count = Recipe.query.filter(Recipe.is_public == True).count()
        
        # Count users with public recipes
        users_with_public_recipes = db.session.query(Recipe.user_id).filter(
            Recipe.is_public == True
        ).distinct().count()
        
        # Get recent activity (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_recipes = Recipe.query.filter(
            Recipe.is_public == True,
            Recipe.published_at >= thirty_days_ago
        ).count()
        
        return jsonify({
            "public_recipes": public_recipes_count,
            "contributing_users": users_with_public_recipes,
            "recent_recipes": recent_recipes
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch statistics", "details": str(e)}), 500
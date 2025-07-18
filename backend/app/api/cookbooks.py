import os
import uuid
from pathlib import Path

from flask import Response, jsonify, request, send_file, current_app
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app import db
from app.api import bp
from app.api.auth import require_auth, should_apply_user_filter
from app.models import Cookbook, Recipe
from app.services.google_books_service import GoogleBooksService, GoogleBooksAPIError

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tiff"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/cookbooks", methods=["GET"])
@require_auth
def get_all_cookbooks(current_user) -> Response:
    """Get all public cookbooks with recipe counts. No ownership restrictions for viewing."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "")
    sort_by = request.args.get(
        "sort_by", "title"
    )  # title, author, created_at, recipe_count

    # Base query - all cookbooks are publicly viewable
    query = Cookbook.query

    # Apply search filter if provided
    if search:
        query = query.filter(
            db.or_(
                Cookbook.title.ilike(f"%{search}%"),
                Cookbook.author.ilike(f"%{search}%"),
            )
        )

    # Apply sorting
    if sort_by == "title":
        query = query.order_by(Cookbook.title)
    elif sort_by == "author":
        query = query.order_by(Cookbook.author)
    elif sort_by == "created_at":
        query = query.order_by(Cookbook.created_at.desc())
    elif sort_by == "recipe_count":
        # This requires a subquery to count recipes
        recipe_count_subquery = (
            db.session.query(func.count(Recipe.id))
            .filter(Recipe.cookbook_id == Cookbook.id)
            .filter(Recipe.user_id == current_user.id)
            .scalar_subquery()
        )
        query = query.order_by(recipe_count_subquery.desc())

    # Paginate results
    cookbooks_pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Build response with recipe counts
    cookbooks_data = []
    for cookbook in cookbooks_pagination.items:
        # Get recipe count for this cookbook - admins see all, users see only their own
        recipe_count_query = Recipe.query.filter_by(cookbook_id=cookbook.id)
        if should_apply_user_filter(current_user):
            recipe_count_query = recipe_count_query.filter_by(user_id=current_user.id)
        recipe_count = recipe_count_query.count()

        cookbook_dict = cookbook.to_dict()
        cookbook_dict["recipe_count"] = recipe_count
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
    )


@bp.route("/cookbooks/<int:cookbook_id>", methods=["GET"])
@require_auth
def get_cookbook_detail(current_user, cookbook_id: int) -> Response:
    """Get specific cookbook with its public recipes. Anyone can view any cookbook."""
    search = request.args.get("search", "")

    # Get cookbook - publicly accessible
    cookbook = Cookbook.query.get(cookbook_id)
    if not cookbook:
        return jsonify({"error": "Cookbook not found"}), 404

    # Get recipes for this cookbook - show public recipes from all users + user's own private recipes
    recipe_query = Recipe.query.options(db.joinedload(Recipe.images)).filter_by(
        cookbook_id=cookbook_id
    )

    if should_apply_user_filter(current_user):
        # Regular users see: public recipes from all users + their own private recipes
        recipe_query = recipe_query.filter(
            db.or_(
                Recipe.is_public == True,  # Public recipes from anyone
                Recipe.user_id == current_user.id,  # Own private recipes
            )
        )
    # Admins see all recipes (no additional filter needed)

    # Apply search filter if provided
    if search:
        recipe_query = recipe_query.filter(
            db.or_(
                Recipe.title.ilike(f"%{search}%"),
                Recipe.description.ilike(f"%{search}%"),
            )
        )

    recipes = recipe_query.order_by(
        Recipe.page_number.asc().nullslast(), Recipe.created_at.desc()
    ).all()

    cookbook_dict = cookbook.to_dict()
    cookbook_dict["recipes"] = [recipe.to_dict() for recipe in recipes]
    cookbook_dict["recipe_count"] = len(recipes)

    return jsonify(cookbook_dict)


@bp.route("/cookbooks/<int:cookbook_id>/recipes", methods=["GET"])
@require_auth
def get_cookbook_recipes(current_user, cookbook_id: int) -> Response:
    """Get all public recipes for a specific cookbook. Anyone can view recipes in any cookbook."""
    # Get cookbook - publicly accessible
    cookbook = Cookbook.query.get(cookbook_id)
    if not cookbook:
        return jsonify({"error": "Cookbook not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "")

    # Get paginated recipes for this cookbook with privacy filtering
    recipe_query = Recipe.query.options(db.joinedload(Recipe.images)).filter_by(
        cookbook_id=cookbook_id
    )

    # Apply privacy filtering
    if should_apply_user_filter(current_user):
        # Regular users see: public recipes from all users + their own private recipes
        recipe_query = recipe_query.filter(
            db.or_(
                Recipe.is_public == True,  # Public recipes from anyone
                Recipe.user_id == current_user.id,  # Own private recipes
            )
        )
    # Admins see all recipes (no additional filter needed)

    # Apply search filter if provided
    if search:
        recipe_query = recipe_query.filter(
            db.or_(
                Recipe.title.ilike(f"%{search}%"),
                Recipe.description.ilike(f"%{search}%"),
            )
        )

    recipes_pagination = recipe_query.order_by(
        Recipe.page_number.asc().nullslast(), Recipe.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "cookbook": cookbook.to_dict(),
            "recipes": [recipe.to_dict() for recipe in recipes_pagination.items],
            "total": recipes_pagination.total,
            "pages": recipes_pagination.pages,
            "current_page": page,
            "per_page": per_page,
            "has_next": recipes_pagination.has_next,
            "has_prev": recipes_pagination.has_prev,
        }
    )


@bp.route("/cookbooks", methods=["POST"])
@require_auth
def create_cookbook(current_user) -> Response:
    """Create a new cookbook for the authenticated user."""

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    try:
        cookbook = Cookbook(
            title=title,
            author=data.get("author", "").strip() or None,
            description=data.get("description", "").strip() or None,
            isbn=data.get("isbn", "").strip() or None,
            publisher=data.get("publisher", "").strip() or None,
            cover_image_url=data.get("cover_image_url", "").strip() or None,
            user_id=current_user.id,
        )

        # Handle publication_date if provided
        publication_date = data.get("publication_date")
        if publication_date:
            from datetime import datetime

            try:
                cookbook.publication_date = datetime.fromisoformat(
                    publication_date.replace("Z", "+00:00")
                )
            except ValueError:
                return jsonify({"error": "Invalid publication_date format"}), 400

        db.session.add(cookbook)
        db.session.commit()

        cookbook_dict = cookbook.to_dict()
        cookbook_dict["recipe_count"] = 0  # New cookbook has no recipes

        return (
            jsonify(
                {"message": "Cookbook created successfully", "cookbook": cookbook_dict}
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create cookbook"}), 500


@bp.route("/cookbooks/<int:cookbook_id>", methods=["PUT"])
@require_auth
def update_cookbook(current_user, cookbook_id: int) -> Response:
    """Update cookbook details for the authenticated user."""
    # Get cookbook - admins can update any cookbook, users only their own
    if should_apply_user_filter(current_user):
        cookbook = Cookbook.query.filter_by(
            id=cookbook_id, user_id=current_user.id
        ).first()
    else:
        cookbook = Cookbook.query.get(cookbook_id)
    if not cookbook:
        return jsonify({"error": "Cookbook not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Update fields if provided
        if "title" in data:
            title = data["title"].strip()
            if not title:
                return jsonify({"error": "Title cannot be empty"}), 400
            cookbook.title = title

        if "author" in data:
            cookbook.author = data["author"].strip() or None

        if "description" in data:
            cookbook.description = data["description"].strip() or None

        if "isbn" in data:
            cookbook.isbn = data["isbn"].strip() or None

        if "publisher" in data:
            cookbook.publisher = data["publisher"].strip() or None

        if "cover_image_url" in data:
            cookbook.cover_image_url = data["cover_image_url"].strip() or None

        if "publication_date" in data:
            publication_date = data["publication_date"]
            if publication_date:
                from datetime import datetime

                try:
                    cookbook.publication_date = datetime.fromisoformat(
                        publication_date.replace("Z", "+00:00")
                    )
                except ValueError:
                    return jsonify({"error": "Invalid publication_date format"}), 400
            else:
                cookbook.publication_date = None

        db.session.commit()

        # Get recipe count
        recipe_count = Recipe.query.filter_by(
            cookbook_id=cookbook.id, user_id=current_user.id
        ).count()

        cookbook_dict = cookbook.to_dict()
        cookbook_dict["recipe_count"] = recipe_count

        return jsonify(
            {"message": "Cookbook updated successfully", "cookbook": cookbook_dict}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update cookbook"}), 500


@bp.route("/cookbooks/<int:cookbook_id>", methods=["DELETE"])
@require_auth
def delete_cookbook(current_user, cookbook_id: int) -> Response:
    """Delete a cookbook and its associated recipes for the authenticated user."""
    # Get cookbook - admins can delete any cookbook, users only their own
    if should_apply_user_filter(current_user):
        cookbook = Cookbook.query.filter_by(
            id=cookbook_id, user_id=current_user.id
        ).first()
    else:
        cookbook = Cookbook.query.get(cookbook_id)
    if not cookbook:
        return jsonify({"error": "Cookbook not found"}), 404

    try:
        # Note: Due to foreign key constraints, we might need to handle associated recipes
        # The current model relationships should handle cascading if configured properly
        db.session.delete(cookbook)
        db.session.commit()

        return jsonify({"message": "Cookbook deleted successfully"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete cookbook"}), 500


@bp.route("/cookbooks/search", methods=["GET"])
@require_auth
def search_all_cookbooks(current_user) -> Response:
    """Search for cookbooks across all users by title, author, ISBN, publisher."""
    query_param = request.args.get("q", "").strip()

    if not query_param:
        return jsonify({"cookbooks": []})

    # Search across all cookbooks from all users
    search_query = Cookbook.query.filter(
        db.or_(
            Cookbook.title.ilike(f"%{query_param}%"),
            Cookbook.author.ilike(f"%{query_param}%"),
            Cookbook.publisher.ilike(f"%{query_param}%"),
            Cookbook.isbn.ilike(f"%{query_param}%"),
        )
    ).order_by(Cookbook.title.asc())

    # Limit results to prevent overwhelming the user
    cookbooks = search_query.limit(20).all()

    # Build response with basic cookbook info and creator
    cookbooks_data = []
    for cookbook in cookbooks:
        cookbook_dict = cookbook.to_dict()
        # Add creator information
        if cookbook.user:
            cookbook_dict["creator"] = {
                "id": cookbook.user.id,
                "username": cookbook.user.username,
            }
        else:
            cookbook_dict["creator"] = None

        # Get recipe count for this cookbook
        recipe_count = Recipe.query.filter_by(cookbook_id=cookbook.id).count()
        cookbook_dict["recipe_count"] = recipe_count

        cookbooks_data.append(cookbook_dict)

    return jsonify({"cookbooks": cookbooks_data})


@bp.route("/cookbooks/stats", methods=["GET"])
@require_auth
def get_cookbook_stats(current_user) -> Response:
    """Get cookbook statistics for the authenticated user."""

    # Get basic counts - admins see all, users see only their own
    cookbook_query = Cookbook.query
    recipe_query = Recipe.query
    if should_apply_user_filter(current_user):
        cookbook_query = cookbook_query.filter_by(user_id=current_user.id)
        recipe_query = recipe_query.filter_by(user_id=current_user.id)
    total_cookbooks = cookbook_query.count()
    total_recipes = recipe_query.count()

    # Get cookbooks with recipe counts - admins see all, users see only their own
    cookbook_stats_query = db.session.query(
        Cookbook.id, Cookbook.title, func.count(Recipe.id).label("recipe_count")
    )

    if should_apply_user_filter(current_user):
        # Users see only their own cookbooks and recipes
        cookbook_stats_query = cookbook_stats_query.outerjoin(
            Recipe,
            db.and_(
                Recipe.cookbook_id == Cookbook.id, Recipe.user_id == current_user.id
            ),
        ).filter(Cookbook.user_id == current_user.id)
    else:
        # Admins see all cookbooks and all recipes
        cookbook_stats_query = cookbook_stats_query.outerjoin(
            Recipe, Recipe.cookbook_id == Cookbook.id
        )

    cookbook_stats = cookbook_stats_query.group_by(Cookbook.id, Cookbook.title).all()

    # Calculate additional stats
    cookbooks_with_recipes = sum(
        1 for stats in cookbook_stats if stats.recipe_count > 0
    )
    avg_recipes_per_cookbook = (
        total_recipes / total_cookbooks if total_cookbooks > 0 else 0
    )

    return jsonify(
        {
            "total_cookbooks": total_cookbooks,
            "total_recipes": total_recipes,
            "cookbooks_with_recipes": cookbooks_with_recipes,
            "empty_cookbooks": total_cookbooks - cookbooks_with_recipes,
            "avg_recipes_per_cookbook": round(avg_recipes_per_cookbook, 1),
            "cookbook_details": [
                {
                    "id": stats.id,
                    "title": stats.title,
                    "recipe_count": stats.recipe_count,
                }
                for stats in cookbook_stats
            ],
        }
    )


@bp.route("/cookbooks/<int:cookbook_id>/images", methods=["POST"])
@require_auth
def upload_cookbook_image(current_user, cookbook_id: int) -> Response:
    """Upload an image for a cookbook."""
    # Get cookbook - admins can upload to any cookbook, users only their own
    if should_apply_user_filter(current_user):
        cookbook = Cookbook.query.filter_by(
            id=cookbook_id, user_id=current_user.id
        ).first()
    else:
        cookbook = Cookbook.query.get(cookbook_id)

    if not cookbook:
        return jsonify({"error": "Cookbook not found"}), 404

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    try:
        # Generate unique filename
        filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        file_path = upload_folder / filename

        # Save file
        file.save(str(file_path))

        # Update cookbook with new image URL
        cookbook.cover_image_url = f"/api/images/{filename}"
        db.session.commit()

        return jsonify(
            {
                "message": "Cookbook image uploaded successfully",
                "filename": filename,
                "image_url": cookbook.cover_image_url,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to upload image"}), 500


@bp.route("/cookbooks/search/google-books", methods=["GET"])
@require_auth
def search_google_books(current_user) -> Response:
    """Search for books using Google Books API."""
    query = request.args.get("q", "").strip()
    max_results = request.args.get("max_results", 10, type=int)

    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    # Limit max_results to prevent abuse
    max_results = min(max_results, 20)

    try:
        # Initialize Google Books service
        api_key = current_app.config.get("GOOGLE_BOOKS_API_KEY")
        service = GoogleBooksService(api_key)

        # Search for books
        books = service.search_books(query, max_results)

        return jsonify({"books": books, "total": len(books), "query": query})

    except GoogleBooksAPIError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500


@bp.route("/cookbooks/from-google-books", methods=["POST"])
@require_auth
def create_cookbook_from_google_books(current_user) -> Response:
    """Create a new cookbook from Google Books data."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    google_books_id = data.get("google_books_id")
    if not google_books_id:
        return jsonify({"error": "google_books_id is required"}), 400

    try:
        # Initialize Google Books service
        api_key = current_app.config.get("GOOGLE_BOOKS_API_KEY")
        service = GoogleBooksService(api_key)

        # Get book details from Google Books
        book_data = service.get_book_details(google_books_id)
        if not book_data:
            return jsonify({"error": "Book not found in Google Books"}), 404

        # Check if cookbook already exists (by title and author)
        existing_cookbook = Cookbook.query.filter_by(
            title=book_data["title"],
            author=book_data["author"],
            user_id=current_user.id,
        ).first()

        if existing_cookbook:
            return (
                jsonify(
                    {
                        "error": "A cookbook with this title and author already exists",
                        "existing_cookbook": existing_cookbook.to_dict(),
                    }
                ),
                409,
            )

        # Create new cookbook
        cookbook = Cookbook(
            title=book_data["title"],
            author=book_data["author"] or None,
            description=book_data["description"] or None,
            isbn=book_data["isbn"] or None,
            publisher=book_data["publisher"] or None,
            publication_date=book_data["publication_date"],
            cover_image_url=book_data["thumbnail_url"] or None,
            user_id=current_user.id,
        )

        db.session.add(cookbook)
        db.session.commit()

        cookbook_dict = cookbook.to_dict()
        cookbook_dict["recipe_count"] = 0  # New cookbook has no recipes
        cookbook_dict["source"] = "google_books"
        cookbook_dict["google_books_id"] = google_books_id

        return (
            jsonify(
                {
                    "message": "Cookbook created successfully from Google Books",
                    "cookbook": cookbook_dict,
                }
            ),
            201,
        )

    except GoogleBooksAPIError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create cookbook from Google Books"}), 500


@bp.route("/cookbooks/search/google-books/isbn/<isbn>", methods=["GET"])
@require_auth
def search_google_books_by_isbn(current_user, isbn: str) -> Response:
    """Search for a book by ISBN using Google Books API."""
    if not isbn:
        return jsonify({"error": "ISBN is required"}), 400

    try:
        # Initialize Google Books service
        api_key = current_app.config.get("GOOGLE_BOOKS_API_KEY")
        service = GoogleBooksService(api_key)

        # Search by ISBN
        book = service.search_by_isbn(isbn)

        if not book:
            return jsonify({"error": "Book not found"}), 404

        return jsonify({"book": book, "isbn": isbn})

    except GoogleBooksAPIError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500

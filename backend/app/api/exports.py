"""API endpoints for exporting recipes and cookbooks to various formats"""

import logging
import traceback
from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime

from app.models.recipe import Recipe, Cookbook
from app.models.user import UserRole
from app.api.auth import get_current_user
from app.services.pdf_service import (
    PDFService,
    PDFConfig,
    PageSize,
    PDFTemplate,
    OutputProfile,
)

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint("exports", __name__)


def login_required(f):
    """Decorator to require authentication"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        request.current_user = user
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/recipes/<int:recipe_id>/export/pdf", methods=["GET"])
@login_required
def export_recipe_pdf(recipe_id):
    """Export a single recipe as PDF"""
    try:
        user = request.current_user

        # Get the recipe
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404

        # Check permissions
        is_admin = user.role == UserRole.ADMIN
        if not recipe.can_be_viewed_by(user.id, is_admin):
            return jsonify({"error": "Permission denied"}), 403

        # Get export options from query params
        template = request.args.get("template", "classic")
        page_size = request.args.get("page_size", "letter")
        profile = request.args.get("profile", "digital")
        include_images = request.args.get("include_images", "true").lower() == "true"
        include_notes = request.args.get("include_notes", "true").lower() == "true"

        # Map template string to enum
        template_map = {
            "classic": PDFTemplate.CLASSIC,
            "modern": PDFTemplate.MODERN,
            "minimalist": PDFTemplate.MINIMALIST,
            "book": PDFTemplate.BOOK,
        }

        # Map profile string to enum
        profile_map = {
            "digital": OutputProfile.DIGITAL,
            "home_print": OutputProfile.HOME_PRINT,
            "professional_print": OutputProfile.PROFESSIONAL_PRINT,
        }

        # Create PDF config
        config = PDFConfig(
            page_size=PageSize.LETTER if page_size == "letter" else PageSize.A4,
            template=template_map.get(template, PDFTemplate.CLASSIC),
            profile=profile_map.get(profile, OutputProfile.DIGITAL),
            include_images=include_images,
            include_notes=include_notes,
        )

        # Convert recipe to dict format for PDF service
        recipe_dict = recipe.to_dict(current_user_id=user.id)

        # Generate PDF
        pdf_service = PDFService(config)
        pdf_bytes = pdf_service.generate_recipe_pdf(recipe_dict, config)

        # Create response
        pdf_io = BytesIO(pdf_bytes)
        pdf_io.seek(0)

        # Generate filename
        safe_title = "".join(
            c for c in recipe.title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        safe_title = safe_title.replace(" ", "_")[:50]  # Limit length
        filename = f"{safe_title}.pdf"

        logger.info(f"Generated PDF for recipe {recipe_id} for user {user.id}")

        return send_file(
            pdf_io,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        logger.error(f"Failed to export recipe {recipe_id} as PDF: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to generate PDF"}), 500


@bp.route("/cookbooks/<int:cookbook_id>/export/pdf", methods=["GET"])
@login_required
def export_cookbook_pdf(cookbook_id):
    """Export an entire cookbook as PDF"""
    try:
        user = request.current_user

        # Get the cookbook
        cookbook = Cookbook.query.get(cookbook_id)
        if not cookbook:
            return jsonify({"error": "Cookbook not found"}), 404

        # Check permissions - user must own the cookbook, have purchased it,
        # or have recipes in it
        has_access = False
        is_admin = user.role == UserRole.ADMIN
        if cookbook.user_id == user.id:
            has_access = True
        elif cookbook.is_purchasable and user.has_purchased_cookbook(cookbook_id):
            has_access = True
        elif is_admin:
            has_access = True
        else:
            # Check if user has any recipes in this cookbook
            user_recipe_count = Recipe.query.filter_by(
                cookbook_id=cookbook_id, user_id=user.id
            ).count()
            if user_recipe_count > 0:
                has_access = True

        if not has_access:
            return jsonify({"error": "Permission denied"}), 403

        # Get export options
        template = request.args.get("template", "classic")
        page_size = request.args.get("page_size", "letter")
        profile = request.args.get("profile", "digital")
        include_images = request.args.get("include_images", "true").lower() == "true"
        include_notes = request.args.get("include_notes", "true").lower() == "true"
        include_toc = request.args.get("include_toc", "true").lower() == "true"
        include_index = request.args.get("include_index", "false").lower() == "true"

        # Map template string to enum
        template_map = {
            "classic": PDFTemplate.CLASSIC,
            "modern": PDFTemplate.MODERN,
            "minimalist": PDFTemplate.MINIMALIST,
            "book": PDFTemplate.BOOK,
        }

        # Map profile string to enum
        profile_map = {
            "digital": OutputProfile.DIGITAL,
            "home_print": OutputProfile.HOME_PRINT,
            "professional_print": OutputProfile.PROFESSIONAL_PRINT,
        }

        # Create PDF config
        config = PDFConfig(
            page_size=PageSize.LETTER if page_size == "letter" else PageSize.A4,
            template=template_map.get(template, PDFTemplate.CLASSIC),
            profile=profile_map.get(profile, OutputProfile.DIGITAL),
            include_images=include_images,
            include_notes=include_notes,
            include_toc=include_toc,
            include_index=include_index,
        )

        # Get recipes in the cookbook that the user can access
        is_cookbook_owner = cookbook.user_id == user.id

        if is_cookbook_owner or is_admin:
            # Cookbook owner or admin can export all recipes
            recipes = cookbook.recipes
        elif cookbook.is_purchasable and user.has_purchased_cookbook(cookbook_id):
            # Purchaser can export all recipes
            recipes = cookbook.recipes
        else:
            # User can only export their own recipes from this cookbook
            recipes = Recipe.query.filter_by(
                cookbook_id=cookbook_id, user_id=user.id
            ).all()

        if not recipes:
            return jsonify({"error": "No recipes available to export"}), 400

        # Convert to dict format
        cookbook_dict = cookbook.to_dict(current_user_id=user.id)
        recipes_dict = [
            recipe.to_dict(current_user_id=user.id, is_admin=is_cookbook_owner or is_admin)
            for recipe in recipes
        ]

        # Generate PDF
        pdf_service = PDFService(config)
        pdf_bytes = pdf_service.generate_cookbook_pdf(
            cookbook_dict, recipes_dict, config
        )

        # Create response
        pdf_io = BytesIO(pdf_bytes)
        pdf_io.seek(0)

        # Generate filename
        safe_title = "".join(
            c for c in cookbook.title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        safe_title = safe_title.replace(" ", "_")[:50]
        filename = f"{safe_title}_cookbook.pdf"

        logger.info(f"Generated PDF for cookbook {cookbook_id} for user {user.id}")

        return send_file(
            pdf_io,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        logger.error(f"Failed to export cookbook {cookbook_id} as PDF: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to generate PDF"}), 500


@bp.route("/recipes/export/pdf", methods=["POST"])
@login_required
def export_recipes_pdf():
    """Export multiple recipes as a PDF collection"""
    try:
        user = request.current_user
        data = request.get_json()

        recipe_ids = data.get("recipe_ids", [])
        if not recipe_ids:
            return jsonify({"error": "No recipes specified"}), 400

        # Get and validate recipes
        recipes = []
        for recipe_id in recipe_ids:
            recipe = Recipe.query.get(recipe_id)
            if recipe and recipe.can_be_viewed_by(
                user.id, getattr(user, "is_admin", False)
            ):
                recipes.append(recipe)

        if not recipes:
            return jsonify({"error": "No accessible recipes found"}), 404

        # Get export options
        title = data.get("title", "My Recipe Collection")
        template = data.get("template", "classic")
        page_size = data.get("page_size", "letter")
        profile = data.get("profile", "digital")
        include_images = data.get("include_images", True)
        include_notes = data.get("include_notes", True)
        include_toc = data.get("include_toc", True)
        include_index = data.get("include_index", False)

        # Map template string to enum
        template_map = {
            "classic": PDFTemplate.CLASSIC,
            "modern": PDFTemplate.MODERN,
            "minimalist": PDFTemplate.MINIMALIST,
            "book": PDFTemplate.BOOK,
        }

        # Map profile string to enum
        profile_map = {
            "digital": OutputProfile.DIGITAL,
            "home_print": OutputProfile.HOME_PRINT,
            "professional_print": OutputProfile.PROFESSIONAL_PRINT,
        }

        # Create PDF config
        config = PDFConfig(
            page_size=PageSize.LETTER if page_size == "letter" else PageSize.A4,
            template=template_map.get(template, PDFTemplate.CLASSIC),
            profile=profile_map.get(profile, OutputProfile.DIGITAL),
            include_images=include_images,
            include_notes=include_notes,
            include_toc=include_toc,
            include_index=include_index,
        )

        # Convert recipes to dict format
        recipes_dict = [recipe.to_dict(current_user_id=user.id) for recipe in recipes]

        # Generate PDF
        pdf_service = PDFService(config)
        pdf_bytes = pdf_service.generate_recipe_collection_pdf(
            recipes_dict, title=title, config=config
        )

        # Create response
        pdf_io = BytesIO(pdf_bytes)
        pdf_io.seek(0)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recipe_collection_{timestamp}.pdf"

        logger.info(
            f"Generated PDF collection of {len(recipes)} recipes for user {user.id}"
        )

        return send_file(
            pdf_io,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        logger.error(f"Failed to export recipe collection as PDF: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to generate PDF"}), 500


@bp.route("/export/options", methods=["GET"])
def get_export_options():
    """Get available export options and templates"""
    return jsonify(
        {
            "templates": [
                {
                    "value": "classic",
                    "label": "Classic",
                    "description": "Traditional professional layout",
                },
                {
                    "value": "modern",
                    "label": "Modern Minimalist",
                    "description": "Clean, contemporary design with ample white space",
                },
                {
                    "value": "book",
                    "label": "Book Style",
                    "description": "Elegant two-column layout",
                },
            ],
            "page_sizes": ["letter", "a4"],
            "profiles": [
                {
                    "value": "digital",
                    "label": "Digital Viewing",
                    "description": "Optimized for screens with smaller file size and hyperlinks (85% image quality, RGB)",
                },
                {
                    "value": "home_print",
                    "label": "Home Printing",
                    "description": "Optimized for standard home printers (90% quality, RGB, no bleed)",
                },
                {
                    "value": "professional_print",
                    "label": "Professional Print Service",
                    "description": "Print-ready with bleed, crop marks, and CMYK colors (95% quality)",
                },
            ],
            "options": {
                "include_images": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include recipe images in the PDF",
                },
                "include_notes": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include recipe notes in the PDF",
                },
                "include_toc": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include table of contents (for cookbooks)",
                },
                "include_index": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include ingredient index (for cookbooks)",
                },
            },
        }
    )

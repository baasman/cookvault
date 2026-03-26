"""
Recipes API Blueprint Package

This package organizes recipe-related API endpoints into logical modules:
- helpers.py: Shared utility functions
- images.py: Image upload and serving endpoints
- engagement.py: Comments, ratings, and notes endpoints
- uploads.py: Recipe upload processing endpoints (single/multi image, text, URL)
- video.py: Video and YouTube processing endpoints
- crud.py: Basic CRUD operations for recipes
- search.py: Search and discovery endpoints
- admin.py: Admin-only operations

Note: The routes are still registered on the main api blueprint (bp) to maintain
backwards compatibility with existing frontend code.
"""

from flask import Blueprint

# Create a sub-blueprint for recipes
# Note: Currently routes are added to the main api bp for backwards compatibility
# In the future, this could be registered as a nested blueprint

# Import modules to register routes (these import from app.api and add routes to bp)
# The actual route registration happens when these modules are imported

# For now, we export the helper functions for use by other modules
from app.api.recipes.helpers import (
    allowed_file,
    process_and_save_image,
    get_image_data_for_ocr,
    safe_int_conversion,
    ALLOWED_EXTENSIONS,
)

__all__ = [
    "allowed_file",
    "process_and_save_image",
    "get_image_data_for_ocr",
    "safe_int_conversion",
    "ALLOWED_EXTENSIONS",
]

# Import route modules to register all recipe routes with the main api blueprint
# This must be at the end to avoid circular imports
from app.api.recipes import routes  # noqa: E402, F401
from app.api.recipes import images  # noqa: E402, F401
from app.api.recipes import engagement  # noqa: E402, F401
from app.api.recipes import video  # noqa: E402, F401

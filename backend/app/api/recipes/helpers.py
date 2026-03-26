"""
Shared helper functions for recipe-related API endpoints.
"""

import re
import uuid
from pathlib import Path
from typing import Any

import requests
from flask import current_app
from werkzeug.utils import secure_filename

from app.models import RecipeImage
from app.services.cloudinary_service import cloudinary_service


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tiff"}


def allowed_file(filename: str) -> bool:
    """Check if a filename has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_and_save_image(
    file, original_filename: str, folder: str = "recipes"
) -> RecipeImage:
    """
    Process and save an image file, using Cloudinary if enabled, otherwise local storage.

    Args:
        file: The uploaded file object
        original_filename: The original filename from the user
        folder: The Cloudinary folder to upload to (if using Cloudinary)

    Returns:
        RecipeImage: The created RecipeImage object
    """
    filename = secure_filename(f"{uuid.uuid4().hex}_{original_filename}")

    # Read file data for Cloudinary upload
    file.seek(0)
    file_data = file.read()
    file.seek(0)  # Reset for local save if needed

    recipe_image = RecipeImage(
        filename=filename,
        original_filename=original_filename,
        file_size=len(file_data),
        content_type=file.content_type or "image/jpeg",
    )

    # Try Cloudinary first if enabled
    if cloudinary_service.is_enabled():
        try:
            current_app.logger.info("Uploading image to Cloudinary...")
            cloudinary_result = cloudinary_service.upload_image(
                file_data, original_filename, folder=folder, generate_thumbnail=True
            )

            # Store Cloudinary information
            recipe_image.cloudinary_public_id = cloudinary_result["public_id"]
            recipe_image.cloudinary_url = cloudinary_result["url"]
            recipe_image.cloudinary_thumbnail_url = cloudinary_result.get(
                "thumbnail_url"
            )
            recipe_image.cloudinary_width = cloudinary_result["width"]
            recipe_image.cloudinary_height = cloudinary_result["height"]
            recipe_image.cloudinary_format = cloudinary_result["format"]
            recipe_image.cloudinary_bytes = cloudinary_result["bytes"]

            # For Cloudinary images, we don't need local file path
            recipe_image.file_path = f"cloudinary:{cloudinary_result['public_id']}"

            current_app.logger.info(
                f"Successfully uploaded to Cloudinary: {cloudinary_result['public_id']}"
            )

        except Exception as e:
            current_app.logger.error(
                f"Cloudinary upload failed, falling back to local storage: {str(e)}"
            )
            # Fall through to local storage

    # Local storage fallback (or primary if Cloudinary not enabled)
    if not recipe_image.cloudinary_public_id:
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        file_path = upload_folder / filename

        # Save file locally
        with open(file_path, "wb") as f:
            f.write(file_data)

        recipe_image.file_path = str(file_path)
        current_app.logger.info(f"Saved image locally: {file_path}")

    return recipe_image


def get_image_data_for_ocr(recipe_image: RecipeImage) -> bytes:
    """
    Get image data for OCR processing, handling both Cloudinary and local images.

    Args:
        recipe_image: RecipeImage object

    Returns:
        bytes: Image data

    Raises:
        Exception: If image cannot be retrieved
    """
    # Check if it's a Cloudinary image
    if recipe_image.file_path.startswith("cloudinary:"):
        if not recipe_image.cloudinary_url:
            raise Exception("Cloudinary image has no URL")

        current_app.logger.info(
            f"Downloading Cloudinary image for OCR: {recipe_image.cloudinary_url}"
        )

        try:
            response = requests.get(recipe_image.cloudinary_url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            current_app.logger.error(f"Failed to download Cloudinary image: {e}")
            raise Exception(f"Failed to download Cloudinary image: {str(e)}")

    # Local image
    else:
        image_path = Path(recipe_image.file_path)
        if not image_path.exists():
            raise Exception(f"Local image file not found: {image_path}")

        current_app.logger.info(f"Reading local image for OCR: {image_path}")
        return image_path.read_bytes()


def safe_int_conversion(value: Any) -> int | None:
    """
    Safely convert a value to an integer, handling ranges and extracting numbers from text.

    Handles cases like:
    - "8-10" -> 9 (average)
    - "4-6 servings" -> 5 (average)
    - "2 to 4" -> 3 (average)
    - "30" -> 30
    - "30 minutes" -> 30

    Args:
        value: The value to convert

    Returns:
        int or None: The converted integer, or None if conversion failed
    """
    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        value_str = value.strip()
        if not value_str:
            return None

        # Handle range values like "8-10", "4-6 servings", "2-3 hours", "2 to 4 servings"
        # Look for patterns like "8-10", "4-6", "2 to 4", etc.
        range_match = re.search(r"(\d+)\s*(?:[-–—]|to)\s*(\d+)", value_str)
        if range_match:
            start_val = int(range_match.group(1))
            end_val = int(range_match.group(2))
            # Take the average of the range, rounded down
            result = (start_val + end_val) // 2
            current_app.logger.info(
                f"Converted range '{value_str}' to {result} for servings field"
            )
            return result

        # Look for single numbers (ignoring text like "servings", "minutes", etc.)
        number_match = re.search(r"(\d+)", value_str)
        if number_match:
            result = int(number_match.group(1))
            current_app.logger.debug(
                f"Extracted number {result} from '{value_str}' for servings field"
            )
            return result

    try:
        return int(value)
    except (ValueError, TypeError):
        current_app.logger.warning(
            f"Could not convert '{value}' to integer for servings field"
        )
        return None

#!/usr/bin/env python3
"""
PDF Cookbook Seeder - Create database entries for PDF cookbooks

This module provides utilities for:
- Creating cookbook entries from PDF files in the database
- Processing and storing recipes from PDF cookbooks
- Associating recipes with cookbook and user accounts
- Handling recipe data conversion and image extraction
"""

import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import json
import re

try:
    from cookbook_db_utils.imports import (
        create_app,
        db,
        User,
        Recipe,
        Cookbook,
        Ingredient,
        Tag,
        Instruction,
        RecipeImage,
        ProcessingJob,
        UserRole,
        UserStatus,
        ProcessingStatus,
        recipe_ingredients,
    )
    from cookbook_db_utils.pdf_processor import extract_pdf_cookbook_text, PDFProcessor
    from cookbook_db_utils.pdf_recipe_parser import PDFRecipeParser

    # Import production-quality services for enhanced processing
    from app.services.recipe_parser import RecipeParser
    from app.services.ocr_service import OCRService

    # For image processing
    try:
        from pdf2image import convert_from_path
    except ImportError:
        convert_from_path = None

    try:
        from PIL import Image
    except ImportError:
        Image = None
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    print("This module requires the full CookVault environment")


class PDFCookbookSeeder:
    """Seed database with PDF cookbook data"""

    def __init__(
        self,
        config_name: str = "development",
        use_llm: bool = True,
        enable_historical_conversions: bool = True,
    ):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name
        self.use_llm = use_llm
        self.enable_historical_conversions = enable_historical_conversions

        # Configure logging for CLI visibility
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Configure Flask app logger for production services
        with self.app.app_context():
            self.app.logger.setLevel(logging.INFO)

            # Add console handler if not already present
            if not self.app.logger.handlers:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.INFO)
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                console_handler.setFormatter(formatter)
                self.app.logger.addHandler(console_handler)

        # Statistics tracking
        self.stats = {
            "recipes_processed": 0,
            "recipes_created": 0,
            "recipes_failed": 0,
            "non_recipe_pages_skipped": 0,
            "ingredients_created": 0,
            "instructions_created": 0,
            "images_created": 0,
            "errors": [],
            # New segmentation-specific stats
            "pages_processed": 0,
            "ocr_fallbacks_used": 0,
            "recipe_segments_found": 0,
            "segmentation_method_used": None,  # 'llm', 'pattern', or 'single'
            "combined_text_chars": 0,
        }

    def seed_pdf_cookbook(
        self,
        pdf_path: str,
        cookbook_metadata: Dict = None,
        user_id: Optional[int] = None,
        dry_run: bool = False,
        overwrite_existing: bool = False,
        use_google_books: bool = True,
        max_pages: Optional[int] = None,
        skip_pages: int = 0,
    ) -> Dict:
        """
        Complete pipeline to seed database with PDF cookbook data.

        Args:
            pdf_path: Path to the PDF cookbook file
            cookbook_metadata: Optional metadata for the cookbook (will use Google Books if None)
            user_id: User ID to associate recipes with (creates admin user if None)
            dry_run: If True, parse but don't commit to database
            overwrite_existing: If True, overwrite existing recipes with same title
            use_google_books: If True, enhance metadata with Google Books API
            max_pages: Maximum number of pages to process (None = all pages)
            skip_pages: Number of pages to skip at the beginning

        Returns:
            Dictionary with processing results and statistics
        """

        # Extract enhanced metadata using Google Books API if requested
        if use_google_books and not cookbook_metadata:
            self.logger.info(
                "📚 Extracting cookbook metadata using Google Books API..."
            )
            try:
                processor = PDFProcessor()
                enhanced_metadata = processor.extract_enhanced_metadata(Path(pdf_path))
                cookbook_metadata = self._convert_google_books_to_cookbook_metadata(
                    enhanced_metadata
                )
                self.logger.info(
                    f"📚 Google Books metadata: '{cookbook_metadata['title']}' by {cookbook_metadata['author']}"
                )
            except Exception as e:
                self.logger.warning(f"Google Books metadata extraction failed: {e}")
                cookbook_metadata = self._extract_basic_metadata_from_path(pdf_path)
        elif not cookbook_metadata:
            cookbook_metadata = self._extract_basic_metadata_from_path(pdf_path)

        self.logger.info(
            f"Starting PDF cookbook seeding: {cookbook_metadata.get('title', 'Unknown')}"
        )

        if dry_run:
            self.logger.info("DRY RUN MODE - No database changes will be made")

        try:
            with self.app.app_context():
                # Step 1: Extract and parse recipes from PDF
                self.logger.info("Step 1: Extracting recipes from PDF...")
                parsed_recipes = self._extract_and_parse_recipes(
                    pdf_path, max_pages, skip_pages
                )

                if not parsed_recipes:
                    raise ValueError("No recipes could be extracted from the PDF")

                # with open("/tmp/parsed_recipes.pkl", 'wb') as f:
                #     pickle.dump(parsed_recipes, f)

                self.logger.info(f"Extracted {len(parsed_recipes)} recipes from PDF")

                # Step 2: Get or create user
                user = self._get_or_create_cookbook_user(user_id)

                # Step 3: Create cookbook entry
                self.logger.info("Step 2: Creating cookbook entry...")
                cookbook = self._create_cookbook_entry(
                    cookbook_metadata, user.id, dry_run
                )
                
                # Step 3.5: Create cookbook cover image from first page
                if cookbook and not dry_run:
                    self.logger.info("Step 2.5: Creating cookbook cover image...")
                    self._create_cookbook_cover_image(pdf_path, cookbook)

                # Step 4: Process and create recipes
                self.logger.info("Step 3: Creating recipe entries...")
                created_recipes = self._create_recipes_from_parsed_data(
                    parsed_recipes,
                    cookbook,
                    user,
                    pdf_path,
                    dry_run,
                    overwrite_existing,
                )

                # Step 5: Commit or rollback
                if dry_run:
                    self.logger.info("DRY RUN: Rolling back transaction")
                    db.session.rollback()
                else:
                    self.logger.info("Committing database changes...")
                    db.session.commit()

                # Compile results
                results = {
                    "success": True,
                    "cookbook": cookbook.to_dict() if cookbook else None,
                    "recipes_created": len(created_recipes),
                    "total_recipes_found": len(parsed_recipes),
                    "statistics": self.stats,
                    "dry_run": dry_run,
                }

                self.logger.info(
                    f"Successfully processed {len(created_recipes)} recipes"
                )
                return results

        except Exception as e:
            self.logger.error(f"Error during PDF cookbook seeding: {e}")
            try:
                if not dry_run:
                    db.session.rollback()
            except Exception as rollback_error:
                self.logger.warning(f"Error during rollback: {rollback_error}")

            return {
                "success": False,
                "error": str(e),
                "statistics": self.stats,
                "dry_run": dry_run,
            }

    def _extract_and_parse_recipes(
        self, pdf_path: str, max_pages: Optional[int] = None, skip_pages: int = 0
    ) -> List[Dict]:
        """Extract and parse recipes from PDF using production-quality processing with intelligent segmentation"""
        try:
            # Initialize production services
            ocr_service = OCRService()
            recipe_parser = RecipeParser()

            self.logger.info(
                "Using production-quality OCR and recipe parsing services with intelligent segmentation"
            )

            # Step 1: Convert PDF pages to images for OCR processing
            pdf_processor = PDFProcessor(use_llm=self.use_llm)
            pdf_images = self._extract_pdf_pages_as_images(
                pdf_path, max_pages, skip_pages
            )

            if not pdf_images:
                self.logger.warning(
                    "No images could be extracted from PDF, falling back to text extraction"
                )
                return self._fallback_text_extraction(pdf_path, max_pages, skip_pages)

            # Step 2: Use production OCR service for quality-aware text extraction from all pages
            self.logger.info(
                f"Step 1/4: Processing {len(pdf_images)} pages with production OCR service..."
            )

            try:
                # Always use multi-image OCR for consistency, even for single pages
                multi_ocr_result = ocr_service.extract_text_from_multiple_images(
                    pdf_images
                )
                self.logger.info(
                    f"OCR completed: success_rate={multi_ocr_result['processing_summary']['success_rate']:.1f}%, "
                    f"overall_quality={multi_ocr_result['overall_quality']:.1f}/10"
                )

                # Extract and combine all text from OCR results
                extracted_texts = []
                for i, result in enumerate(multi_ocr_result["results"]):
                    self.stats["pages_processed"] += 1
                    if result["text"].strip():
                        extracted_texts.append(result["text"])
                        # Track OCR fallback usage
                        if result.get("fallback_used", False):
                            self.stats["ocr_fallbacks_used"] += 1
                        self.logger.info(
                            f"Page {i+1}: {len(result['text'])} chars, "
                            f"method={result['method']}, quality={result.get('quality_score', 'N/A')}"
                        )

                if not extracted_texts:
                    self.logger.warning("No text extracted from any PDF pages")
                    return []

                # Step 3: Combine all extracted text
                self.logger.info(
                    f"Step 2/4: Combining text from {len(extracted_texts)} pages..."
                )
                combined_text = "\n\n--- PAGE BREAK ---\n\n".join(extracted_texts)
                self.stats["combined_text_chars"] = len(combined_text)
                self.logger.info(
                    f"Combined text length: {len(combined_text)} characters"
                )

                # Step 4: Segment combined text into individual recipes using LLM
                self.logger.info("Step 3/4: Segmenting text into individual recipes...")
                recipe_segments = self._segment_ocr_text_into_recipes(combined_text)

                if not recipe_segments:
                    self.logger.warning(
                        "No recipe segments found, trying simple pattern-based segmentation..."
                    )
                    # Fallback to simple segmentation
                    simple_segments = self._simple_text_segmentation(combined_text)
                    if simple_segments and len(simple_segments) > 1:
                        # Convert simple segments to proper format
                        recipe_segments = []
                        for i, segment in enumerate(simple_segments):
                            if segment.strip():
                                recipe_segments.append(
                                    {
                                        "title": f"Recipe {i+1}",
                                        "full_text": segment,
                                        "confidence": 5,  # Lower confidence for pattern-based
                                    }
                                )
                        self.stats["segmentation_method_used"] = "pattern"
                    else:
                        self.stats["segmentation_method_used"] = "single"
                else:
                    self.stats["segmentation_method_used"] = "llm"

                if not recipe_segments:
                    self.logger.warning(
                        "No recipe segments found, treating entire text as one recipe"
                    )
                    # Last resort: treat entire combined text as one recipe
                    recipe_segments = [
                        {
                            "title": "Cookbook Recipe",
                            "full_text": combined_text,
                            "confidence": 3,
                        }
                    ]
                    self.stats["segmentation_method_used"] = "single"

                self.stats["recipe_segments_found"] = len(recipe_segments)

                # Step 5: Parse each recipe segment individually
                self.logger.info(
                    f"Step 4/4: Parsing {len(recipe_segments)} individual recipes..."
                )
                successfully_parsed_recipes = []

                for i, segment in enumerate(recipe_segments):
                    try:
                        self.logger.info(
                            f"Parsing recipe {i+1}/{len(recipe_segments)}: '{segment['title'][:50]}...'"
                        )

                        # Parse this individual recipe segment
                        parsed_recipe = recipe_parser.parse_recipe_text(
                            segment["full_text"]
                        )

                        # Validate the parsed result
                        if self._validate_production_recipe(parsed_recipe):
                            # Add segmentation metadata
                            parsed_recipe["segmentation_confidence"] = segment.get(
                                "confidence", 5
                            )
                            parsed_recipe["original_segment_title"] = segment.get(
                                "title", "Unknown"
                            )

                            successfully_parsed_recipes.append(parsed_recipe)
                            self.stats["recipes_processed"] += 1
                            self.stats["recipes_created"] += 1
                            self.logger.info(
                                f"✅ Successfully parsed recipe: '{parsed_recipe.get('title', 'Untitled')}'"
                            )
                        else:
                            self.stats["recipes_failed"] += 1
                            self.logger.warning(
                                f"❌ Failed validation for recipe: '{segment['title'][:50]}...'"
                            )

                    except Exception as e:
                        self.stats["recipes_failed"] += 1
                        error_msg = f"Failed to parse recipe segment {i+1} ('{segment['title'][:50]}...'): {e}"
                        self.logger.error(error_msg)
                        self.stats["errors"].append(error_msg)

                self.logger.info(
                    f"Recipe processing complete: {len(successfully_parsed_recipes)} recipes successfully parsed "
                    f"from {len(recipe_segments)} segments using {self.stats['segmentation_method_used']} segmentation"
                )
                self.logger.info(
                    f"Processing stats: {self.stats['pages_processed']} pages, "
                    f"{self.stats['ocr_fallbacks_used']} OCR fallbacks, "
                    f"{self.stats['combined_text_chars']:,} total characters"
                )
                return successfully_parsed_recipes

            finally:
                # Always clean up temporary image files
                self._cleanup_temp_images(pdf_images)

        except Exception as e:
            self.logger.error(
                f"Production recipe extraction failed: {e}", exc_info=True
            )
            # Fall back to original method
            self.logger.info("Falling back to original text extraction method...")
            return self._fallback_text_extraction(pdf_path, max_pages, skip_pages)

    def _extract_pdf_pages_as_images(
        self, pdf_path: str, max_pages: Optional[int] = None, skip_pages: int = 0
    ) -> List[Path]:
        """Extract PDF pages as images for OCR processing"""
        if not convert_from_path:
            self.logger.warning(
                "pdf2image not available, cannot extract pages as images"
            )
            return []

        try:
            pdf_path_obj = Path(pdf_path)

            # Determine page range
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Convert PDF pages to images
                start_page = skip_pages + 1  # convert_from_path uses 1-based indexing
                if max_pages:
                    end_page = start_page + max_pages - 1
                else:
                    end_page = None

                self.logger.info(
                    f"Converting PDF pages {start_page} to {end_page or 'end'} to images..."
                )

                images = convert_from_path(
                    pdf_path_obj,
                    first_page=start_page,
                    last_page=end_page,
                    dpi=200,  # Good quality for OCR
                    fmt="PNG",
                )

                # Save images to temporary files
                image_paths = []
                for i, image in enumerate(images):
                    image_path = temp_path / f"page_{start_page + i}.png"
                    image.save(image_path, "PNG")

                    # Copy to a permanent temp location
                    permanent_temp_path = Path(
                        tempfile.mktemp(suffix=f"_page_{start_page + i}.png")
                    )
                    shutil.copy2(image_path, permanent_temp_path)
                    image_paths.append(permanent_temp_path)

                self.logger.info(
                    f"Successfully extracted {len(image_paths)} pages as images"
                )
                return image_paths

        except Exception as e:
            self.logger.error(f"Failed to extract PDF pages as images: {e}")
            return []

    def _segment_ocr_text_into_recipes(self, combined_text: str) -> List[Dict]:
        """Use LLM to intelligently segment cookbook text into individual recipes"""
        if not combined_text.strip():
            return []

        self.logger.info("Starting intelligent recipe segmentation using LLM...")

        with self.app.app_context():
            try:
                # Import recipe parser within app context
                from app.services.recipe_parser import RecipeParser

                recipe_parser = RecipeParser()

                # Build concise segmentation prompt to avoid truncation
                segmentation_prompt = f"""
Analyze this cookbook text and identify individual recipe boundaries. Return ONLY a JSON array.

TEXT:
{combined_text[:8000]}{"..." if len(combined_text) > 8000 else ""}

For each recipe found, return:
{{"title": "Recipe Name", "full_text": "Complete recipe text", "confidence": 1-10}}

Rules:
- Look for recipe titles (caps, standalone lines)
- Each recipe needs ingredients + instructions
- Skip indexes, introductions, non-recipe content
- Return ONLY the JSON array, no other text

JSON:"""

                try:
                    response = recipe_parser.client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=8000,  # Increased to handle more recipes
                        temperature=0.1,
                        system="You are an expert cookbook analyzer. Return only valid JSON arrays.",
                        messages=[{"role": "user", "content": segmentation_prompt}],
                    )

                    content = response.content[0].text

                    # Extract JSON from response - handle potentially truncated responses
                    self.logger.debug(
                        f"Segmentation response length: {len(content)} chars"
                    )

                    # Look for JSON array start
                    json_start = content.find("[")
                    if json_start == -1:
                        self.logger.warning(
                            "No JSON array start found in segmentation response"
                        )
                        return []

                    # Try to find the end bracket, but handle truncated responses
                    json_end = content.rfind("]")
                    if json_end == -1 or json_end <= json_start:
                        self.logger.warning(
                            "JSON array appears to be truncated, attempting to fix..."
                        )
                        # Try to find the last complete JSON object and close the array
                        truncated_json = content[json_start:]

                        # Find the last complete object by looking for the last occurrence of '},'
                        last_complete_obj = truncated_json.rfind("},")
                        if last_complete_obj != -1:
                            # Truncate at the last complete object and add closing bracket
                            fixed_json = truncated_json[: last_complete_obj + 1] + "]"
                            self.logger.info(
                                f"Attempting to parse {last_complete_obj + 1} chars of truncated JSON"
                            )
                        else:
                            # Look for at least one complete object
                            first_obj_end = truncated_json.find("}")
                            if first_obj_end != -1:
                                fixed_json = truncated_json[: first_obj_end + 1] + "]"
                                self.logger.info(
                                    "Found at least one complete object in truncated response"
                                )
                            else:
                                self.logger.error(
                                    "No complete JSON objects found in response"
                                )
                                return []
                    else:
                        # Normal case - complete JSON
                        fixed_json = content[json_start : json_end + 1]

                    try:
                        recipe_segments = json.loads(fixed_json)

                        # Validate and filter segments
                        valid_segments = []
                        for segment in recipe_segments:
                            if (
                                isinstance(segment, dict)
                                and segment.get("title")
                                and segment.get("full_text")
                                and len(segment["full_text"].strip())
                                > 50  # Minimum content length
                                and segment.get("confidence", 0) >= 6
                            ):  # Minimum confidence

                                valid_segments.append(segment)

                        self.logger.info(
                            f"Segmented text into {len(valid_segments)} recipe candidates (from {len(recipe_segments)} identified)"
                        )
                        return valid_segments

                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse segmentation JSON: {e}")
                        return []

                except Exception as e:
                    self.logger.error(f"LLM segmentation request failed: {e}")
                    return []

            except ImportError as e:
                self.logger.error(
                    f"Could not import RecipeParser for segmentation: {e}"
                )
                return []

    def _validate_production_recipe(self, parsed_recipe: Dict) -> bool:
        """Validate recipe parsed with production parser"""
        if not parsed_recipe:
            return False

        # Check for essential elements
        if not parsed_recipe.get("title") or not parsed_recipe["title"].strip():
            self.logger.warning("Recipe missing title")
            return False

        # Must have ingredients or instructions
        has_ingredients = (
            parsed_recipe.get("ingredients") and len(parsed_recipe["ingredients"]) > 0
        )
        has_instructions = (
            parsed_recipe.get("instructions") and len(parsed_recipe["instructions"]) > 0
        )

        if not (has_ingredients or has_instructions):
            self.logger.warning("Recipe missing both ingredients and instructions")
            return False

        return True

    def _fallback_text_extraction(
        self, pdf_path: str, max_pages: Optional[int] = None, skip_pages: int = 0
    ) -> List[Dict]:
        """Fallback to original text extraction method"""
        try:
            # Get API key from Flask config if available
            anthropic_api_key = None
            try:
                from flask import current_app

                anthropic_api_key = current_app.config.get("ANTHROPIC_API_KEY")
            except RuntimeError:
                pass

            pdf_result = extract_pdf_cookbook_text(
                pdf_path,
                use_llm=self.use_llm,
                anthropic_api_key=anthropic_api_key,
                max_pages=max_pages,
                skip_pages=skip_pages,
            )

            # Use production recipe parser instead of PDFRecipeParser
            self.logger.info("Parsing PDF cookbook with production recipe parser...")
            recipe_parser = RecipeParser()

            # Split text into reasonable chunks for parsing
            full_text = pdf_result["pdf_data"]["full_text"]
            if not full_text.strip():
                return []

            # Try to parse as a single recipe first
            try:
                parsed_recipe = recipe_parser.parse_recipe_text(full_text)
                if self._validate_production_recipe(parsed_recipe):
                    self.stats["recipes_processed"] += 1
                    return [parsed_recipe]
            except Exception as e:
                self.logger.warning(f"Failed to parse as single recipe: {e}")

            # If that fails, try to segment the text
            segments = self._simple_text_segmentation(full_text)
            parsed_recipes = []

            for i, segment in enumerate(segments):
                if not segment.strip():
                    continue

                try:
                    self.logger.info(f"Parsing text segment {i+1}/{len(segments)}...")
                    parsed_recipe = recipe_parser.parse_recipe_text(segment)

                    if self._validate_production_recipe(parsed_recipe):
                        parsed_recipes.append(parsed_recipe)
                        self.stats["recipes_processed"] += 1
                    else:
                        self.stats["recipes_failed"] += 1

                except Exception as e:
                    error_msg = f"Failed to parse text segment {i+1}: {e}"
                    self.logger.error(error_msg)
                    self.stats["errors"].append(error_msg)
                    self.stats["recipes_failed"] += 1

            return parsed_recipes

        except Exception as e:
            self.logger.error(f"Fallback text extraction failed: {e}")
            return []

    def _simple_text_segmentation(self, text: str) -> List[str]:
        """Simple text segmentation for fallback processing"""
        # Split on likely recipe boundaries
        segments = []

        # Look for recipe titles (lines in all caps or title case)
        lines = text.split("\n")
        current_segment = []

        for line in lines:
            line = line.strip()
            if not line:
                if current_segment:
                    current_segment.append("")
                continue

            # Check if this looks like a recipe title
            if (
                len(line) > 5
                and len(line) < 100
                and (line.isupper() or line.istitle())
                and not line.startswith(
                    ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")
                )
            ):

                # Save previous segment
                if current_segment:
                    segments.append("\n".join(current_segment))
                    current_segment = []

                # Start new segment
                current_segment.append(line)
            else:
                current_segment.append(line)

        # Don't forget the last segment
        if current_segment:
            segments.append("\n".join(current_segment))

        # If no segmentation worked, return the whole text as one segment
        if not segments:
            segments = [text]

        return segments

    def _cleanup_temp_images(self, image_paths: List[Path]) -> None:
        """Clean up temporary image files"""
        for image_path in image_paths:
            try:
                if image_path.exists():
                    image_path.unlink()
                    self.logger.debug(f"Cleaned up temporary image: {image_path}")
            except Exception as e:
                self.logger.warning(
                    f"Failed to clean up temporary image {image_path}: {e}"
                )

    def _get_or_create_cookbook_user(self, user_id: Optional[int]) -> User:
        """Get existing user or create a cookbook admin user"""
        if user_id:
            user = User.query.get(user_id)
            if user:
                return user
            else:
                self.logger.warning(
                    f"User ID {user_id} not found, creating cookbook admin user"
                )

        # Check if cookbook admin user already exists
        cookbook_user = User.query.filter_by(username="pdf_cookbook_admin").first()
        if cookbook_user:
            return cookbook_user

        # Create cookbook admin user
        self.logger.info("Creating PDF cookbook admin user")
        cookbook_user = User(
            username="pdf_cookbook_admin",
            email="cookbook@admin.internal",
            first_name="Cookbook",
            last_name="Admin",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        cookbook_user.set_password("cookbook_admin_2024")  # Secure default password

        db.session.add(cookbook_user)
        db.session.flush()  # Get user ID

        return cookbook_user

    def _create_cookbook_entry(
        self, metadata: Dict, user_id: int, dry_run: bool
    ) -> Cookbook:
        """Create cookbook entry from PDF metadata"""
        # Check if cookbook already exists
        existing_cookbook = Cookbook.query.filter_by(
            title=metadata.get("title"), author=metadata.get("author")
        ).first()

        if existing_cookbook:
            self.logger.info(f"Cookbook already exists: {existing_cookbook.title}")
            return existing_cookbook

        # Create new cookbook
        cookbook = Cookbook(
            title=metadata.get("title", "PDF Cookbook"),
            author=metadata.get("author", "Unknown"),
            description=metadata.get("description", "Cookbook from PDF file"),
            publisher=metadata.get("publisher", ""),
            isbn=metadata.get("isbn", ""),
            publication_date=metadata.get("publication_date"),
            user_id=user_id,
        )

        if not dry_run:
            db.session.add(cookbook)
            db.session.flush()  # Get cookbook ID

        self.logger.info(f"Created cookbook: {cookbook.title}")
        return cookbook

    def _create_cookbook_cover_image(self, pdf_path: str, cookbook: Cookbook) -> None:
        """Create cookbook cover image from first page of PDF"""
        if not convert_from_path or not Image:
            self.logger.warning(
                "PDF image extraction not available (missing pdf2image or PIL)"
            )
            return None

        try:
            # Get the uploads directory from Flask config
            uploads_dir = self.app.config.get("UPLOAD_FOLDER", "/tmp/uploads")
            images_dir = Path(uploads_dir)
            images_dir.mkdir(parents=True, exist_ok=True)

            # Extract first page as image (always page 1, regardless of skip_pages)
            pdf_path_obj = Path(pdf_path)
            images = convert_from_path(
                pdf_path_obj,
                first_page=1,  # Always use first page for cover
                last_page=1,
                dpi=200,  # Good quality for web display
                fmt="PNG",
            )

            if not images:
                self.logger.warning("No cover image extracted from PDF first page")
                return None

            # Generate filename for cookbook cover
            cookbook_name = self._sanitize_filename(cookbook.title)
            filename = f"{cookbook_name}_cover.png"
            image_path = images_dir / filename

            # Save the image
            images[0].save(image_path, "PNG")

            # Set cookbook cover image URL
            cookbook.cover_image_url = f"/api/images/{filename}"
            
            self.logger.info(f"📸 Created cookbook cover image: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to create cookbook cover image: {e}")
            return None

    def _create_recipes_from_parsed_data(
        self,
        parsed_recipes: List[Dict],
        cookbook: Cookbook,
        user: User,
        pdf_path: str,
        dry_run: bool,
        overwrite_existing: bool = False,
    ) -> List[Recipe]:
        """Create recipe database entries from parsed data"""
        created_recipes = []

        for i, recipe_data in enumerate(parsed_recipes):
            try:
                self.logger.info(
                    f"Creating recipe {i+1}/{len(parsed_recipes)}: {recipe_data.get('title', 'Unknown')[:50]}..."
                )

                # Check for existing recipe
                existing_recipe = self._find_existing_recipe(
                    recipe_data.get("title", ""), cookbook.id
                )

                if existing_recipe and not overwrite_existing:
                    self.logger.info(
                        f"⏭️  Skipping existing recipe: {existing_recipe.title[:50]}..."
                    )
                    continue
                elif existing_recipe and overwrite_existing:
                    self.logger.info(
                        f"🔄 Overwriting existing recipe: {existing_recipe.title[:50]}..."
                    )
                    # Delete existing recipe and its related data
                    if not dry_run:
                        self._delete_recipe_and_related_data(existing_recipe)

                # Create recipe entry
                recipe = self._create_recipe_entry(
                    recipe_data, cookbook, user, i + 1, dry_run
                )

                if recipe:
                    created_recipes.append(recipe)
                    self.stats["recipes_created"] += 1

                    # Extract and save recipe image from PDF page
                    page_number = i + 1  # Page numbers are 1-indexed
                    recipe_image = self._extract_and_save_recipe_image(
                        pdf_path, page_number, recipe, cookbook, dry_run
                    )
                    if recipe_image:
                        self.logger.info(
                            f"📸 Associated image with recipe '{recipe.title[:30]}...'"
                        )
                    else:
                        self.logger.debug(
                            f"No image saved for recipe '{recipe.title[:30]}...')"
                        )

            except Exception as e:
                error_msg = f"Failed to create recipe '{recipe_data.get('title', 'Unknown')}': {e}"
                self.logger.error(error_msg)
                self.stats["errors"].append(error_msg)
                self.stats["recipes_failed"] += 1

        return created_recipes

    def _create_recipe_entry(
        self,
        recipe_data: Dict,
        cookbook: Cookbook,
        user: User,
        page_number: int,
        dry_run: bool,
    ) -> Optional[Recipe]:
        """Create a single recipe entry with all related data"""

        # Extract cookbook metadata if available
        cookbook_meta = recipe_data.get("cookbook_metadata", {})

        # Helper function to safely convert timing values
        def safe_int_conversion(value):
            """Safely convert a value to an integer"""
            if value is None:
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                import re

                # Extract the first number from the string
                match = re.search(r"\d+", value.strip())
                if match:
                    return int(match.group())
            return None

        # Create recipe record
        recipe = Recipe(
            title=recipe_data.get("title", "Untitled Recipe"),
            description=recipe_data.get("description", f"Recipe from {cookbook.title}"),
            prep_time=safe_int_conversion(recipe_data.get("prep_time")),
            cook_time=safe_int_conversion(recipe_data.get("cook_time")),
            servings=safe_int_conversion(recipe_data.get("servings")),
            difficulty=recipe_data.get("difficulty", "medium"),
            page_number=page_number,
            user_id=user.id,
            cookbook_id=cookbook.id,
            is_public=True,  # Make recipes public by default
            source=f"PDF cookbook: {cookbook.title}",
        )

        if not dry_run:
            db.session.add(recipe)
            db.session.flush()  # Get recipe ID

        # Create instructions
        instructions = recipe_data.get("instructions", [])
        if isinstance(instructions, list):
            for step_num, instruction_text in enumerate(instructions, 1):
                if instruction_text and instruction_text.strip():
                    instruction = Instruction(
                        recipe_id=recipe.id if not dry_run else 0,
                        step_number=step_num,
                        text=instruction_text.strip(),
                    )
                    if not dry_run:
                        db.session.add(instruction)
                    self.stats["instructions_created"] += 1

        # Create ingredients using production-quality parsing
        ingredients = recipe_data.get("ingredients", [])
        if isinstance(ingredients, list):
            for order, ingredient_text in enumerate(ingredients, 1):
                if ingredient_text and ingredient_text.strip():
                    # Parse ingredient using production method
                    parsed_ingredient = self._parse_ingredient_text(
                        ingredient_text.strip()
                    )

                    if not dry_run:
                        # Find or create ingredient
                        ingredient = Ingredient.query.filter_by(
                            name=parsed_ingredient["name"]
                        ).first()
                        if not ingredient:
                            ingredient = Ingredient(
                                name=parsed_ingredient["name"],
                                category=parsed_ingredient.get("category")
                                or "pdf_cookbook",
                            )
                            db.session.add(ingredient)
                            db.session.flush()
                            self.stats["ingredients_created"] += 1

                        ingredient_id = ingredient.id

                        # Create recipe-ingredient association (avoid duplicates)
                        # Check if this recipe-ingredient association already exists
                        existing_association = db.session.execute(
                            recipe_ingredients.select().where(
                                (recipe_ingredients.c.recipe_id == recipe.id)
                                & (recipe_ingredients.c.ingredient_id == ingredient_id)
                            )
                        ).first()

                        if not existing_association:
                            stmt = recipe_ingredients.insert().values(
                                recipe_id=recipe.id,
                                ingredient_id=ingredient_id,
                                quantity=parsed_ingredient.get("quantity"),
                                unit=parsed_ingredient.get("unit"),
                                preparation=parsed_ingredient.get("preparation"),
                                optional=parsed_ingredient.get("optional", False),
                                order=order,
                            )
                            db.session.execute(stmt)
                        else:
                            self.logger.debug(
                                f"Skipping duplicate ingredient association: recipe_id={recipe.id}, ingredient_id={ingredient_id}"
                            )

        # Add cookbook-specific tags (configurable based on cookbook metadata)
        cookbook_tags = self._get_cookbook_tags(cookbook, recipe_data)
        recipe_tags = recipe_data.get("tags", [])
        all_tags = list(set(cookbook_tags + recipe_tags))

        for tag_name in all_tags:
            if not dry_run:
                # Create tag associated with this recipe
                tag = Tag(name=tag_name, recipe_id=recipe.id)
                db.session.add(tag)

        return recipe

    def _extract_and_save_recipe_image(
        self, pdf_path: str, page_number: int, recipe: Recipe, cookbook: Cookbook, dry_run: bool
    ) -> Optional[RecipeImage]:
        """Extract and save recipe image from PDF page"""
        if not convert_from_path or not Image:
            self.logger.warning(
                "PDF image extraction not available (missing pdf2image or PIL)"
            )
            return None

        try:
            # Get the uploads directory from Flask config
            uploads_dir = self.app.config.get("UPLOAD_FOLDER", "/tmp/uploads")
            images_dir = Path(uploads_dir)
            images_dir.mkdir(parents=True, exist_ok=True)

            # Extract page as image
            pdf_path_obj = Path(pdf_path)
            images = convert_from_path(
                pdf_path_obj,
                first_page=page_number,
                last_page=page_number,
                dpi=200,  # Good quality for web display
                fmt="PNG",
            )

            if not images:
                self.logger.warning(f"No image extracted from page {page_number}")
                return None

            # Generate filename based on cookbook
            cookbook_name = self._sanitize_filename(cookbook.title)
            filename = f"{cookbook_name}_page_{page_number}_recipe_{recipe.id}.png"
            image_path = images_dir / filename

            if not dry_run:
                # Save the image
                images[0].save(image_path, "PNG")

                # Get file info
                file_size = image_path.stat().st_size

                # Create RecipeImage record
                recipe_image = RecipeImage(
                    recipe_id=recipe.id,
                    filename=filename,
                    original_filename=f"page_{page_number}.png",
                    file_path=str(image_path),
                    file_size=file_size,
                    content_type="image/png",
                    image_order=0,  # Primary image
                    page_number=page_number,
                )

                db.session.add(recipe_image)
                self.stats["images_created"] += 1
                self.logger.info(f"📸 Saved recipe image: {filename}")
                return recipe_image
            else:
                self.logger.info(
                    f"📸 DRY RUN: Would save recipe image for page {page_number}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Failed to extract image from page {page_number}: {e}")
            return None

    def _find_existing_recipe(self, title: str, cookbook_id: int) -> Optional[Recipe]:
        """Find existing recipe with the same title in the same cookbook"""
        if not title or not title.strip():
            return None

        return Recipe.query.filter_by(
            title=title.strip(), cookbook_id=cookbook_id
        ).first()

    def _delete_recipe_and_related_data(self, recipe: Recipe) -> None:
        """Delete recipe and all its related data (ingredients, instructions, tags, images)"""
        try:
            self.logger.debug(
                f"Deleting existing recipe data for: {recipe.title[:30]}..."
            )

            # Delete recipe images
            existing_images = RecipeImage.query.filter_by(recipe_id=recipe.id).all()
            for image in existing_images:
                # Delete the actual image file if it exists
                if os.path.exists(image.file_path):
                    try:
                        os.unlink(image.file_path)
                        self.logger.debug(f"Deleted image file: {image.filename}")
                    except Exception as e:
                        self.logger.warning(
                            f"Could not delete image file {image.filename}: {e}"
                        )

                db.session.delete(image)

            # Delete recipe tags
            existing_tags = Tag.query.filter_by(recipe_id=recipe.id).all()
            for tag in existing_tags:
                db.session.delete(tag)

            # Delete recipe instructions
            existing_instructions = Instruction.query.filter_by(
                recipe_id=recipe.id
            ).all()
            for instruction in existing_instructions:
                db.session.delete(instruction)

            # Delete recipe-ingredient associations
            db.session.execute(
                recipe_ingredients.delete().where(
                    recipe_ingredients.c.recipe_id == recipe.id
                )
            )

            # Finally delete the recipe itself
            db.session.delete(recipe)
            db.session.flush()  # Ensure deletion is processed

        except Exception as e:
            self.logger.error(f"Error deleting existing recipe data: {e}")
            raise

    def _validate_parsed_recipe(self, recipe_data: Dict) -> Tuple[bool, str]:
        """
        Validate that parsed recipe has minimum required data.

        Returns:
            Tuple of (is_valid, reason) where reason explains validation result
        """
        if not recipe_data:
            return False, "empty_recipe_data"

        # Must have a title
        if not recipe_data.get("title") or not recipe_data["title"].strip():
            return False, "missing_title"

        # Check if this looks like non-recipe content
        title_lower = recipe_data["title"].lower()
        non_recipe_indicators = [
            "table of contents",
            "index",
            "preface",
            "introduction",
            "acknowledgments",
            "copyright",
            "publisher",
            "contents",
            "chapter",
            "page number",
            "advertisement",
            "notice",
        ]

        for indicator in non_recipe_indicators:
            if indicator in title_lower:
                return False, "non_recipe_content"

        # Must have some content (ingredients or instructions)
        has_ingredients = (
            recipe_data.get("ingredients") and len(recipe_data["ingredients"]) > 0
        )
        has_instructions = (
            recipe_data.get("instructions") and len(recipe_data["instructions"]) > 0
        )

        if not (has_ingredients or has_instructions):
            return False, "missing_content"

        return True, "valid_recipe"

    def _get_cookbook_tags(self, cookbook: Cookbook, recipe_data: Dict) -> List[str]:
        """Get tags appropriate for this cookbook based on metadata"""
        tags = ["pdf_cookbook"]

        # Add era-based tags if publication date is available
        if cookbook.publication_date:
            year = cookbook.publication_date.year
            if year < 1900:
                tags.extend(["historical", "vintage", "19th_century"])
            elif year < 1950:
                tags.extend(["early_20th_century", "traditional"])
            elif year < 2000:
                tags.extend(["mid_20th_century", "classic"])
            else:
                tags.extend(["modern", "contemporary"])

        # Add cookbook-specific metadata as tags
        cookbook_meta = recipe_data.get("cookbook_metadata", {})
        if cookbook_meta.get("era"):
            tags.append(cookbook_meta["era"])

        return tags

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a string for use as a filename"""
        import re

        # Remove non-alphanumeric characters and replace with underscores
        sanitized = re.sub(r"[^\w\s-]", "", filename)
        sanitized = re.sub(r"[-\s]+", "_", sanitized)
        return sanitized.lower()[:50]  # Limit length

    def _convert_google_books_to_cookbook_metadata(
        self, google_books_data: Dict
    ) -> Dict:
        """Convert Google Books metadata to cookbook metadata format"""
        return {
            "title": google_books_data.get("title", "Unknown Cookbook"),
            "author": google_books_data.get("author", "Unknown"),
            "description": google_books_data.get("description", ""),
            "publisher": google_books_data.get("publisher", ""),
            "publication_date": google_books_data.get("publication_date"),
            "isbn": google_books_data.get("isbn_13")
            or google_books_data.get("isbn_10", ""),
            "google_books_id": google_books_data.get("google_books_id"),
            "thumbnail_url": google_books_data.get("thumbnail_url"),
            "source": google_books_data.get("source", "google_books"),
        }

    def _extract_basic_metadata_from_path(self, pdf_path: str) -> Dict:
        """Extract basic metadata from PDF file path when Google Books is not available"""
        pdf_path_obj = Path(pdf_path)
        filename = pdf_path_obj.stem.replace("_", " ").replace("-", " ")

        return {
            "title": filename.title(),
            "author": "Unknown",
            "description": f"Cookbook imported from PDF file: {pdf_path_obj.name}",
            "publisher": "",
            "publication_date": None,
            "isbn": "",
            "source": "filename_extraction",
        }

    def get_seeding_statistics(self) -> Dict:
        """Get current seeding statistics"""
        return self.stats.copy()

    def _parse_ingredient_text(self, ingredient_text: str) -> Dict[str, Any]:
        """Parse ingredient text to extract name, quantity, unit, and preparation."""
        import re

        # Common units pattern
        units = r"\b(?:cups?|cup|tbsp|tsp|teaspoons?|tablespoons?|oz|ounces?|lbs?|pounds?|g|grams?|kg|kilograms?|ml|milliliters?|l|liters?|pint|pints|quart|quarts|gallon|gallons|inch|inches|cloves?|pieces?|slices?|whole|medium|large|small)\b"

        # Pattern to match quantity + unit + ingredient
        pattern = (
            r"^(\d+(?:\.\d+)?(?:/\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*("
            + units
            + r")?\s*(.+)$"
        )

        match = re.match(pattern, ingredient_text.strip(), re.IGNORECASE)

        if match:
            quantity_str = match.group(1)
            unit = match.group(2)
            remaining = match.group(3)

            # Convert quantity to float
            try:
                if "/" in quantity_str:
                    # Handle fractions like "1/2" or "1 1/2"
                    parts = quantity_str.split()
                    if len(parts) == 2:  # "1 1/2"
                        whole, fraction = parts
                        num, denom = fraction.split("/")
                        quantity = float(whole) + float(num) / float(denom)
                    else:  # "1/2"
                        num, denom = quantity_str.split("/")
                        quantity = float(num) / float(denom)
                elif "-" in quantity_str:
                    # Handle ranges like "2-3"
                    quantity = float(quantity_str.split("-")[0])
                else:
                    quantity = float(quantity_str)
            except ValueError:
                quantity = None
        else:
            # No quantity/unit found, treat entire text as ingredient name
            quantity = None
            unit = None
            remaining = ingredient_text

        # Split remaining text to separate ingredient from preparation
        # Look for common preparation indicators
        prep_indicators = [
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

        name = remaining.strip()
        preparation = None

        # Look for preparation at the end
        for prep in prep_indicators:
            if prep in name.lower():
                # Try to split on the preparation word
                parts = name.lower().split(prep)
                if len(parts) == 2 and parts[1].strip() == "":
                    # Preparation is at the end
                    name = parts[0].strip()
                    preparation = prep
                    break
                elif len(parts) == 2 and parts[0].strip():
                    # Preparation is in the middle/end
                    name = parts[0].strip()
                    preparation = prep + parts[1].strip()
                    break

        # Clean up the name
        name = re.sub(r"\s+", " ", name).strip()
        name = name.strip(",")

        return {
            "name": name,
            "quantity": quantity,
            "unit": unit.lower() if unit else None,
            "preparation": preparation,
            "optional": "optional" in ingredient_text.lower(),
            "category": None,  # Could be enhanced with ingredient categorization
        }

    def clear_cookbook_data(self, cookbook_title: str, confirm: bool = False) -> bool:
        """Clear cookbook data (for testing/cleanup)"""
        if not confirm:
            self.logger.warning("⚠️  This will delete cookbook data!")
            response = (
                input(f"Delete cookbook '{cookbook_title}' and all recipes? (y/N): ")
                .lower()
                .strip()
            )
            if response != "y":
                self.logger.info("Operation cancelled.")
                return False

        try:
            with self.app.app_context():
                cookbook = Cookbook.query.filter_by(title=cookbook_title).first()
                if not cookbook:
                    self.logger.warning(f"Cookbook '{cookbook_title}' not found")
                    return False

                # Delete all recipes in this cookbook (cascade should handle related data)
                recipes = Recipe.query.filter_by(cookbook_id=cookbook.id).all()
                for recipe in recipes:
                    db.session.delete(recipe)

                # Delete the cookbook
                db.session.delete(cookbook)

                db.session.commit()
                self.logger.info(
                    f"✅ Deleted cookbook '{cookbook_title}' and {len(recipes)} recipes"
                )
                return True

        except Exception as e:
            self.logger.error(f"❌ Error deleting cookbook data: {e}")
            db.session.rollback()
            return False


def seed_chicago_womens_club_cookbook(
    dry_run: bool = False,
    user_id: Optional[int] = None,
    use_llm: bool = True,
    overwrite_existing: bool = False,
) -> Dict:
    """
    Convenience function to seed the specific 1887 Chicago Women's Club cookbook.

    Args:
        dry_run: If True, parse but don't commit to database
        user_id: User ID to associate recipes with (creates admin user if None)
        use_llm: Whether to use LLM for enhanced text extraction
        overwrite_existing: If True, overwrite existing recipes with same title

    Returns:
        Dictionary with processing results
    """
    pdf_path = "/Users/baasman/projects/cookbook-creator/backend/scripts/seed_data/175_choice_recipes_mainly_furnished_by_members_of_the_chicago_womens_club-1887.pdf"

    cookbook_metadata = {
        "title": "175 Choice Recipes",
        "author": "Members of the Chicago Women's Club",
        "description": "A collection of 175 choice recipes mainly furnished by members of the Chicago Women's Club, published in 1887. This historical cookbook represents traditional American cooking of the late 19th century.",
        "publisher": "Chicago Women's Club",
        "publication_date": datetime(1887, 1, 1),
        "isbn": "",  # ISBN didn't exist in 1887
    }

    seeder = PDFCookbookSeeder(use_llm=use_llm, enable_historical_conversions=True)
    return seeder.seed_pdf_cookbook(
        pdf_path=pdf_path,
        cookbook_metadata=cookbook_metadata,
        user_id=user_id,
        dry_run=dry_run,
        overwrite_existing=overwrite_existing,
        use_google_books=True,  # Enable for backward compatibility
        max_pages=None,  # Process all pages for backward compatibility
        skip_pages=0,  # Don't skip pages for backward compatibility
    )


if __name__ == "__main__":
    # Test the historical cookbook seeder
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("🧪 Testing PDF Cookbook Seeder (DRY RUN)")
    print("=" * 60)

    try:
        result = seed_chicago_womens_club_cookbook(dry_run=True, use_llm=True)

        if result["success"]:
            print("✅ Test successful!")
            print(f"📊 Results:")
            print(
                f"   📖 Cookbook: {result.get('cookbook', {}).get('title', 'Unknown')}"
            )
            print(f"   🍽️  Recipes created: {result['recipes_created']}")
            print(f"   📋 Total recipes found: {result['total_recipes_found']}")
            print(f"   📈 Statistics: {result['statistics']}")
        else:
            print("❌ Test failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback

        traceback.print_exc()

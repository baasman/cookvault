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
from typing import List, Dict, Optional, Tuple

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

    def __init__(self, config_name: str = "development", use_llm: bool = True, enable_historical_conversions: bool = True):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name
        self.use_llm = use_llm
        self.enable_historical_conversions = enable_historical_conversions
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

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
            self.logger.info("📚 Extracting cookbook metadata using Google Books API...")
            try:
                processor = PDFProcessor()
                enhanced_metadata = processor.extract_enhanced_metadata(Path(pdf_path))
                cookbook_metadata = self._convert_google_books_to_cookbook_metadata(enhanced_metadata)
                self.logger.info(f"📚 Google Books metadata: '{cookbook_metadata['title']}' by {cookbook_metadata['author']}")
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
                parsed_recipes = self._extract_and_parse_recipes(pdf_path, max_pages, skip_pages)

                if not parsed_recipes:
                    raise ValueError("No recipes could be extracted from the PDF")

                self.logger.info(f"Extracted {len(parsed_recipes)} recipes from PDF")

                # Step 2: Get or create user
                user = self._get_or_create_cookbook_user(user_id)

                # Step 3: Create cookbook entry
                self.logger.info("Step 2: Creating cookbook entry...")
                cookbook = self._create_cookbook_entry(
                    cookbook_metadata, user.id, dry_run
                )

                # Step 4: Process and create recipes
                self.logger.info("Step 3: Creating recipe entries...")
                created_recipes = self._create_recipes_from_parsed_data(
                    parsed_recipes, cookbook, user, pdf_path, dry_run, overwrite_existing
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
            if not dry_run:
                db.session.rollback()

            return {
                "success": False,
                "error": str(e),
                "statistics": self.stats,
                "dry_run": dry_run,
            }

    def _extract_and_parse_recipes(self, pdf_path: str, max_pages: Optional[int] = None, skip_pages: int = 0) -> List[Dict]:
        """Extract and parse recipes from PDF"""
        # Extract text from PDF using enhanced LLM extraction
        if self.use_llm:
            self.logger.info(
                "Extracting text from PDF using Claude Haiku for enhanced accuracy..."
            )
        else:
            self.logger.info(
                "Extracting text from PDF using pdfplumber (LLM disabled)..."
            )

        # Get API key from Flask config if available
        anthropic_api_key = None
        try:
            from flask import current_app

            anthropic_api_key = current_app.config.get("ANTHROPIC_API_KEY")
        except RuntimeError:
            # Not in Flask app context, will fall back to environment variable
            pass

        pdf_result = extract_pdf_cookbook_text(
            pdf_path, use_llm=self.use_llm, anthropic_api_key=anthropic_api_key,
            max_pages=max_pages, skip_pages=skip_pages
        )

        # Parse recipes using PDF parser
        self.logger.info("Parsing PDF cookbook recipes...")
        parser = PDFRecipeParser(self.app, enable_historical_conversions=self.enable_historical_conversions)
        recipe_segments = parser.segment_cookbook_text(
            pdf_result["pdf_data"]["full_text"]
        )

        # Parse each recipe segment
        parsed_recipes = []
        for i, segment in enumerate(recipe_segments):
            self.stats["recipes_processed"] += 1

            try:
                self.logger.info(
                    f"Parsing recipe {i+1}/{len(recipe_segments)}: {segment.get('title', 'Unknown')[:50]}..."
                )
                parsed_recipe = parser.parse_pdf_recipe(segment)

                # Validate parsed recipe
                is_valid, reason = self._validate_parsed_recipe(parsed_recipe)
                if is_valid:
                    parsed_recipes.append(parsed_recipe)
                elif reason == "non_recipe_content":
                    self.logger.debug(
                        f"Skipping non-recipe content: {segment.get('title', 'Unknown')[:50]}..."
                    )
                    self.stats["non_recipe_pages_skipped"] += 1
                else:
                    self.logger.warning(
                        f"Recipe validation failed ({reason}): {segment.get('title', 'Unknown')[:50]}..."
                    )
                    self.stats["recipes_failed"] += 1

            except Exception as e:
                error_msg = (
                    f"Failed to parse recipe '{segment.get('title', 'Unknown')}': {e}"
                )
                self.logger.error(error_msg)
                self.stats["errors"].append(error_msg)
                self.stats["recipes_failed"] += 1

        return parsed_recipes

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
        cookbook_user = User.query.filter_by(
            username="pdf_cookbook_admin"
        ).first()
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
            self.logger.info(
                f"Cookbook already exists: {existing_cookbook.title}"
            )
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

    def _create_recipes_from_parsed_data(
        self, parsed_recipes: List[Dict], cookbook: Cookbook, user: User, pdf_path: str, dry_run: bool, overwrite_existing: bool = False
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
                    recipe_data.get('title', ''), cookbook.id
                )

                if existing_recipe and not overwrite_existing:
                    self.logger.info(f"⏭️  Skipping existing recipe: {existing_recipe.title[:50]}...")
                    continue
                elif existing_recipe and overwrite_existing:
                    self.logger.info(f"🔄 Overwriting existing recipe: {existing_recipe.title[:50]}...")
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
                        pdf_path, page_number, recipe, dry_run
                    )
                    if recipe_image:
                        self.logger.info(f"📸 Associated image with recipe '{recipe.title[:30]}...'")
                    else:
                        self.logger.debug(f"No image saved for recipe '{recipe.title[:30]}...')")

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

        # Create recipe record
        recipe = Recipe(
            title=recipe_data.get("title", "Untitled Recipe"),
            description=recipe_data.get(
                "description", f"Recipe from {cookbook.title}"
            ),
            prep_time=recipe_data.get("prep_time"),
            cook_time=recipe_data.get("cook_time"),
            servings=recipe_data.get("servings"),
            difficulty=recipe_data.get("difficulty", "medium"),
            page_number=page_number,
            user_id=user.id,
            cookbook_id=cookbook.id,
            is_public=True,  # Make historical recipes public
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

        # Create ingredients (simplified for historical recipes)
        ingredients = recipe_data.get("ingredients", [])
        if isinstance(ingredients, list):
            for order, ingredient_text in enumerate(ingredients, 1):
                if ingredient_text and ingredient_text.strip():
                    # For PDF recipes, we'll store ingredients as simple text
                    # rather than trying to parse them into separate quantity/unit/name
                    ingredient = Ingredient(
                        name=ingredient_text.strip()[:200],  # Truncate if too long
                        category="pdf_cookbook",
                    )

                    if not dry_run:
                        # Check if ingredient already exists
                        existing_ingredient = Ingredient.query.filter_by(
                            name=ingredient.name
                        ).first()
                        if not existing_ingredient:
                            db.session.add(ingredient)
                            db.session.flush()
                            self.stats["ingredients_created"] += 1
                            ingredient_id = ingredient.id
                        else:
                            ingredient_id = existing_ingredient.id

                        # Create recipe-ingredient association (avoid duplicates)
                        # Check if this recipe-ingredient association already exists
                        existing_association = db.session.execute(
                            recipe_ingredients.select().where(
                                (recipe_ingredients.c.recipe_id == recipe.id) &
                                (recipe_ingredients.c.ingredient_id == ingredient_id)
                            )
                        ).first()
                        
                        if not existing_association:
                            stmt = recipe_ingredients.insert().values(
                                recipe_id=recipe.id,
                                ingredient_id=ingredient_id,
                                quantity=None,  # Historical recipes often don't have precise quantities
                                unit=None,
                                preparation=None,
                                optional=False,
                                order=order,
                            )
                            db.session.execute(stmt)
                        else:
                            self.logger.debug(f"Skipping duplicate ingredient association: recipe_id={recipe.id}, ingredient_id={ingredient_id}")

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
        self, pdf_path: str, page_number: int, recipe: Recipe, dry_run: bool
    ) -> Optional[RecipeImage]:
        """Extract and save recipe image from PDF page"""
        if not convert_from_path or not Image:
            self.logger.warning("PDF image extraction not available (missing pdf2image or PIL)")
            return None

        try:
            # Get the uploads directory from Flask config
            uploads_dir = self.app.config.get('UPLOAD_FOLDER', '/tmp/uploads')
            images_dir = Path(uploads_dir)
            images_dir.mkdir(parents=True, exist_ok=True)

            # Extract page as image
            pdf_path_obj = Path(pdf_path)
            images = convert_from_path(
                pdf_path_obj,
                first_page=page_number,
                last_page=page_number,
                dpi=200,  # Good quality for web display
                fmt='PNG'
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
                    page_number=page_number
                )

                db.session.add(recipe_image)
                self.stats["images_created"] += 1
                self.logger.info(f"📸 Saved recipe image: {filename}")
                return recipe_image
            else:
                self.logger.info(f"📸 DRY RUN: Would save recipe image for page {page_number}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to extract image from page {page_number}: {e}")
            return None

    def _find_existing_recipe(self, title: str, cookbook_id: int) -> Optional[Recipe]:
        """Find existing recipe with the same title in the same cookbook"""
        if not title or not title.strip():
            return None

        return Recipe.query.filter_by(
            title=title.strip(),
            cookbook_id=cookbook_id
        ).first()

    def _delete_recipe_and_related_data(self, recipe: Recipe) -> None:
        """Delete recipe and all its related data (ingredients, instructions, tags, images)"""
        try:
            self.logger.debug(f"Deleting existing recipe data for: {recipe.title[:30]}...")

            # Delete recipe images
            existing_images = RecipeImage.query.filter_by(recipe_id=recipe.id).all()
            for image in existing_images:
                # Delete the actual image file if it exists
                if os.path.exists(image.file_path):
                    try:
                        os.unlink(image.file_path)
                        self.logger.debug(f"Deleted image file: {image.filename}")
                    except Exception as e:
                        self.logger.warning(f"Could not delete image file {image.filename}: {e}")

                db.session.delete(image)

            # Delete recipe tags
            existing_tags = Tag.query.filter_by(recipe_id=recipe.id).all()
            for tag in existing_tags:
                db.session.delete(tag)

            # Delete recipe instructions
            existing_instructions = Instruction.query.filter_by(recipe_id=recipe.id).all()
            for instruction in existing_instructions:
                db.session.delete(instruction)

            # Delete recipe-ingredient associations
            db.session.execute(
                recipe_ingredients.delete().where(recipe_ingredients.c.recipe_id == recipe.id)
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
        sanitized = re.sub(r'[^\w\s-]', '', filename)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized.lower()[:50]  # Limit length

    def _convert_google_books_to_cookbook_metadata(self, google_books_data: Dict) -> Dict:
        """Convert Google Books metadata to cookbook metadata format"""
        return {
            "title": google_books_data.get("title", "Unknown Cookbook"),
            "author": google_books_data.get("author", "Unknown"),
            "description": google_books_data.get("description", ""),
            "publisher": google_books_data.get("publisher", ""),
            "publication_date": google_books_data.get("publication_date"),
            "isbn": google_books_data.get("isbn_13") or google_books_data.get("isbn_10", ""),
            "google_books_id": google_books_data.get("google_books_id"),
            "thumbnail_url": google_books_data.get("thumbnail_url"),
            "source": google_books_data.get("source", "google_books")
        }

    def _extract_basic_metadata_from_path(self, pdf_path: str) -> Dict:
        """Extract basic metadata from PDF file path when Google Books is not available"""
        pdf_path_obj = Path(pdf_path)
        filename = pdf_path_obj.stem.replace('_', ' ').replace('-', ' ')

        return {
            "title": filename.title(),
            "author": "Unknown",
            "description": f"Cookbook imported from PDF file: {pdf_path_obj.name}",
            "publisher": "",
            "publication_date": None,
            "isbn": "",
            "source": "filename_extraction"
        }

    def get_seeding_statistics(self) -> Dict:
        """Get current seeding statistics"""
        return self.stats.copy()

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
    dry_run: bool = False, user_id: Optional[int] = None, use_llm: bool = True, overwrite_existing: bool = False
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

#!/usr/bin/env python3
"""
Recipe import script for importing LaTeX recipes from GitHub repository.
This script crawls the drewnutt/CookBook repository and imports all .tex recipe files
using the backend's services directly for maximum accuracy and easier configuration.

Usage:
    python scripts/import_recipes.py                  # Normal import (updates existing to public)
    python scripts/import_recipes.py --update-public-only  # Only update existing recipes to public
    python scripts/import_recipes.py --overwrite      # Delete and reimport all recipes
"""

import os
import sys
import json
import time
import requests
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add the backend directory to the Python path so we can import Flask app
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app import create_app, db
from app.models.recipe import (
    Recipe,
    Cookbook,
    Ingredient,
    Instruction,
    Tag,
    recipe_ingredients,
)
from app.models.user import User, UserStatus, UserRole
from app.services.recipe_parser import RecipeParser
from app.api.recipes import _parse_ingredient_text
from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


@dataclass
class RecipeFile:
    """Represents a recipe file in the repository."""

    name: str
    path: str
    category: str
    download_url: str


class GitHubCrawler:
    """Crawls the GitHub repository to find all recipe files."""

    def __init__(self, repo_owner: str, repo_name: str, branch: str = "master"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.base_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.raw_base_url = (
            f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}"
        )

    def get_repository_structure(self) -> List[Dict]:
        """Get the top-level directory structure of the repository."""
        url = f"{self.base_api_url}/contents"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def get_directory_contents(self, path: str) -> List[Dict]:
        """Get contents of a specific directory."""
        url = f"{self.base_api_url}/contents/{path}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def find_recipe_directories(self) -> List[str]:
        """Find all directories that likely contain recipes."""
        structure = self.get_repository_structure()

        # Known recipe directories from our research
        known_recipe_dirs = {
            "Bread",
            "Breakfast",
            "Curries",
            "Dessert",
            "Entrees",
            "Instant_Pot",
            "Side_Dishes",
            "Substitutes",
        }

        recipe_dirs = []
        for item in structure:
            if item["type"] == "dir" and item["name"] in known_recipe_dirs:
                recipe_dirs.append(item["name"])
                print(f"Found recipe directory: {item['name']}")

        return recipe_dirs

    def find_recipe_files(self) -> List[RecipeFile]:
        """Find all .tex recipe files in the repository."""
        recipe_dirs = self.find_recipe_directories()
        all_recipe_files = []

        for category in recipe_dirs:
            print(f"Scanning {category} directory...")
            try:
                contents = self.get_directory_contents(category)

                for item in contents:
                    if item["type"] == "file" and item["name"].endswith(".tex"):
                        recipe_file = RecipeFile(
                            name=item["name"],
                            path=item["path"],
                            category=category,
                            download_url=item["download_url"],
                        )
                        all_recipe_files.append(recipe_file)
                        print(f"  Found recipe: {item['name']}")

            except Exception as e:
                print(f"Error scanning {category}: {e}")

        print(f"Total recipe files found: {len(all_recipe_files)}")
        return all_recipe_files

    def download_recipe_content(self, recipe_file: RecipeFile) -> str:
        """Download the content of a recipe file."""
        response = requests.get(recipe_file.download_url)
        response.raise_for_status()
        return response.text


class LaTeXProcessor:
    """Processes LaTeX recipe files for AI parsing."""

    @staticmethod
    def clean_latex_content(latex_content: str) -> str:
        """Clean LaTeX content to make it more suitable for AI parsing."""
        # Remove LaTeX comments
        latex_content = re.sub(r"%.*$", "", latex_content, flags=re.MULTILINE)

        # Convert common LaTeX commands to readable text
        replacements = {
            r"\\begin{recipe}": "--- RECIPE START ---",
            r"\\end{recipe}": "--- RECIPE END ---",
            r"\\ingredients": "\nINGREDIENTS:",
            r"\\preparation": "\nPREPARATION:",
            r"\\step": "\nSTEP:",
            r"\\recipetitle{([^}]*)}": r"RECIPE TITLE: \1",
            r"\\preptime{([^}]*)}": r"PREP TIME: \1",
            r"\\baketime{([^}]*)}": r"BAKE TIME: \1",
            r"\\cooktime{([^}]*)}": r"COOK TIME: \1",
            r"\\portions{([^}]*)}": r"SERVES: \1",
            r"\\source{([^}]*)}": r"SOURCE: \1",
            r"\\index{([^}]*)}": r"TAGS: \1",
            r"\\textbf{([^}]*)}": r"\1",
            r"\\emph{([^}]*)}": r"\1",
            r"\\\\": "\n",
        }

        for pattern, replacement in replacements.items():
            latex_content = re.sub(
                pattern, replacement, latex_content, flags=re.IGNORECASE
            )

        # Remove remaining LaTeX commands
        latex_content = re.sub(
            r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})*", "", latex_content
        )

        # Clean up whitespace
        latex_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", latex_content)
        latex_content = re.sub(r"[ \t]+", " ", latex_content)

        return latex_content.strip()

    @staticmethod
    def extract_recipe_metadata(latex_content: str) -> Dict[str, str]:
        """Extract metadata from LaTeX content."""
        metadata = {}

        patterns = {
            "title": r"\\recipetitle\{([^}]*)\}",
            "prep_time": r"\\preptime\{([^}]*)\}",
            "bake_time": r"\\baketime\{([^}]*)\}",
            "cook_time": r"\\cooktime\{([^}]*)\}",
            "portions": r"\\portions\{([^}]*)\}",
            "source": r"\\source\{([^}]*)\}",
            "tags": r"\\index\{([^}]*)\}",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, latex_content, re.IGNORECASE)
            if match:
                metadata[key] = match.group(1).strip()

        return metadata


class DatabaseRecipeUploader:
    """Handles uploading recipes directly to the database using Flask services."""

    def __init__(self, user_id: int, max_retries: int = 3):
        self.user_id = user_id
        self.max_retries = max_retries
        self.recipe_parser = RecipeParser()

    def create_cookbook(
        self, title: str, author: str = "", description: str = ""
    ) -> Optional[int]:
        """Create a new cookbook and return its ID."""
        try:
            cookbook = Cookbook(
                title=title,
                author=author,
                description=description,
                user_id=self.user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            db.session.add(cookbook)
            db.session.commit()

            current_app.logger.info(f"Created cookbook: {title} (ID: {cookbook.id})")
            return cookbook.id

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating cookbook: {e}")
            return None

    def get_or_create_ingredient(self, ingredient_name: str) -> Ingredient:
        """Get existing ingredient or create a new one."""
        # Normalize ingredient name
        normalized_name = ingredient_name.strip().lower()

        # Try to find existing ingredient
        ingredient = Ingredient.query.filter(
            db.func.lower(Ingredient.name) == normalized_name
        ).first()

        if not ingredient:
            ingredient = Ingredient(
                name=ingredient_name.strip(), created_at=datetime.utcnow()
            )
            db.session.add(ingredient)
            db.session.flush()  # Flush to get the ID

        return ingredient

    def create_recipe_tag(self, recipe_id: int, tag_name: str) -> Tag:
        """Create a tag for a specific recipe."""
        # Check if this tag already exists for this recipe
        existing_tag = Tag.query.filter(
            db.and_(
                Tag.recipe_id == recipe_id,
                db.func.lower(Tag.name) == tag_name.strip().lower()
            )
        ).first()

        if not existing_tag:
            tag = Tag(
                recipe_id=recipe_id,
                name=tag_name.strip()
            )
            db.session.add(tag)
            db.session.flush()  # Flush to get the ID
            return tag

        return existing_tag

    def parse_time_string(self, time_str: str) -> Optional[int]:
        """Parse time string and return minutes."""
        if not time_str:
            return None

        time_str = time_str.lower().strip()

        # Extract numbers and time units
        hours_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)", time_str)
        minutes_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)", time_str)

        total_minutes = 0

        if hours_match:
            total_minutes += float(hours_match.group(1)) * 60

        if minutes_match:
            total_minutes += float(minutes_match.group(1))

        return int(total_minutes) if total_minutes > 0 else None

    def upload_recipe(
        self,
        recipe_text: str,
        cookbook_id: Optional[int] = None,
        page_number: Optional[int] = None,
    ) -> Tuple[bool, Dict]:
        """Upload a recipe text using the recipe parser service."""
        try:
            # Parse the recipe text using the RecipeParser service
            current_app.logger.info("Parsing recipe with AI service...")
            parsed_data = self.recipe_parser.parse_recipe_text(recipe_text)

            if not parsed_data:
                return False, {"error": "Failed to parse recipe text"}

            current_app.logger.debug(f"Parsed data: {parsed_data}")

            # Create the recipe object
            recipe = Recipe(
                title=parsed_data.get("title", "Untitled Recipe"),
                description=parsed_data.get("description"),
                prep_time=(
                    self.parse_time_string(str(parsed_data.get("prep_time", "")))
                    if parsed_data.get("prep_time")
                    else None
                ),
                cook_time=(
                    self.parse_time_string(str(parsed_data.get("cook_time", "")))
                    if parsed_data.get("cook_time")
                    else None
                ),
                servings=parsed_data.get("servings"),
                difficulty=parsed_data.get("difficulty"),
                source=(
                    f"Imported from LaTeX cookbook (Page {page_number})"
                    if page_number
                    else "Imported from LaTeX cookbook"
                ),
                cookbook_id=cookbook_id,
                page_number=page_number,
                user_id=self.user_id,
                is_public=True,  # Make imported recipes public by default
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            db.session.add(recipe)
            db.session.flush()  # Flush to get the recipe ID

            # Add ingredients
            ingredients = parsed_data.get("ingredients", [])
            added_ingredient_ids = set()  # Track ingredients already added to avoid duplicates

            for i, ingredient_text in enumerate(ingredients):
                if not ingredient_text or not ingredient_text.strip():
                    continue

                # Parse ingredient text to extract quantity, unit, and name using the API function
                ingredient_parts = _parse_ingredient_text(ingredient_text)

                # Get or create the ingredient
                ingredient = self.get_or_create_ingredient(ingredient_parts["name"])

                # Skip if this ingredient is already added to this recipe
                if ingredient.id in added_ingredient_ids:
                    current_app.logger.warning(f"Duplicate ingredient '{ingredient.name}' found in recipe, skipping")
                    continue

                # Check if this ingredient relationship already exists in database
                existing_relationship = db.session.execute(
                    text("SELECT 1 FROM recipe_ingredients WHERE recipe_id = :recipe_id AND ingredient_id = :ingredient_id"),
                    {"recipe_id": recipe.id, "ingredient_id": ingredient.id}
                ).fetchone()

                if existing_relationship:
                    current_app.logger.warning(f"Ingredient relationship already exists for recipe {recipe.id} and ingredient {ingredient.id}, skipping")
                    added_ingredient_ids.add(ingredient.id)
                    continue

                # Create the recipe-ingredient relationship
                db.session.execute(
                    recipe_ingredients.insert().values(
                        recipe_id=recipe.id,
                        ingredient_id=ingredient.id,
                        quantity=ingredient_parts.get("quantity"),
                        unit=ingredient_parts.get("unit"),
                        preparation=ingredient_parts.get("preparation"),
                        optional=ingredient_parts.get("optional", False),
                        order=i + 1,
                    )
                )

                added_ingredient_ids.add(ingredient.id)

            # Add instructions
            instructions = parsed_data.get("instructions", [])
            for i, instruction_text in enumerate(instructions):
                if not instruction_text or not instruction_text.strip():
                    continue

                instruction = Instruction(
                    recipe_id=recipe.id,
                    step_number=i + 1,
                    text=instruction_text.strip(),
                )
                db.session.add(instruction)

            # Add tags
            tags = parsed_data.get("tags", [])
            for tag_name in tags:
                if not tag_name or not tag_name.strip():
                    continue

                # Create tag for this specific recipe
                self.create_recipe_tag(recipe.id, tag_name)

            # Commit the transaction
            db.session.commit()

            return True, {
                "recipe": {
                    "id": recipe.id,
                    "title": recipe.title,
                    "ingredients_count": len(ingredients),
                    "instructions_count": len(instructions),
                    "tags_count": len(tags),
                }
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error uploading recipe: {e}", exc_info=True)
            return False, {"error": str(e)}



class RecipeImporter:
    """Main class orchestrating the recipe import process."""

    def __init__(self, flask_app, config_name: str = None):
        self.app = flask_app
        self.config_name = config_name or os.environ.get("FLASK_ENV", "development")
        self.crawler = GitHubCrawler("drewnutt", "CookBook")
        self.processor = LaTeXProcessor()
        self.stats = {
            "total_found": 0,
            "successful_imports": 0,
            "failed_imports": 0,
            "errors": [],
        }

    def delete_existing_imported_recipes(self) -> int:
        """Delete all existing imported recipes to allow for clean reimport."""
        with self.app.app_context():
            # Find all recipes with "Imported from LaTeX cookbook" in the source
            imported_recipes = Recipe.query.filter(
                Recipe.source.like('%Imported from LaTeX cookbook%')
            ).all()

            if not imported_recipes:
                current_app.logger.info("No existing imported recipes found to delete")
                return 0

            deleted_count = 0
            for recipe in imported_recipes:
                try:
                    current_app.logger.info(f"Deleting existing recipe '{recipe.title}' (ID: {recipe.id})")

                    # Delete associated data (CASCADE should handle this, but being explicit)
                    # Tags will be deleted automatically via CASCADE
                    # Instructions will be deleted automatically via CASCADE
                    # Recipe-ingredient relationships will be deleted automatically via CASCADE

                    db.session.delete(recipe)
                    deleted_count += 1

                except Exception as e:
                    current_app.logger.error(f"Error deleting recipe {recipe.id}: {e}")

            if deleted_count > 0:
                db.session.commit()
                current_app.logger.info(f"Successfully deleted {deleted_count} existing imported recipes")

            return deleted_count

    def make_imported_recipes_public(self) -> int:
        """Update all existing imported recipes to be public."""
        with self.app.app_context():
            # Find all recipes with "Imported from LaTeX cookbook" in the source
            private_imported_recipes = Recipe.query.filter(
                db.and_(
                    Recipe.source.like('%Imported from LaTeX cookbook%'),
                    Recipe.is_public == False
                )
            ).all()

            if not private_imported_recipes:
                current_app.logger.info("No private imported recipes found to update")
                return 0

            updated_count = 0
            for recipe in private_imported_recipes:
                try:
                    recipe.is_public = True
                    recipe.updated_at = datetime.utcnow()
                    updated_count += 1
                    current_app.logger.info(f"Updated recipe '{recipe.title}' (ID: {recipe.id}) to public")
                except Exception as e:
                    current_app.logger.error(f"Error updating recipe {recipe.id}: {e}")

            if updated_count > 0:
                db.session.commit()
                current_app.logger.info(f"Successfully updated {updated_count} imported recipes to public")

            return updated_count

    def get_or_create_import_user(self) -> int:
        """Get or create a user for importing recipes."""
        with self.app.app_context():
            # Try to find existing import user
            import_user = User.query.filter_by(username="recipe_importer").first()

            if not import_user:
                # Create import user
                from app import bcrypt

                import_user = User(
                    username="recipe_importer",
                    email="import@cookbook.local",
                    password_hash=bcrypt.generate_password_hash(
                        "import_recipes_2024"
                    ).decode("utf-8"),
                    first_name="Recipe",
                    last_name="Importer",
                    role=UserRole.USER,
                    status=UserStatus.ACTIVE,
                    is_verified=True,
                    created_at=datetime.utcnow(),
                )
                db.session.add(import_user)
                db.session.commit()
                current_app.logger.info(
                    f"Created import user with ID: {import_user.id}"
                )

            return import_user.id

    def import_all_recipes(
        self,
        cookbook_title: str = "Imported LaTeX Cookbook",
        resume_from: int = 0,
        save_progress: bool = True,
        overwrite_existing: bool = False,
    ) -> Dict:
        """Import all recipes from the GitHub repository."""
        with self.app.app_context():
            current_app.logger.info("Starting recipe import process...")

            if overwrite_existing:
                # Delete existing imported recipes before importing
                deleted_count = self.delete_existing_imported_recipes()
                if deleted_count > 0:
                    print(f"✅ Deleted {deleted_count} existing imported recipes for clean reimport")
                else:
                    print("ℹ️ No existing imported recipes found to delete")
            else:
                # Update existing imported recipes to be public
                updated_count = self.make_imported_recipes_public()
                if updated_count > 0:
                    print(f"✅ Updated {updated_count} existing imported recipes to public")

            # Get or create import user
            user_id = self.get_or_create_import_user()
            uploader = DatabaseRecipeUploader(user_id)

            # Find all recipe files
            recipe_files = self.crawler.find_recipe_files()
            self.stats["total_found"] = len(recipe_files)

            if not recipe_files:
                current_app.logger.warning("No recipe files found!")
                return self.stats

            # Create cookbook for imported recipes
            current_app.logger.info(f"Creating cookbook: {cookbook_title}")
            cookbook_id = uploader.create_cookbook(
                title=cookbook_title,
                author="Drew Nutting",
                description="Recipes imported from https://github.com/drewnutt/CookBook LaTeX cookbook collection",
            )

            if not cookbook_id:
                current_app.logger.warning(
                    "Failed to create cookbook, importing without cookbook association"
                )
            else:
                current_app.logger.info(f"Created cookbook with ID: {cookbook_id}")

            # Load progress file if resuming
            progress_file = "import_progress.json"
            processed_files = set()

            if resume_from > 0:
                try:
                    with open(progress_file, "r") as f:
                        progress_data = json.load(f)
                        processed_files = set(progress_data.get("processed_files", []))
                        self.stats.update(progress_data.get("stats", self.stats))
                    current_app.logger.info(
                        f"Resuming from recipe {resume_from}, {len(processed_files)} already processed"
                    )
                except FileNotFoundError:
                    current_app.logger.info("No progress file found, starting fresh")

            # Process each recipe file
            for i, recipe_file in enumerate(recipe_files, 1):
                # Skip if already processed (for resume functionality)
                if recipe_file.name in processed_files:
                    print(
                        f"[{i}/{len(recipe_files)}] Skipping already processed: {recipe_file.name}"
                    )
                    continue

                # Skip if we're resuming and haven't reached the resume point
                if i < resume_from:
                    continue

                print(
                    f"\n[{i}/{len(recipe_files)}] Processing {recipe_file.category}/{recipe_file.name}"
                )

                try:
                    # Download recipe content
                    latex_content = self.crawler.download_recipe_content(recipe_file)

                    # Process LaTeX content
                    cleaned_text = self.processor.clean_latex_content(latex_content)

                    # Add category context for better AI parsing
                    categorized_text = (
                        f"RECIPE CATEGORY: {recipe_file.category}\n\n{cleaned_text}"
                    )

                    # Upload to database
                    success, result = uploader.upload_recipe(
                        recipe_text=categorized_text,
                        cookbook_id=cookbook_id,
                        page_number=i,
                    )

                    if success:
                        recipe_info = result.get("recipe", {})
                        print(
                            f"  ✅ Successfully imported: {recipe_info.get('title', 'Untitled')}"
                        )
                        current_app.logger.info(
                            f"Imported recipe: {recipe_info.get('title')} (ID: {recipe_info.get('id')})"
                        )
                        self.stats["successful_imports"] += 1
                        processed_files.add(recipe_file.name)
                    else:
                        error_msg = f"Upload failed: {result}"
                        print(f"  ❌ {error_msg}")
                        current_app.logger.error(error_msg)
                        self.stats["failed_imports"] += 1
                        self.stats["errors"].append(
                            {"file": recipe_file.name, "error": error_msg}
                        )

                    # Save progress periodically
                    if (
                        save_progress
                        and (
                            self.stats["successful_imports"]
                            + self.stats["failed_imports"]
                        )
                        % 5
                        == 0
                    ):
                        progress_data = {
                            "processed_files": list(processed_files),
                            "stats": self.stats,
                            "last_processed_index": i,
                            "cookbook_id": cookbook_id,
                        }
                        with open(progress_file, "w") as f:
                            json.dump(progress_data, f, indent=2)
                        print(f"  💾 Progress saved")

                    # Add delay to avoid overwhelming the AI service
                    time.sleep(1)

                except Exception as e:
                    error_msg = f"Processing error: {str(e)}"
                    print(f"  ❌ {error_msg}")
                    current_app.logger.error(error_msg, exc_info=True)
                    self.stats["failed_imports"] += 1
                    self.stats["errors"].append(
                        {"file": recipe_file.name, "error": error_msg}
                    )

            return self.stats

    def print_summary(self):
        """Print import summary."""
        print("\n" + "=" * 50)
        print("IMPORT SUMMARY")
        print("=" * 50)
        print(f"Total recipes found: {self.stats['total_found']}")
        print(f"Successfully imported: {self.stats['successful_imports']}")
        print(f"Failed imports: {self.stats['failed_imports']}")

        if self.stats["errors"]:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"][:10]:  # Show first 10 errors
                print(f"  - {error['file']}: {error['error']}")
            if len(self.stats["errors"]) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more errors")


def main():
    """Main function."""
    import sys

    # Check for command line arguments
    update_only = len(sys.argv) > 1 and sys.argv[1] == '--update-public-only'
    overwrite_existing = len(sys.argv) > 1 and sys.argv[1] == '--overwrite'

    # Get configuration from environment
    config_name = os.getenv("FLASK_ENV", "development")

    print(f"Using Flask configuration: {config_name}")
    if update_only:
        print("Updating existing imported recipes to be public...\n")
    elif overwrite_existing:
        print("Starting import process with OVERWRITE mode (will delete existing imported recipes)...\n")
    else:
        print("Starting import process with direct database access...\n")

    # Create Flask app
    app = create_app(config_name)

    with app.app_context():
        # Test database connection
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            sys.exit(1)

        # Test AI service configuration
        try:
            anthropic_key = current_app.config.get("ANTHROPIC_API_KEY")
            if not anthropic_key:
                print("❌ ANTHROPIC_API_KEY not configured")
                sys.exit(1)
            print("✅ AI service configuration found")
        except Exception as e:
            print(f"❌ AI service configuration error: {e}")
            sys.exit(1)

    # Create importer
    importer = RecipeImporter(app, config_name)

    if update_only:
        # Only update existing recipes to be public
        updated_count = importer.make_imported_recipes_public()
        print(f"\n✅ Updated {updated_count} existing imported recipes to public status")
    else:
        # Run full import process
        stats = importer.import_all_recipes(overwrite_existing=overwrite_existing)
        importer.print_summary()

        # Save detailed results
        with open("import_results.json", "w") as f:
            json.dump(stats, f, indent=2)

        print(f"\nDetailed results saved to: import_results.json")


if __name__ == "__main__":
    main()

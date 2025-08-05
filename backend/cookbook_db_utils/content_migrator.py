#!/usr/bin/env python3
"""
Content Migrator - Specialized database content migration tools

This module provides advanced export/import functionality for migrating
cookbook content between environments with proper user ownership management.
"""

import json
import shutil
import zipfile
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from cookbook_db_utils.imports import (
    create_app, db, User, Recipe, Cookbook, Ingredient, Tag, Instruction, 
    RecipeImage, ProcessingJob, UserRecipeCollection, RecipeGroup, RecipeNote, 
    RecipeComment
)


class ContentMigrator:
    """Advanced content migration for cookbook database"""
    
    def __init__(self, config_name: str = "development"):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name
        self.export_metadata = {}
        self.import_stats = {}
        self.id_mappings = {}
        
        # Get upload directory from app config
        with self.app.app_context():
            self.upload_dir = Path(self.app.config.get('UPLOAD_FOLDER', 'uploads'))
    
    def export_all_content(self, output_path: Optional[str] = None, 
                          include_user_data: bool = False) -> bool:
        """
        Export all database content including metadata and image files
        
        Args:
            output_path: Output file path (will be a .zip file)
            include_user_data: Whether to include user-specific data
            
        Returns:
            bool: Success status
        """
        try:
            with self.app.app_context():
                print("🔄 Collecting all database content...")
                
                # Collect export metadata
                self.export_metadata = {
                    "export_timestamp": datetime.now().isoformat(),
                    "source_environment": self.config_name,
                    "export_type": "full" if include_user_data else "content_only",
                    "total_records": 0,
                    "images_exported": 0
                }
                
                # Collect all content data
                data = self._collect_comprehensive_data(include_user_data)
                
                # Add metadata to export
                data["_metadata"] = self.export_metadata
                
                # Generate output path if not provided
                if output_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    export_type = "full" if include_user_data else "content"
                    output_path = f"cookbook_{export_type}_export_{timestamp}.zip"
                
                # Ensure output path has .zip extension
                if not output_path.endswith('.zip'):
                    output_path = output_path.rsplit('.', 1)[0] + '.zip'
                
                # Create zip export with images
                return self._create_zip_export(data, output_path)
                
        except Exception as e:
            print(f"❌ Error during export: {e}")
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            return False
    
    def export_content_only(self, output_path: Optional[str] = None) -> bool:
        """
        Export only content data (no user-specific data)
        Ideal for environment migrations
        """
        return self.export_all_content(output_path, include_user_data=False)
    
    def import_to_admin(self, input_path: str, admin_username: str = "admin",
                       create_admin: bool = False, dry_run: bool = False) -> bool:
        """
        Import content and assign ownership to admin user
        Supports both ZIP files (with images) and JSON files (data only)
        
        Args:
            input_path: Input file path (.zip or .json)
            admin_username: Username for admin user
            create_admin: Create admin user if not exists
            dry_run: Test import without committing
            
        Returns:
            bool: Success status
        """
        input_file = Path(input_path)
        if not input_file.exists():
            print(f"❌ Input file not found: {input_path}")
            return False
        
        try:
            with self.app.app_context():
                print(f"📥 Starting content import from {input_path}")
                if dry_run:
                    print("🧪 DRY RUN: No changes will be committed")
                
                # Load import data - handle both ZIP and JSON formats
                data, temp_images_dir = self._load_import_data(input_path)
                if not data:
                    return False
                
                # Display import metadata if available
                if "_metadata" in data:
                    self._display_import_metadata(data["_metadata"])
                
                # Get or create admin user
                admin_user = self._get_or_create_admin_user(admin_username, create_admin)
                if not admin_user:
                    return False
                
                print(f"👤 Using admin user: {admin_user.username} (ID: {admin_user.id})")
                
                # Initialize import statistics
                self.import_stats = {
                    "cookbooks_imported": 0,
                    "recipes_imported": 0,
                    "ingredients_imported": 0,
                    "tags_imported": 0,
                    "instructions_imported": 0,
                    "images_imported": 0,
                    "image_files_copied": 0,
                    "errors": []
                }
                
                # Reset ID mappings for this import
                self.id_mappings = {
                    "cookbooks": {},
                    "recipes": {},
                    "ingredients": {},
                    "tags": {},
                    "users": {0: admin_user.id}  # Map any null/0 user IDs to admin
                }
                
                # Begin transaction
                try:
                    # Import in dependency order
                    success = True
                    success &= self._import_ingredients(data.get("ingredients", []), dry_run)
                    success &= self._import_cookbooks(data.get("cookbooks", []), admin_user.id, dry_run)
                    success &= self._import_recipes(data.get("recipes", []), admin_user.id, dry_run)
                    
                    # Import image files if available
                    if temp_images_dir and not dry_run:
                        success &= self._import_image_files(temp_images_dir)
                    
                    if success and not dry_run:
                        db.session.commit()
                        print("✅ All changes committed to database")
                    elif success and dry_run:
                        db.session.rollback()
                        print("🧪 DRY RUN: All changes rolled back")
                    else:
                        db.session.rollback()
                        print("❌ Import failed: All changes rolled back")
                        return False
                    
                    # Display final statistics
                    self._display_import_statistics()
                    return True
                    
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Import failed: {e}")
                    import traceback
                    print("\nFull traceback:")
                    traceback.print_exc()
                    return False
                finally:
                    # Clean up temporary directory if created
                    if temp_images_dir and temp_images_dir.exists():
                        shutil.rmtree(temp_images_dir)
                
        except Exception as e:
            print(f"❌ Error during import: {e}")
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            return False
    
    def _collect_comprehensive_data(self, include_user_data: bool = False) -> Dict:
        """Collect all database content for export"""
        data = {}
        total_records = 0
        
        # Always export content data
        print("   📚 Collecting cookbooks...")
        data["cookbooks"] = [cookbook.to_dict() for cookbook in Cookbook.query.all()]
        total_records += len(data["cookbooks"])
        
        print("   🍽️  Collecting recipes...")
        data["recipes"] = [recipe.to_dict() for recipe in Recipe.query.all()]
        total_records += len(data["recipes"])
        
        print("   🥕 Collecting ingredients...")
        data["ingredients"] = [ingredient.to_dict() for ingredient in Ingredient.query.all()]
        total_records += len(data["ingredients"])
        
        print("   🏷️  Collecting tags...")
        data["tags"] = [tag.to_dict() for tag in Tag.query.all()]
        total_records += len(data["tags"])
        
        print("   📝 Collecting instructions...")
        data["instructions"] = [instruction.to_dict() for instruction in Instruction.query.all()]
        total_records += len(data["instructions"])
        
        print("   📸 Collecting recipe images...")
        data["recipe_images"] = [image.to_dict() for image in RecipeImage.query.all()]
        total_records += len(data["recipe_images"])
        
        print("   📋 Collecting recipe groups...")
        data["recipe_groups"] = [group.to_dict() for group in RecipeGroup.query.all()]
        total_records += len(data["recipe_groups"])
        
        # Conditionally export user data
        if include_user_data:
            print("   👥 Collecting users...")
            data["users"] = [
                {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role.value,
                    'status': user.status.value,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                }
                for user in User.query.all()
            ]
            total_records += len(data["users"])
            
            print("   📝 Collecting recipe notes...")
            data["recipe_notes"] = [note.to_dict() for note in RecipeNote.query.all()]
            total_records += len(data["recipe_notes"])
            
            print("   💬 Collecting recipe comments...")
            data["recipe_comments"] = [comment.to_dict() for comment in RecipeComment.query.all()]
            total_records += len(data["recipe_comments"])
            
            print("   📑 Collecting user recipe collections...")
            data["user_recipe_collections"] = [collection.to_dict() for collection in UserRecipeCollection.query.all()]
            total_records += len(data["user_recipe_collections"])
        
        self.export_metadata["total_records"] = total_records
        print(f"   ✅ Collected {total_records} total records")
        
        return data
    
    def _create_zip_export(self, data: Dict, output_path: str) -> bool:
        """Create zip export with JSON data and image files"""
        try:
            images_exported = 0
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add JSON data
                json_data = json.dumps(data, indent=2, default=str)
                zipf.writestr('data.json', json_data)
                
                # Add image files
                print("📸 Collecting image files...")
                
                # Create images directory in zip
                for image_data in data.get("recipe_images", []):
                    filename = image_data.get('filename')
                    if filename:
                        # Try to find the image file in upload directory
                        image_path = self.upload_dir / filename
                        if image_path.exists():
                            # Add to zip with images/ prefix
                            zipf.write(image_path, f"images/{filename}")
                            images_exported += 1
                        else:
                            print(f"   ⚠️  Image file not found: {filename}")
                
                # Also check recipe_images subdirectory
                recipe_images_dir = self.upload_dir / "recipe_images"
                if recipe_images_dir.exists():
                    for image_file in recipe_images_dir.glob("*"):
                        if image_file.is_file():
                            zipf.write(image_file, f"images/recipe_images/{image_file.name}")
                            images_exported += 1
            
            # Update metadata with images count
            self.export_metadata["images_exported"] = images_exported
            
            file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
            print(f"✅ Export completed successfully!")
            print(f"   📁 File: {output_path}")
            print(f"   📊 Size: {file_size:.2f} MB")
            print(f"   📈 Records: {self.export_metadata.get('total_records', 0)}")
            print(f"   📸 Images: {images_exported}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating zip export: {e}")
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            return False
    
    def _write_export_file(self, data: Dict, output_path: str) -> bool:
        """Write export data to file (legacy JSON format)"""
        try:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
            print(f"✅ Export completed successfully!")
            print(f"   📁 File: {output_path}")
            print(f"   📊 Size: {file_size:.2f} MB")
            print(f"   📈 Records: {self.export_metadata.get('total_records', 0)}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing export file: {e}")
            return False
    
    def _display_import_metadata(self, metadata: Dict) -> None:
        """Display information about the import file"""
        print(f"\n📋 Import File Metadata:")
        print(f"   🕒 Export timestamp: {metadata.get('export_timestamp', 'Unknown')}")
        print(f"   🌍 Source environment: {metadata.get('source_environment', 'Unknown')}")
        print(f"   📊 Total records: {metadata.get('total_records', 0)}")
        print(f"   📁 Export type: {metadata.get('export_type', 'Unknown')}")
        print("")
    
    def _get_or_create_admin_user(self, username: str, create_if_missing: bool) -> Optional[User]:
        """Get existing admin user or create new one"""
        from app.models.user import UserRole, UserStatus
        
        # Try to find existing admin user
        admin_user = User.query.filter_by(username=username).first()
        if admin_user:
            if admin_user.role != UserRole.ADMIN:
                print(f"⚠️  Warning: User '{username}' exists but is not an admin")
            return admin_user
        
        # Try to find any admin user
        admin_user = User.query.filter_by(role=UserRole.ADMIN).first()
        if admin_user:
            print(f"👤 Using existing admin user: {admin_user.username}")
            return admin_user
        
        # Create admin user if requested
        if create_if_missing:
            print(f"👤 Creating new admin user: {username}")
            try:
                admin_user = User(
                    username=username,
                    email=f"{username}@cookbook.local",
                    first_name="Admin",
                    last_name="User",
                    role=UserRole.ADMIN,
                    status=UserStatus.ACTIVE
                )
                db.session.add(admin_user)
                db.session.flush()  # Get the ID without committing
                return admin_user
            except Exception as e:
                print(f"❌ Error creating admin user: {e}")
                return None
        
        print(f"❌ No admin user found and create_admin=False")
        print("   Use --create-admin flag to create an admin user automatically")
        return None
    
    def _import_ingredients(self, ingredients_data: List[Dict], dry_run: bool) -> bool:
        """Import ingredients with conflict resolution"""
        if not ingredients_data:
            return True
            
        print(f"🥕 Importing {len(ingredients_data)} ingredients...")
        imported = 0
        
        try:
            for ingredient_data in ingredients_data:
                # Check for existing ingredient by name
                existing = Ingredient.query.filter_by(name=ingredient_data['name']).first()
                
                if existing:
                    # Map the old ID to existing ID
                    self.id_mappings["ingredients"][ingredient_data['id']] = existing.id
                    print(f"   ↩️  Ingredient '{ingredient_data['name']}' already exists, using existing")
                else:
                    # Create new ingredient
                    if not dry_run:
                        ingredient = Ingredient(
                            name=ingredient_data['name'],
                            category=ingredient_data.get('category')
                        )
                        db.session.add(ingredient)
                        db.session.flush()
                        self.id_mappings["ingredients"][ingredient_data['id']] = ingredient.id
                    imported += 1
            
            self.import_stats["ingredients_imported"] = imported
            print(f"   ✅ Imported {imported} new ingredients")
            return True
            
        except Exception as e:
            self.import_stats["errors"].append(f"Ingredients import error: {e}")
            print(f"   ❌ Error importing ingredients: {e}")
            return False
    
    def _import_tags(self, tags_data: List[Dict], dry_run: bool) -> bool:
        """Import tags with conflict resolution"""
        if not tags_data:
            return True
            
        print(f"🏷️  Importing {len(tags_data)} tags...")
        imported = 0
        
        try:
            for tag_data in tags_data:
                # Check for existing tag by name
                existing = Tag.query.filter_by(name=tag_data['name']).first()
                
                if existing:
                    # Map the old ID to existing ID
                    self.id_mappings["tags"][tag_data['id']] = existing.id
                    print(f"   ↩️  Tag '{tag_data['name']}' already exists, using existing")
                else:
                    # Create new tag
                    if not dry_run:
                        tag = Tag(
                            name=tag_data['name']
                        )
                        db.session.add(tag)
                        db.session.flush()
                        self.id_mappings["tags"][tag_data['id']] = tag.id
                    imported += 1
            
            self.import_stats["tags_imported"] = imported
            print(f"   ✅ Imported {imported} new tags")
            return True
            
        except Exception as e:
            self.import_stats["errors"].append(f"Tags import error: {e}")
            print(f"   ❌ Error importing tags: {e}")
            return False
    
    def _import_cookbooks(self, cookbooks_data: List[Dict], admin_user_id: int, dry_run: bool) -> bool:
        """Import cookbooks and assign to admin user"""
        if not cookbooks_data:
            return True
            
        print(f"📚 Importing {len(cookbooks_data)} cookbooks...")
        imported = 0
        
        try:
            for cookbook_data in cookbooks_data:
                # Check for existing cookbook by title and author
                existing = Cookbook.query.filter_by(
                    title=cookbook_data['title'],
                    author=cookbook_data.get('author')
                ).first()
                
                if existing:
                    # Map the old ID to existing ID
                    self.id_mappings["cookbooks"][cookbook_data['id']] = existing.id
                    print(f"   ↩️  Cookbook '{cookbook_data['title']}' already exists, using existing")
                else:
                    # Create new cookbook assigned to admin
                    if not dry_run:
                        # Parse publication date if it exists
                        pub_date = None
                        if cookbook_data.get('publication_date'):
                            try:
                                from datetime import datetime
                                pub_date = datetime.fromisoformat(cookbook_data['publication_date'].replace('Z', '+00:00'))
                            except:
                                pass
                        
                        cookbook = Cookbook(
                            title=cookbook_data['title'],
                            description=cookbook_data.get('description'),
                            author=cookbook_data.get('author'),
                            publication_date=pub_date,
                            isbn=cookbook_data.get('isbn'),
                            publisher=cookbook_data.get('publisher'),
                            cover_image_url=cookbook_data.get('cover_image_url'),
                            user_id=admin_user_id  # Assign to admin user
                        )
                        db.session.add(cookbook)
                        db.session.flush()
                        self.id_mappings["cookbooks"][cookbook_data['id']] = cookbook.id
                    imported += 1
            
            self.import_stats["cookbooks_imported"] = imported
            print(f"   ✅ Imported {imported} new cookbooks (assigned to admin)")
            return True
            
        except Exception as e:
            self.import_stats["errors"].append(f"Cookbooks import error: {e}")
            print(f"   ❌ Error importing cookbooks: {e}")
            return False
    
    def _import_recipes(self, recipes_data: List[Dict], admin_user_id: int, dry_run: bool) -> bool:
        """Import recipes with all relationships and assign to admin user"""
        if not recipes_data:
            return True
            
        print(f"🍽️  Importing {len(recipes_data)} recipes...")
        imported = 0
        
        try:
            for recipe_data in recipes_data:
                # Check for existing recipe by title and cookbook
                cookbook_id = None
                if recipe_data.get('cookbook') and recipe_data['cookbook'].get('id'):
                    cookbook_id = self.id_mappings["cookbooks"].get(recipe_data['cookbook']['id'])
                
                existing = None
                if cookbook_id:
                    existing = Recipe.query.filter_by(
                        title=recipe_data['title'],
                        cookbook_id=cookbook_id
                    ).first()
                else:
                    existing = Recipe.query.filter_by(
                        title=recipe_data['title']
                    ).first()
                
                if existing:
                    # Map the old ID to existing ID
                    self.id_mappings["recipes"][recipe_data['id']] = existing.id
                    print(f"   ↩️  Recipe '{recipe_data['title']}' already exists, using existing")
                else:
                    # Create new recipe assigned to admin
                    if not dry_run:
                        recipe = Recipe(
                            title=recipe_data['title'],
                            description=recipe_data.get('description'),
                            prep_time=recipe_data.get('prep_time'),
                            cook_time=recipe_data.get('cook_time'),
                            servings=recipe_data.get('servings'),
                            difficulty=recipe_data.get('difficulty'),
                            page_number=recipe_data.get('page_number'),
                            cookbook_id=cookbook_id,
                            user_id=admin_user_id,  # Assign to admin user
                            is_public=recipe_data.get('is_public', False)  # Preserve original privacy status
                        )
                        db.session.add(recipe)
                        db.session.flush()
                        self.id_mappings["recipes"][recipe_data['id']] = recipe.id
                        
                        # Import recipe instructions
                        self._import_recipe_instructions(recipe, recipe_data.get('instructions', []))
                        
                        # Import recipe tags
                        self._import_recipe_tags(recipe, recipe_data.get('tags', []))
                        
                        # Import recipe images  
                        self._import_recipe_images(recipe, recipe_data.get('images', []))
                        
                    imported += 1
            
            self.import_stats["recipes_imported"] = imported
            print(f"   ✅ Imported {imported} new recipes (assigned to admin, privacy status preserved)")
            return True
            
        except Exception as e:
            self.import_stats["errors"].append(f"Recipes import error: {e}")
            print(f"   ❌ Error importing recipes: {e}")
            return False
    
    def _import_recipe_instructions(self, recipe: Recipe, instructions_data: List[Dict]) -> None:
        """Import instructions for a recipe"""
        for instruction_data in instructions_data:
            instruction = Instruction(
                recipe_id=recipe.id,
                step_number=instruction_data.get('step_number', 1),
                text=instruction_data.get('instruction', '')
            )
            db.session.add(instruction)
            self.import_stats["instructions_imported"] = self.import_stats.get("instructions_imported", 0) + 1
    
    def _import_recipe_tags(self, recipe: Recipe, tags_data: List[Dict]) -> None:
        """Import tags for a recipe"""
        for tag_data in tags_data:
            tag = Tag(
                recipe_id=recipe.id,
                name=tag_data.get('name')
            )
            db.session.add(tag)
            self.import_stats["tags_imported"] = self.import_stats.get("tags_imported", 0) + 1
    
    def _import_recipe_images(self, recipe: Recipe, images_data: List[Dict]) -> None:
        """Import images for a recipe"""
        for image_data in images_data:
            image = RecipeImage(
                recipe_id=recipe.id,
                filename=image_data.get('filename'),
                original_filename=image_data.get('original_filename'),
                file_path=image_data.get('file_path', ''),
                file_size=image_data.get('file_size', 0),
                content_type=image_data.get('content_type', '')
            )
            db.session.add(image)
            self.import_stats["images_imported"] = self.import_stats.get("images_imported", 0) + 1
    
    def _load_import_data(self, input_path: str) -> Tuple[Optional[Dict], Optional[Path]]:
        """
        Load import data from either ZIP or JSON file
        Returns (data, temp_images_dir) where temp_images_dir is None for JSON files
        """
        input_file = Path(input_path)
        
        if input_path.endswith('.zip'):
            # Handle ZIP file
            try:
                import tempfile
                temp_dir = Path(tempfile.mkdtemp(prefix="cookbook_import_"))
                
                with zipfile.ZipFile(input_path, 'r') as zipf:
                    # Extract all files
                    zipf.extractall(temp_dir)
                    
                    # Load JSON data
                    json_file = temp_dir / 'data.json'
                    if not json_file.exists():
                        print("❌ No data.json found in ZIP file")
                        return None, None
                    
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    
                    # Check for images directory
                    images_dir = temp_dir / 'images'
                    if images_dir.exists():
                        print(f"📸 Found images directory with {len(list(images_dir.rglob('*')))} files")
                        return data, images_dir
                    else:
                        print("📸 No images directory found in ZIP file")
                        return data, None
                        
            except Exception as e:
                print(f"❌ Error extracting ZIP file: {e}")
                return None, None
        else:
            # Handle JSON file
            try:
                with open(input_path, 'r') as f:
                    data = json.load(f)
                return data, None
            except Exception as e:
                print(f"❌ Error loading JSON file: {e}")
                return None, None
    
    def _import_image_files(self, images_dir: Path) -> bool:
        """Copy image files from temp directory to upload directory"""
        if not images_dir.exists():
            return True
            
        print("📸 Copying image files...")
        files_copied = 0
        
        try:
            # Ensure upload directory exists
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all files from images directory
            for image_file in images_dir.rglob('*'):
                if image_file.is_file():
                    # Determine destination path
                    relative_path = image_file.relative_to(images_dir)
                    
                    if str(relative_path).startswith('recipe_images/'):
                        # Special handling for recipe_images subdirectory
                        dest_dir = self.upload_dir / "recipe_images"
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest_path = dest_dir / relative_path.name
                    else:
                        # Regular upload directory
                        dest_path = self.upload_dir / relative_path.name
                    
                    # Copy file if it doesn't exist
                    if not dest_path.exists():
                        shutil.copy2(image_file, dest_path)
                        files_copied += 1
                        print(f"   ✅ Copied: {relative_path}")
                    else:
                        print(f"   ↩️  Skipped (exists): {relative_path}")
            
            self.import_stats["image_files_copied"] = files_copied
            print(f"   📸 Total files copied: {files_copied}")
            return True
            
        except Exception as e:
            self.import_stats["errors"].append(f"Image files copy error: {e}")
            print(f"   ❌ Error copying image files: {e}")
            return False
    
    def _display_import_statistics(self) -> None:
        """Display final import statistics"""
        print(f"\n📊 Import Statistics:")
        print(f"   📚 Cookbooks imported: {self.import_stats.get('cookbooks_imported', 0)}")
        print(f"   🍽️  Recipes imported: {self.import_stats.get('recipes_imported', 0)}")
        print(f"   🥕 Ingredients imported: {self.import_stats.get('ingredients_imported', 0)}")
        print(f"   🏷️  Tags imported: {self.import_stats.get('tags_imported', 0)}")
        print(f"   📝 Instructions imported: {self.import_stats.get('instructions_imported', 0)}")
        print(f"   📸 Images imported: {self.import_stats.get('images_imported', 0)}")
        print(f"   🗂️  Image files copied: {self.import_stats.get('image_files_copied', 0)}")
        
        if self.import_stats.get("errors"):
            print(f"\n⚠️  Errors encountered:")
            for error in self.import_stats["errors"]:
                print(f"   - {error}")
        else:
            print(f"\n✅ Import completed successfully with no errors!")
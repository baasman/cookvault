#!/usr/bin/env python3
"""
Database Utilities - Import/Export and analysis tools for Cookbook Creator

This module provides utilities for:
- Importing and exporting data in various formats (JSON, CSV)
- Database statistics and analysis
- Data validation and integrity checks
- Maintenance and optimization tools
"""

import sys
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import io

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent.parent))

from app import create_app, db
from app.models import (
    User, UserSession, Password, Recipe, Cookbook, Ingredient,
    Tag, Instruction, RecipeImage, ProcessingJob, recipe_ingredients
)


class DatabaseUtils:
    """Database utility operations for maintenance and analysis"""
    
    def __init__(self, config_name: str = "development"):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name
    
    def export_data(self, format_type: str = "json", output_path: Optional[str] = None,
                   include_sensitive: bool = False) -> bool:
        """Export all database data to specified format"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_path is None:
            output_path = f"cookbook_export_{timestamp}.{format_type}"
        
        try:
            with self.app.app_context():
                print(f"📤 Exporting database to {format_type.upper()} format...")
                
                if format_type.lower() == "json":
                    return self._export_to_json(output_path, include_sensitive)
                elif format_type.lower() == "csv":
                    return self._export_to_csv(output_path, include_sensitive)
                else:
                    print(f"❌ Unsupported format: {format_type}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error exporting data: {e}")
            return False
    
    def _export_to_json(self, output_path: str, include_sensitive: bool) -> bool:
        """Export data to JSON format"""
        data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "config": self.config_name,
                "include_sensitive": include_sensitive
            },
            "data": {}
        }
        
        # Export users
        users = User.query.all()
        data["data"]["users"] = [user.to_dict(include_sensitive=include_sensitive) for user in users]
        
        # Export cookbooks
        cookbooks = Cookbook.query.all()
        data["data"]["cookbooks"] = [cookbook.to_dict() for cookbook in cookbooks]
        
        # Export ingredients
        ingredients = Ingredient.query.all()
        data["data"]["ingredients"] = [ingredient.to_dict() for ingredient in ingredients]
        
        # Export tags
        tags = Tag.query.all()
        data["data"]["tags"] = [tag.to_dict() for tag in tags]
        
        # Export recipes with relationships
        recipes = Recipe.query.all()
        data["data"]["recipes"] = []
        for recipe in recipes:
            recipe_data = recipe.to_dict()
            
            # Add instructions
            instructions = Instruction.query.filter_by(recipe_id=recipe.id).order_by(Instruction.step_number).all()
            recipe_data["instructions"] = [inst.to_dict() for inst in instructions]
            
            # Add ingredient associations
            recipe_ingredients_data = db.session.query(recipe_ingredients).filter_by(recipe_id=recipe.id).all()
            recipe_data["recipe_ingredients"] = []
            for ri in recipe_ingredients_data:
                ingredient = Ingredient.query.get(ri.ingredient_id)
                recipe_data["recipe_ingredients"].append({
                    "ingredient_name": ingredient.name if ingredient else "Unknown",
                    "quantity": ri.quantity,
                    "unit": ri.unit,
                    "preparation": ri.preparation,
                    "optional": ri.optional,
                    "order": ri.order
                })
            
            data["data"]["recipes"].append(recipe_data)
        
        # Export processing jobs
        if include_sensitive:
            jobs = ProcessingJob.query.all()
            data["data"]["processing_jobs"] = [job.to_dict() for job in jobs]
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"✅ Data exported to: {output_path}")
        return True
    
    def _export_to_csv(self, output_path: str, include_sensitive: bool) -> bool:
        """Export data to CSV format (creates multiple CSV files)"""
        output_dir = Path(output_path).parent
        base_name = Path(output_path).stem
        
        # Export recipes to CSV
        recipes_path = output_dir / f"{base_name}_recipes.csv"
        with open(recipes_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            header = ['id', 'title', 'description', 'cookbook_title', 'prep_time', 'cook_time', 
                     'servings', 'difficulty', 'source', 'created_at']
            writer.writerow(header)
            
            # Write data
            recipes = Recipe.query.all()
            for recipe in recipes:
                cookbook_title = recipe.cookbook.title if recipe.cookbook else ''
                row = [
                    recipe.id, recipe.title, recipe.description, cookbook_title,
                    recipe.prep_time, recipe.cook_time, recipe.servings,
                    recipe.difficulty, recipe.source, recipe.created_at
                ]
                writer.writerow(row)
        
        # Export ingredients to CSV
        ingredients_path = output_dir / f"{base_name}_ingredients.csv"
        with open(ingredients_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'category', 'common_units'])
            
            ingredients = Ingredient.query.all()
            for ingredient in ingredients:
                writer.writerow([ingredient.id, ingredient.name, ingredient.category, ingredient.common_units])
        
        # Export cookbooks to CSV
        cookbooks_path = output_dir / f"{base_name}_cookbooks.csv"
        with open(cookbooks_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'title', 'author', 'publisher', 'isbn', 'publication_date'])
            
            cookbooks = Cookbook.query.all()
            for cookbook in cookbooks:
                writer.writerow([cookbook.id, cookbook.title, cookbook.author, 
                               cookbook.publisher, cookbook.isbn, cookbook.publication_date])
        
        print(f"✅ Data exported to CSV files:")
        print(f"   - {recipes_path}")
        print(f"   - {ingredients_path}")
        print(f"   - {cookbooks_path}")
        return True
    
    def import_data(self, input_path: str, format_type: str = "json", 
                   merge_strategy: str = "skip") -> bool:
        """Import data from specified format"""
        input_file = Path(input_path)
        if not input_file.exists():
            print(f"❌ Input file not found: {input_path}")
            return False
        
        try:
            with self.app.app_context():
                print(f"📥 Importing data from {format_type.upper()} format...")
                
                if format_type.lower() == "json":
                    return self._import_from_json(input_path, merge_strategy)
                else:
                    print(f"❌ Import format not yet supported: {format_type}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error importing data: {e}")
            return False
    
    def _import_from_json(self, input_path: str, merge_strategy: str) -> bool:
        """Import data from JSON format"""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "data" not in data:
            print("❌ Invalid JSON format: missing 'data' key")
            return False
        
        import_data = data["data"]
        stats = {"created": 0, "skipped": 0, "errors": 0}
        
        # Import ingredients first (no dependencies)
        if "ingredients" in import_data:
            print("📥 Importing ingredients...")
            for ing_data in import_data["ingredients"]:
                try:
                    existing = Ingredient.query.filter_by(name=ing_data["name"]).first()
                    if existing and merge_strategy == "skip":
                        stats["skipped"] += 1
                        continue
                    
                    if not existing:
                        ingredient = Ingredient(
                            name=ing_data["name"],
                            category=ing_data.get("category"),
                            common_units=ing_data.get("common_units")
                        )
                        db.session.add(ingredient)
                        stats["created"] += 1
                    
                except Exception as e:
                    print(f"   Error importing ingredient {ing_data.get('name', 'Unknown')}: {e}")
                    stats["errors"] += 1
        
        # Import tags
        if "tags" in import_data:
            print("📥 Importing tags...")
            for tag_data in import_data["tags"]:
                try:
                    existing = Tag.query.filter_by(name=tag_data["name"]).first()
                    if existing and merge_strategy == "skip":
                        stats["skipped"] += 1
                        continue
                    
                    if not existing:
                        tag = Tag(name=tag_data["name"])
                        db.session.add(tag)
                        stats["created"] += 1
                    
                except Exception as e:
                    print(f"   Error importing tag {tag_data.get('name', 'Unknown')}: {e}")
                    stats["errors"] += 1
        
        db.session.commit()
        
        print(f"✅ Import completed:")
        print(f"   Created: {stats['created']}")
        print(f"   Skipped: {stats['skipped']}")
        print(f"   Errors: {stats['errors']}")
        
        return stats["errors"] == 0
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "tables": {},
            "relationships": {},
            "data_quality": {}
        }
        
        try:
            with self.app.app_context():
                # Table counts
                models = [
                    ("users", User),
                    ("cookbooks", Cookbook),
                    ("recipes", Recipe),
                    ("ingredients", Ingredient),
                    ("tags", Tag),
                    ("instructions", Instruction),
                    ("recipe_images", RecipeImage),
                    ("processing_jobs", ProcessingJob),
                    ("user_sessions", UserSession)
                ]
                
                for table_name, model in models:
                    stats["tables"][table_name] = model.query.count()
                
                # Relationship statistics
                stats["relationships"]["recipes_with_cookbooks"] = Recipe.query.filter(Recipe.cookbook_id.isnot(None)).count()
                stats["relationships"]["recipes_without_cookbooks"] = Recipe.query.filter(Recipe.cookbook_id.is_(None)).count()
                stats["relationships"]["recipes_with_ingredients"] = db.session.query(recipe_ingredients).count()
                stats["relationships"]["avg_ingredients_per_recipe"] = (
                    db.session.query(recipe_ingredients).count() / max(stats["tables"]["recipes"], 1)
                )
                
                # Data quality metrics
                stats["data_quality"]["recipes_without_descriptions"] = Recipe.query.filter(
                    (Recipe.description.is_(None)) | (Recipe.description == "")
                ).count()
                
                stats["data_quality"]["recipes_without_times"] = Recipe.query.filter(
                    (Recipe.prep_time.is_(None)) & (Recipe.cook_time.is_(None))
                ).count()
                
                stats["data_quality"]["users_verified"] = User.query.filter_by(is_verified=True).count()
                stats["data_quality"]["active_sessions"] = UserSession.query.filter_by(is_active=True).count()
                
        except Exception as e:
            stats["error"] = str(e)
        
        return stats
    
    def validate_data_integrity(self) -> Dict[str, List[str]]:
        """Validate database integrity and find issues"""
        issues = {
            "orphaned_records": [],
            "missing_required_data": [],
            "data_inconsistencies": [],
            "foreign_key_violations": []
        }
        
        try:
            with self.app.app_context():
                # Check for orphaned instructions
                orphaned_instructions = Instruction.query.filter(
                    ~Instruction.recipe_id.in_(db.session.query(Recipe.id))
                ).all()
                
                for inst in orphaned_instructions:
                    issues["orphaned_records"].append(f"Instruction {inst.id} references non-existent recipe {inst.recipe_id}")
                
                # Check for recipes without instructions
                recipes_without_instructions = Recipe.query.filter(
                    ~Recipe.id.in_(db.session.query(Instruction.recipe_id))
                ).all()
                
                for recipe in recipes_without_instructions:
                    issues["missing_required_data"].append(f"Recipe '{recipe.title}' has no instructions")
                
                # Check for users without verified emails
                unverified_users = User.query.filter_by(is_verified=False).all()
                for user in unverified_users:
                    issues["data_inconsistencies"].append(f"User '{user.username}' is not verified")
                
                # Check for processing jobs without recipes
                orphaned_jobs = ProcessingJob.query.filter(
                    ~ProcessingJob.recipe_id.in_(db.session.query(Recipe.id))
                ).all()
                
                for job in orphaned_jobs:
                    issues["foreign_key_violations"].append(f"Processing job {job.id} references non-existent recipe {job.recipe_id}")
                
        except Exception as e:
            issues["validation_error"] = [str(e)]
        
        return issues
    
    def cleanup_orphaned_records(self, confirm: bool = False) -> bool:
        """Remove orphaned records from the database"""
        if not confirm:
            print("⚠️  This will permanently delete orphaned records!")
            response = input("Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled.")
                return False
        
        try:
            with self.app.app_context():
                deleted_count = 0
                
                # Delete orphaned instructions
                orphaned_instructions = Instruction.query.filter(
                    ~Instruction.recipe_id.in_(db.session.query(Recipe.id))
                ).all()
                
                for inst in orphaned_instructions:
                    db.session.delete(inst)
                    deleted_count += 1
                
                # Delete orphaned processing jobs
                orphaned_jobs = ProcessingJob.query.filter(
                    ~ProcessingJob.recipe_id.in_(db.session.query(Recipe.id))
                ).all()
                
                for job in orphaned_jobs:
                    db.session.delete(job)
                    deleted_count += 1
                
                # Delete inactive user sessions older than 30 days
                old_sessions = UserSession.query.filter(
                    UserSession.is_active == False,
                    UserSession.last_activity < datetime.utcnow() - timedelta(days=30)
                ).all()
                
                for session in old_sessions:
                    db.session.delete(session)
                    deleted_count += 1
                
                db.session.commit()
                print(f"✅ Cleanup completed: {deleted_count} records deleted")
                return True
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            db.session.rollback()
            return False
    
    def display_statistics(self):
        """Display comprehensive database statistics"""
        print("=" * 60)
        print("📊 COOKBOOK CREATOR DATABASE STATISTICS")
        print("=" * 60)
        
        stats = self.get_database_statistics()
        
        # Table statistics
        print("\n📋 Table Counts:")
        total_records = 0
        for table, count in stats["tables"].items():
            print(f"   {table:20} {count:>8}")
            total_records += count
        print(f"   {'TOTAL':20} {total_records:>8}")
        
        # Relationship statistics
        print("\n🔗 Relationships:")
        for relationship, value in stats["relationships"].items():
            if isinstance(value, float):
                print(f"   {relationship:30} {value:>8.1f}")
            else:
                print(f"   {relationship:30} {value:>8}")
        
        # Data quality metrics
        print("\n✅ Data Quality:")
        for metric, value in stats["data_quality"].items():
            print(f"   {metric:30} {value:>8}")
        
        # Validation issues
        issues = self.validate_data_integrity()
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        
        print(f"\n🔍 Data Integrity Issues: {total_issues}")
        for category, issue_list in issues.items():
            if issue_list and category != "validation_error":
                print(f"   {category:20} {len(issue_list):>8}")
        
        print("=" * 60)


def main():
    """Command line interface for database utilities"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cookbook Creator Database Utilities")
    parser.add_argument("--env", default="development",
                       choices=["development", "testing", "production"],
                       help="Environment configuration")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Export data
    export_parser = subparsers.add_parser("export", help="Export database data")
    export_parser.add_argument("--format", default="json", choices=["json", "csv"],
                              help="Export format")
    export_parser.add_argument("--output", help="Output file path")
    export_parser.add_argument("--include-sensitive", action="store_true",
                              help="Include sensitive data")
    
    # Import data
    import_parser = subparsers.add_parser("import", help="Import database data")
    import_parser.add_argument("input", help="Input file path")
    import_parser.add_argument("--format", default="json", choices=["json"],
                              help="Import format")
    import_parser.add_argument("--merge", default="skip", choices=["skip", "update"],
                              help="Merge strategy for existing records")
    
    # Statistics
    subparsers.add_parser("stats", help="Show database statistics")
    
    # Validate data
    subparsers.add_parser("validate", help="Validate data integrity")
    
    # Cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up orphaned records")
    cleanup_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create database utilities
    db_utils = DatabaseUtils(args.env)
    
    # Execute command
    if args.command == "export":
        db_utils.export_data(args.format, args.output, args.include_sensitive)
    elif args.command == "import":
        db_utils.import_data(args.input, args.format, args.merge)
    elif args.command == "stats":
        db_utils.display_statistics()
    elif args.command == "validate":
        issues = db_utils.validate_data_integrity()
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        print(f"🔍 Found {total_issues} data integrity issues:")
        for category, issue_list in issues.items():
            if issue_list:
                print(f"\n{category.replace('_', ' ').title()}:")
                for issue in issue_list:
                    print(f"   - {issue}")
    elif args.command == "cleanup":
        db_utils.cleanup_orphaned_records(confirm=args.yes)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Database Utilities - Import/export and maintenance tools for Cookbook Creator

This module provides utilities for:
- Data export to JSON/CSV formats
- Data import from JSON files
- Database statistics and analysis
- Data integrity validation
- Cleanup operations
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from cookbook_db_utils.imports import (
    create_app, db, User, UserSession, Password, Recipe, Cookbook, Ingredient,
    Tag, Instruction, RecipeImage, ProcessingJob
)


class DatabaseUtils:
    """Database utility operations"""

    def __init__(self, config_name: str = "development"):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name

    def export_data(self, format: str = "json", output_path: Optional[str] = None,
                   include_sensitive: bool = False) -> bool:
        """Export database data to specified format"""
        try:
            with self.app.app_context():
                data = self._collect_export_data(include_sensitive)
                
                if output_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = f"cookbook_export_{timestamp}.{format}"

                if format == "json":
                    return self._export_json(data, output_path)
                elif format == "csv":
                    return self._export_csv(data, output_path)
                else:
                    print(f"❌ Unsupported export format: {format}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error during export: {e}")
            return False

    def import_data(self, input_path: str, format: str = "json", 
                   merge_strategy: str = "skip") -> bool:
        """Import data from specified file"""
        input_file = Path(input_path)
        if not input_file.exists():
            print(f"❌ Input file not found: {input_path}")
            return False

        try:
            with self.app.app_context():
                if format == "json":
                    return self._import_json(input_path, merge_strategy)
                else:
                    print(f"❌ Unsupported import format: {format}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error during import: {e}")
            return False

    def get_database_statistics(self) -> Dict:
        """Get comprehensive database statistics"""
        stats = {}
        
        try:
            with self.app.app_context():
                # Table counts
                models = [
                    ('users', User),
                    ('cookbooks', Cookbook),
                    ('recipes', Recipe),
                    ('ingredients', Ingredient),
                    ('instructions', Instruction),
                    ('processing_jobs', ProcessingJob)
                ]
                
                stats['tables'] = {}
                for table_name, model in models:
                    try:
                        count = model.query.count()
                        stats['tables'][table_name] = count
                    except Exception:
                        stats['tables'][table_name] = 'Error'
                
                # Additional statistics
                stats['total_records'] = sum(
                    count for count in stats['tables'].values() 
                    if isinstance(count, int)
                )
                
                # Recipe statistics
                if stats['tables'].get('recipes', 0) > 0:
                    recipes = Recipe.query.all()
                    if recipes:
                        prep_times = [r.prep_time for r in recipes if r.prep_time]
                        cook_times = [r.cook_time for r in recipes if r.cook_time]
                        
                        stats['recipe_stats'] = {
                            'avg_prep_time': sum(prep_times) / len(prep_times) if prep_times else 0,
                            'avg_cook_time': sum(cook_times) / len(cook_times) if cook_times else 0,
                            'total_prep_time': sum(prep_times),
                            'total_cook_time': sum(cook_times)
                        }
                
        except Exception as e:
            stats['error'] = str(e)
            
        return stats

    def validate_data_integrity(self) -> Dict[str, List[str]]:
        """Validate data integrity and return issues"""
        issues = {
            'orphaned_instructions': [],
            'orphaned_processing_jobs': [],
            'missing_required_fields': [],
            'validation_error': []
        }
        
        try:
            with self.app.app_context():
                # Check for orphaned instructions
                orphaned_instructions = db.session.query(Instruction).filter(
                    ~Instruction.recipe_id.in_(db.session.query(Recipe.id))
                ).all()
                
                for instruction in orphaned_instructions:
                    issues['orphaned_instructions'].append(
                        f"Instruction {instruction.id} references non-existent recipe {instruction.recipe_id}"
                    )
                
                # Check for orphaned processing jobs
                orphaned_jobs = db.session.query(ProcessingJob).filter(
                    ProcessingJob.recipe_id.isnot(None),
                    ~ProcessingJob.recipe_id.in_(db.session.query(Recipe.id))
                ).all()
                
                for job in orphaned_jobs:
                    issues['orphaned_processing_jobs'].append(
                        f"Processing job {job.id} references non-existent recipe {job.recipe_id}"
                    )
                    
        except Exception as e:
            issues['validation_error'].append(str(e))
            
        return issues

    def cleanup_orphaned_records(self, confirm: bool = False) -> bool:
        """Clean up orphaned records"""
        if not confirm:
            print("⚠️  This will delete orphaned records!")
            response = input("Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled.")
                return False

        try:
            with self.app.app_context():
                cleaned = 0
                
                # Remove orphaned instructions
                orphaned_instructions = db.session.query(Instruction).filter(
                    ~Instruction.recipe_id.in_(db.session.query(Recipe.id))
                ).all()
                
                for instruction in orphaned_instructions:
                    db.session.delete(instruction)
                    cleaned += 1
                
                # Remove orphaned processing jobs
                orphaned_jobs = db.session.query(ProcessingJob).filter(
                    ProcessingJob.recipe_id.isnot(None),
                    ~ProcessingJob.recipe_id.in_(db.session.query(Recipe.id))
                ).all()
                
                for job in orphaned_jobs:
                    db.session.delete(job)
                    cleaned += 1
                
                db.session.commit()
                print(f"✅ Cleaned up {cleaned} orphaned records")
                return True
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            db.session.rollback()
            return False

    def display_statistics(self):
        """Display comprehensive database statistics"""
        stats = self.get_database_statistics()
        
        print("📊 Database Statistics")
        print("=" * 40)
        
        if 'error' in stats:
            print(f"❌ Error getting statistics: {stats['error']}")
            return
            
        print(f"Total Records: {stats.get('total_records', 0)}")
        print("\nTable Counts:")
        for table, count in stats.get('tables', {}).items():
            print(f"  {table:20} {count:>8}")
            
        if 'recipe_stats' in stats:
            recipe_stats = stats['recipe_stats']
            print(f"\nRecipe Statistics:")
            print(f"  Average prep time: {recipe_stats['avg_prep_time']:.1f} minutes")
            print(f"  Average cook time: {recipe_stats['avg_cook_time']:.1f} minutes")

    def _collect_export_data(self, include_sensitive: bool) -> Dict:
        """Collect data for export"""
        data = {}
        
        # Export non-sensitive data
        data['cookbooks'] = [cookbook.to_dict() for cookbook in Cookbook.query.all()]
        data['recipes'] = [recipe.to_dict() for recipe in Recipe.query.all()]
        data['ingredients'] = [ingredient.to_dict() for ingredient in Ingredient.query.all()]
        
        # Optionally include sensitive data
        if include_sensitive:
            data['users'] = [
                {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role.value,
                    'status': user.status.value
                }
                for user in User.query.all()
            ]
            
        return data

    def _export_json(self, data: Dict, output_path: str) -> bool:
        """Export data to JSON format"""
        try:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"✅ Data exported to: {output_path}")
            return True
        except Exception as e:
            print(f"❌ Error exporting JSON: {e}")
            return False

    def _export_csv(self, data: Dict, output_path: str) -> bool:
        """Export data to CSV format (creates multiple files)"""
        try:
            base_path = Path(output_path).stem
            
            for table_name, records in data.items():
                if not records:
                    continue
                    
                csv_path = f"{base_path}_{table_name}.csv"
                
                with open(csv_path, 'w', newline='') as f:
                    if records and isinstance(records[0], dict):
                        writer = csv.DictWriter(f, fieldnames=records[0].keys())
                        writer.writeheader()
                        writer.writerows(records)
                        
                print(f"✅ {table_name} exported to: {csv_path}")
                
            return True
        except Exception as e:
            print(f"❌ Error exporting CSV: {e}")
            return False

    def _import_json(self, input_path: str, merge_strategy: str) -> bool:
        """Import data from JSON file"""
        try:
            with open(input_path, 'r') as f:
                data = json.load(f)
            
            # Simple import for ingredients (as example)
            if 'ingredients' in data:
                imported = 0
                for ingredient_data in data['ingredients']:
                    existing = Ingredient.query.filter_by(name=ingredient_data['name']).first()
                    
                    if existing and merge_strategy == 'skip':
                        continue
                    elif existing and merge_strategy == 'update':
                        existing.category = ingredient_data.get('category', existing.category)
                    else:
                        ingredient = Ingredient(
                            name=ingredient_data['name'],
                            category=ingredient_data.get('category')
                        )
                        db.session.add(ingredient)
                    
                    imported += 1
                
                db.session.commit()
                print(f"✅ Imported {imported} ingredients")
            
            return True
        except Exception as e:
            print(f"❌ Error importing JSON: {e}")
            db.session.rollback()
            return False

    def export_all_content(self, output_path: Optional[str] = None, 
                          include_user_data: bool = False) -> bool:
        """
        Export all database content using ContentMigrator
        
        Args:
            output_path: Output file path
            include_user_data: Whether to include user-specific data
            
        Returns:
            bool: Success status
        """
        try:
            from cookbook_db_utils.content_migrator import ContentMigrator
            migrator = ContentMigrator(self.config_name)
            return migrator.export_all_content(output_path, include_user_data)
        except Exception as e:
            print(f"❌ Error during export-all: {e}")
            return False
    
    def export_content_only(self, output_path: Optional[str] = None) -> bool:
        """
        Export only content data (no user-specific data) using ContentMigrator
        Ideal for environment migrations
        
        Args:
            output_path: Output file path
            
        Returns:
            bool: Success status
        """
        try:
            from cookbook_db_utils.content_migrator import ContentMigrator
            migrator = ContentMigrator(self.config_name)
            return migrator.export_content_only(output_path)
        except Exception as e:
            print(f"❌ Error during export-content: {e}")
            return False
    
    def import_to_admin(self, input_path: str, admin_username: str = "admin",
                       create_admin: bool = False, dry_run: bool = False) -> bool:
        """
        Import content and assign ownership to admin user using ContentMigrator
        
        Args:
            input_path: Input file path
            admin_username: Username for admin user
            create_admin: Create admin user if not exists
            dry_run: Test import without committing
            
        Returns:
            bool: Success status
        """
        try:
            from cookbook_db_utils.content_migrator import ContentMigrator
            migrator = ContentMigrator(self.config_name)
            return migrator.import_to_admin(input_path, admin_username, create_admin, dry_run)
        except Exception as e:
            print(f"❌ Error during import-to-admin: {e}")
            return False


def main():
    """Command line interface for database utilities"""
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Cookbook Creator Database Utilities")
    parser.add_argument("--env", default="development",
                       choices=["development", "testing", "production"],
                       help="Environment configuration")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Export
    export_parser = subparsers.add_parser("export", help="Export database data")
    export_parser.add_argument("--format", default="json", choices=["json", "csv"])
    export_parser.add_argument("--output", help="Output file path")
    export_parser.add_argument("--include-sensitive", action="store_true")

    # Import
    import_parser = subparsers.add_parser("import", help="Import database data")
    import_parser.add_argument("input", help="Input file path")
    import_parser.add_argument("--merge", default="skip", choices=["skip", "update"])

    # Statistics
    subparsers.add_parser("stats", help="Show database statistics")

    # Validate
    subparsers.add_parser("validate", help="Validate data integrity")

    # Cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up orphaned records")
    cleanup_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Create database utils
    db_utils = DatabaseUtils(args.env)

    # Execute command
    if args.command == "export":
        db_utils.export_data(args.format, args.output, args.include_sensitive)
    elif args.command == "import":
        db_utils.import_data(args.input, merge_strategy=args.merge)
    elif args.command == "stats":
        db_utils.display_statistics()
    elif args.command == "validate":
        issues = db_utils.validate_data_integrity()
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        print(f"🔍 Found {total_issues} data integrity issues")
        for category, issue_list in issues.items():
            if issue_list:
                print(f"\n{category.replace('_', ' ').title()}:")
                for issue in issue_list:
                    print(f"   - {issue}")
    elif args.command == "cleanup":
        db_utils.cleanup_orphaned_records(confirm=args.yes)


if __name__ == "__main__":
    main()
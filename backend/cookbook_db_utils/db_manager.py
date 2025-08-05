#!/usr/bin/env python3
"""
Database Manager - Core database operations for Cookbook Creator

This module provides utilities for:
- Creating and dropping database tables
- Resetting the database
- Backing up and restoring data
- Database status and information display
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from cookbook_db_utils.imports import (
    create_app, db, User, UserSession, Password, Recipe, Cookbook, Ingredient,
    Tag, Instruction, RecipeImage, ProcessingJob
)


class DatabaseManager:
    """Core database management operations"""

    def __init__(self, config_name: str = "development"):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name

    def _get_db_path(self) -> Optional[Path]:
        """Get the SQLite database file path if using SQLite"""
        db_uri = self.app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            return Path(db_uri.replace('sqlite:///', ''))
        return None

    def create_tables(self, confirm: bool = False) -> bool:
        """Create all database tables"""
        if not confirm:
            print("⚠️  This will create all database tables.")
            response = input("Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled.")
                return False

        try:
            with self.app.app_context():
                print("Creating database tables...")
                db.create_all()
                print("✅ Database tables created successfully!")
                self._display_tables()
                return True
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False

    def drop_tables(self, confirm: bool = False) -> bool:
        """Drop all database tables"""
        if not confirm:
            print("⚠️  WARNING: This will permanently delete ALL database tables and data!")
            print("This action cannot be undone.")
            response = input("Type 'DELETE' to confirm: ").strip()
            if response != 'DELETE':
                print("Operation cancelled.")
                return False

        try:
            with self.app.app_context():
                print("Dropping all database tables...")
                db.drop_all()
                print("✅ All database tables dropped successfully!")
                return True
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            return False

    def reset_database(self, confirm: bool = False, seed_data: bool = True, users_only: bool = False) -> bool:
        """Reset database (drop + create + optionally seed) or reset only user-related tables"""
        if users_only:
            return self._reset_user_tables_only(confirm, seed_data)
        
        if not confirm:
            print("⚠️  WARNING: This will completely reset the database!")
            print("All existing data will be lost.")
            if seed_data:
                print("Sample data will be added after reset.")
            response = input("Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled.")
                return False

        try:
            # Drop existing tables
            if not self.drop_tables(confirm=True):
                return False

            # Create new tables
            if not self.create_tables(confirm=True):
                return False

            # Seed data if requested
            if seed_data:
                with self.app.app_context():
                    from cookbook_db_utils.seed_data import DataSeeder
                    seeder = DataSeeder(self.config_name)
                    seeder.seed_all()

            print("✅ Database reset completed successfully!")
            return True
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
            return False

    def _reset_user_tables_only(self, confirm: bool = False, seed_data: bool = True) -> bool:
        """Reset only user-related tables while preserving recipes, cookbooks, ingredients, etc."""
        if not confirm:
            print("⚠️  WARNING: This will reset all user-related data!")
            print("The following will be deleted:")
            print("  - All users and their accounts")  
            print("  - User sessions and passwords")
            print("  - User recipe collections")
            print("  - User recipe notes and comments")
            print("  - Recipe groups")
            print("  - Processing jobs")
            print("  - User copyright consents")
            print("")
            print("The following will be PRESERVED:")
            print("  - Recipes and their content")
            print("  - Cookbooks")
            print("  - Ingredients, tags, instructions")
            print("  - Recipe images")
            print("")
            if seed_data:
                print("Sample user data will be added after reset.")
            response = input("Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled.")
                return False

        try:
            with self.app.app_context():
                print("🗑️  Clearing user-related tables...")
                
                # Import all user-related models
                from app.models.user import User, UserSession, Password, CopyrightConsent
                from app.models.recipe import UserRecipeCollection, RecipeGroup, ProcessingJob, RecipeNote, RecipeComment, Cookbook, Recipe
                
                # Delete in order to respect foreign key constraints
                # Start with dependent tables first
                
                print("   Deleting recipe comments...")
                RecipeComment.query.delete()
                
                print("   Deleting user recipe notes...")
                RecipeNote.query.delete()
                
                print("   Deleting user recipe collections...")
                UserRecipeCollection.query.delete()
                
                print("   Deleting recipe groups...")
                RecipeGroup.query.delete()
                
                print("   Deleting processing jobs...")
                ProcessingJob.query.delete()
                
                print("   Deleting copyright consents...")
                CopyrightConsent.query.delete()
                
                print("   Deleting user sessions...")
                UserSession.query.delete()
                
                print("   Deleting password history...")
                Password.query.delete()

                # Update recipe ownership to remove user and cookbook references
                print("🔄 Updating recipes to remove user and cookbook ownership...")
                Recipe.query.update({Recipe.user_id: None, Recipe.cookbook_id: None})

                print("   Deleting cookbooks...")
                Cookbook.query.delete()
                
                print("   Deleting users...")
                User.query.delete()
                
                # Commit the deletions
                db.session.commit()
                print("✅ User-related tables cleared successfully!")
                
                # Seed user data if requested
                if seed_data:
                    print("🌱 Seeding user data...")
                    from cookbook_db_utils.seed_data import DataSeeder
                    seeder = DataSeeder(self.config_name)
                    seeder.seed_users()  # Only seed users, not recipes
                    print("✅ User data seeded!")

                print("✅ User-only database reset completed successfully!")
                self._display_tables()
                return True
                
        except Exception as e:
            print(f"❌ Error resetting user tables: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
            return False

    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Backup SQLite database file"""
        db_path = self._get_db_path()
        if not db_path:
            print("❌ Backup only supported for SQLite databases")
            return False

        if not db_path.exists():
            print(f"❌ Database file not found: {db_path}")
            return False

        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{db_path.stem}_backup_{timestamp}.db"

        try:
            shutil.copy2(db_path, backup_path)
            print(f"✅ Database backed up to: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Error backing up database: {e}")
            return False

    def restore_database(self, backup_path: str, confirm: bool = False) -> bool:
        """Restore SQLite database from backup"""
        db_path = self._get_db_path()
        if not db_path:
            print("❌ Restore only supported for SQLite databases")
            return False

        backup_file = Path(backup_path)
        if not backup_file.exists():
            print(f"❌ Backup file not found: {backup_path}")
            return False

        if not confirm:
            print(f"⚠️  This will replace the current database with: {backup_path}")
            print("Current database will be lost!")
            response = input("Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled.")
                return False

        try:
            # Backup current database first
            current_backup = f"{db_path.stem}_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            if db_path.exists():
                shutil.copy2(db_path, current_backup)
                print(f"📁 Current database backed up to: {current_backup}")

            # Restore from backup
            shutil.copy2(backup_path, db_path)
            print(f"✅ Database restored from: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Error restoring database: {e}")
            return False

    def get_database_info(self) -> dict:
        """Get database information and statistics"""
        info = {
            'config': self.config_name,
            'database_uri': self.app.config['SQLALCHEMY_DATABASE_URI'],
            'tables': {},
            'total_records': 0
        }

        try:
            with self.app.app_context():
                # Get table information
                models = [
                    ('users', User),
                    ('user_sessions', UserSession),
                    ('passwords', Password),
                    ('recipes', Recipe),
                    ('cookbooks', Cookbook),
                    ('ingredients', Ingredient),
                    ('tags', Tag),
                    ('instructions', Instruction),
                    ('recipe_images', RecipeImage),
                    ('processing_jobs', ProcessingJob)
                ]

                for table_name, model in models:
                    try:
                        count = model.query.count()
                        info['tables'][table_name] = count
                        info['total_records'] += count
                    except Exception:
                        info['tables'][table_name] = 'Error'

                # Add database file info for SQLite
                db_path = self._get_db_path()
                if db_path and db_path.exists():
                    stat = db_path.stat()
                    info['file_size'] = f"{stat.st_size / (1024*1024):.2f} MB"
                    info['last_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()

        except Exception as e:
            info['error'] = str(e)

        return info

    def _display_tables(self):
        """Display current table information"""
        info = self.get_database_info()

        print("\n📊 Database Information:")
        print(f"   Config: {info['config']}")
        print(f"   URI: {info['database_uri']}")

        if 'file_size' in info:
            print(f"   Size: {info['file_size']}")

        print(f"\n📋 Tables ({info['total_records']} total records):")
        for table, count in info['tables'].items():
            print(f"   {table:20} {count:>8}")

    def display_status(self):
        """Display comprehensive database status"""
        print("=" * 60)
        print("🗄️  COOKBOOK CREATOR DATABASE STATUS")
        print("=" * 60)

        self._display_tables()

        # Check database connectivity
        try:
            with self.app.app_context():
                # Use text() for raw SQL with SQLAlchemy 2.0+
                from sqlalchemy import text
                db.session.execute(text("SELECT 1"))
                print("\n✅ Database connection: OK")
        except Exception as e:
            print(f"\n❌ Database connection: FAILED ({e})")

        print("=" * 60)


def main():
    """Command line interface for database manager"""
    import argparse

    parser = argparse.ArgumentParser(description="Cookbook Creator Database Manager")
    parser.add_argument("--env", default="development",
                       choices=["development", "testing", "production"],
                       help="Environment configuration")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create tables
    create_parser = subparsers.add_parser("create", help="Create database tables")
    create_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # Drop tables
    drop_parser = subparsers.add_parser("drop", help="Drop all database tables")
    drop_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # Reset database
    reset_parser = subparsers.add_parser("reset", help="Reset database (drop + create + seed)")
    reset_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    reset_parser.add_argument("--no-seed", action="store_true", help="Don't seed sample data")
    reset_parser.add_argument("--users-only", action="store_true", help="Reset only user-related tables, preserve recipes/cookbooks")

    # Backup
    backup_parser = subparsers.add_parser("backup", help="Backup database")
    backup_parser.add_argument("path", nargs="?", help="Backup file path")

    # Restore
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("path", help="Backup file path")
    restore_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # Status
    subparsers.add_parser("status", help="Show database status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Create database manager
    db_manager = DatabaseManager(args.env)

    # Execute command
    if args.command == "create":
        db_manager.create_tables(confirm=args.yes)
    elif args.command == "drop":
        db_manager.drop_tables(confirm=args.yes)
    elif args.command == "reset":
        db_manager.reset_database(confirm=args.yes, seed_data=not args.no_seed)
    elif args.command == "backup":
        db_manager.backup_database(args.path)
    elif args.command == "restore":
        db_manager.restore_database(args.path, confirm=args.yes)
    elif args.command == "status":
        db_manager.display_status()


if __name__ == "__main__":
    main()
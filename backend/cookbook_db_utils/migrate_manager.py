#!/usr/bin/env python3
"""
Migration Manager - Database migration utilities for Cookbook Creator

This module provides utilities for:
- Running database migrations with Flask-Migrate
- Generating new migrations
- Rollback functionality
- Migration status and validation
"""

from typing import Optional, List, Dict
from flask_migrate import upgrade, downgrade, migrate, current, history, show

from cookbook_db_utils.imports import create_app


class MigrationManager:
    """Database migration management operations"""

    def __init__(self, config_name: str = "development"):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name

    def run_migrations(self, target: Optional[str] = None) -> bool:
        """Run database migrations (upgrade to latest or specific revision)"""
        try:
            with self.app.app_context():
                print("Running database migrations...")
                if target:
                    print(f"Upgrading to revision: {target}")
                    upgrade(revision=target)
                else:
                    print("Upgrading to latest revision")
                    upgrade()
                print("✅ Migrations completed successfully!")
                self._display_current_revision()
                return True
        except Exception as e:
            print(f"❌ Error running migrations: {e}")
            return False

    def rollback_migrations(self, target: str, confirm: bool = False) -> bool:
        """Rollback to specific migration revision"""
        if not confirm:
            print(f"⚠️  This will rollback database to revision: {target}")
            response = input("Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled.")
                return False

        try:
            with self.app.app_context():
                print(f"Rolling back to revision: {target}")
                downgrade(revision=target)
                print("✅ Rollback completed successfully!")
                self._display_current_revision()
                return True
        except Exception as e:
            print(f"❌ Error during rollback: {e}")
            return False

    def generate_migration(self, message: str, auto_generate: bool = True) -> bool:
        """Generate new migration file"""
        try:
            with self.app.app_context():
                print(f"Generating migration: {message}")
                if auto_generate:
                    migrate(message=message)
                else:
                    migrate(message=message, empty=True)
                print("✅ Migration generated successfully!")
                return True
        except Exception as e:
            print(f"❌ Error generating migration: {e}")
            return False

    def list_migrations(self, verbose: bool = False) -> List[Dict]:
        """List all migrations"""
        migrations = []
        try:
            with self.app.app_context():
                # Get migration history
                for migration in history():
                    migrations.append({
                        'revision': migration.revision,
                        'message': migration.doc,
                        'down_revision': migration.down_revision
                    })
        except Exception as e:
            print(f"❌ Error listing migrations: {e}")
        
        return migrations

    def show_migration(self, revision: str) -> bool:
        """Show details of specific migration"""
        try:
            with self.app.app_context():
                show(revision)
                return True
        except Exception as e:
            print(f"❌ Error showing migration: {e}")
            return False

    def validate_migrations(self) -> bool:
        """Validate migration consistency"""
        try:
            with self.app.app_context():
                # Basic validation - check if we can get current revision
                current_rev = current()
                print(f"✅ Migration validation passed. Current revision: {current_rev}")
                return True
        except Exception as e:
            print(f"❌ Migration validation failed: {e}")
            return False

    def _display_current_revision(self):
        """Display current migration revision"""
        try:
            with self.app.app_context():
                current_rev = current()
                print(f"📍 Current revision: {current_rev}")
        except Exception as e:
            print(f"❌ Error getting current revision: {e}")

    def display_status(self):
        """Display comprehensive migration status"""
        print("=" * 60)
        print("🔄 COOKBOOK CREATOR MIGRATION STATUS")
        print("=" * 60)

        try:
            with self.app.app_context():
                current_rev = current()
                print(f"📍 Current revision: {current_rev}")
                
                migrations = self.list_migrations()
                print(f"📊 Total migrations: {len(migrations)}")
                
                if migrations:
                    print("\n📋 Recent migrations:")
                    for migration in migrations[-5:]:  # Show last 5
                        print(f"   {migration['revision']} - {migration['message']}")
                
        except Exception as e:
            print(f"❌ Error getting migration status: {e}")

        print("=" * 60)


def main():
    """Command line interface for migration manager"""
    import argparse

    parser = argparse.ArgumentParser(description="Cookbook Creator Migration Manager")
    parser.add_argument("--env", default="development",
                       choices=["development", "testing", "production"],
                       help="Environment configuration")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Upgrade
    upgrade_parser = subparsers.add_parser("upgrade", help="Run database migrations")
    upgrade_parser.add_argument("target", nargs="?", help="Target revision")

    # Rollback
    rollback_parser = subparsers.add_parser("rollback", help="Rollback to revision")
    rollback_parser.add_argument("target", help="Target revision")
    rollback_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # Generate
    generate_parser = subparsers.add_parser("generate", help="Generate new migration")
    generate_parser.add_argument("message", help="Migration message")
    generate_parser.add_argument("--empty", action="store_true", help="Create empty migration")

    # List
    list_parser = subparsers.add_parser("list", help="List all migrations")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Show
    show_parser = subparsers.add_parser("show", help="Show migration details")
    show_parser.add_argument("revision", help="Migration revision")

    # Validate
    subparsers.add_parser("validate", help="Validate migration consistency")

    # Status
    subparsers.add_parser("status", help="Show migration status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Create migration manager
    migrate_manager = MigrationManager(args.env)

    # Execute command
    if args.command == "upgrade":
        migrate_manager.run_migrations(args.target)
    elif args.command == "rollback":
        migrate_manager.rollback_migrations(args.target, confirm=args.yes)
    elif args.command == "generate":
        migrate_manager.generate_migration(args.message, auto_generate=not args.empty)
    elif args.command == "list":
        migrations = migrate_manager.list_migrations(args.verbose)
        for migration in migrations:
            print(f"{migration['revision']} - {migration['message']}")
    elif args.command == "show":
        migrate_manager.show_migration(args.revision)
    elif args.command == "validate":
        migrate_manager.validate_migrations()
    elif args.command == "status":
        migrate_manager.display_status()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Migration Manager - Database migration utilities for Cookbook Creator

This module provides utilities for:
- Running database migrations (upgrade/downgrade)
- Generating new migrations from model changes
- Checking migration status and history
- Managing migration rollbacks
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent.parent))

from app import create_app, db
from flask_migrate import upgrade, downgrade, migrate, current, history, show


class MigrationManager:
    """Database migration management operations"""
    
    def __init__(self, config_name: str = "development"):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name
        self.migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        
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
        """Rollback to a specific migration revision"""
        if not confirm:
            print(f"⚠️  This will rollback the database to revision: {target}")
            print("This may result in data loss!")
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
        """Generate a new migration from model changes"""
        if not message.strip():
            print("❌ Migration message is required")
            return False
        
        try:
            with self.app.app_context():
                print(f"Generating migration: {message}")
                if auto_generate:
                    migrate(message=message)
                    print("✅ Migration generated successfully!")
                    self._display_latest_migration()
                else:
                    print("Creating empty migration file...")
                    # Create empty migration file
                    from flask_migrate import revision
                    revision(message=message)
                    print("✅ Empty migration file created!")
                return True
        except Exception as e:
            print(f"❌ Error generating migration: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status and information"""
        status = {
            'current_revision': None,
            'head_revision': None,
            'pending_upgrades': False,
            'migrations_count': 0,
            'migrations_dir': str(self.migrations_dir)
        }
        
        try:
            with self.app.app_context():
                # Get current revision
                try:
                    current_rev = current()
                    status['current_revision'] = current_rev
                except Exception:
                    status['current_revision'] = "No migrations applied"
                
                # Get migration history
                try:
                    migration_history = history(verbose=False)
                    if migration_history:
                        status['migrations_count'] = len(migration_history)
                        # Head is the latest migration
                        status['head_revision'] = migration_history[0].revision[:8]
                        # Check if there are pending upgrades
                        if status['current_revision'] != status['head_revision']:
                            status['pending_upgrades'] = True
                except Exception as e:
                    status['error'] = f"Could not get migration history: {e}"
                
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def list_migrations(self, verbose: bool = False) -> List[Dict[str, str]]:
        """List all available migrations"""
        migrations = []
        
        try:
            with self.app.app_context():
                migration_history = history(verbose=verbose)
                
                for migration in migration_history:
                    migration_info = {
                        'revision': migration.revision[:8],
                        'full_revision': migration.revision,
                        'message': migration.doc,
                        'down_revision': migration.down_revision[:8] if migration.down_revision else None
                    }
                    migrations.append(migration_info)
                    
        except Exception as e:
            print(f"❌ Error listing migrations: {e}")
        
        return migrations
    
    def show_migration(self, revision: str) -> bool:
        """Show details of a specific migration"""
        try:
            with self.app.app_context():
                print(f"Migration details for revision: {revision}")
                print("-" * 50)
                show(revision)
                return True
        except Exception as e:
            print(f"❌ Error showing migration: {e}")
            return False
    
    def validate_migrations(self) -> bool:
        """Validate migration consistency and detect conflicts"""
        print("🔍 Validating migration consistency...")
        
        # Check if migrations directory exists
        if not self.migrations_dir.exists():
            print("❌ Migrations directory not found!")
            return False
        
        versions_dir = self.migrations_dir / "versions"
        if not versions_dir.exists():
            print("❌ Migration versions directory not found!")
            return False
        
        # Count migration files
        migration_files = list(versions_dir.glob("*.py"))
        print(f"📁 Found {len(migration_files)} migration files")
        
        # Check for basic issues
        try:
            with self.app.app_context():
                # Try to get migration history
                migration_history = history(verbose=False)
                db_migrations = len(migration_history) if migration_history else 0
                
                print(f"📊 Database shows {db_migrations} applied migrations")
                
                if len(migration_files) != db_migrations:
                    print("⚠️  Mismatch between file count and database migrations")
                
                # Check current status
                current_rev = current()
                if current_rev:
                    print(f"📍 Current revision: {current_rev}")
                else:
                    print("📍 No migrations applied to database")
                
                print("✅ Migration validation completed")
                return True
                
        except Exception as e:
            print(f"❌ Error during validation: {e}")
            return False
    
    def _display_current_revision(self):
        """Display current migration revision"""
        try:
            with self.app.app_context():
                current_rev = current()
                if current_rev:
                    print(f"📍 Current revision: {current_rev}")
                else:
                    print("📍 No migrations applied")
        except Exception as e:
            print(f"Error getting current revision: {e}")
    
    def _display_latest_migration(self):
        """Display information about the latest migration"""
        migrations = self.list_migrations()
        if migrations:
            latest = migrations[0]
            print(f"📄 Latest migration: {latest['revision']} - {latest['message']}")
    
    def display_status(self):
        """Display comprehensive migration status"""
        print("=" * 60)
        print("🔄 COOKBOOK CREATOR MIGRATION STATUS")
        print("=" * 60)
        
        status = self.get_migration_status()
        
        print(f"📁 Migrations directory: {status['migrations_dir']}")
        print(f"📊 Total migrations: {status['migrations_count']}")
        print(f"📍 Current revision: {status['current_revision']}")
        print(f"🔝 Head revision: {status['head_revision']}")
        
        if status['pending_upgrades']:
            print("⚠️  Pending upgrades available!")
        else:
            print("✅ Database is up to date")
        
        if 'error' in status:
            print(f"❌ Error: {status['error']}")
        
        print("\n📋 Recent migrations:")
        migrations = self.list_migrations()
        for migration in migrations[:5]:  # Show last 5 migrations
            current_marker = "→" if migration['revision'] in str(status['current_revision']) else " "
            print(f"   {current_marker} {migration['revision']} - {migration['message']}")
        
        print("=" * 60)


def main():
    """Command line interface for migration manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cookbook Creator Migration Manager")
    parser.add_argument("--env", default="development",
                       choices=["development", "testing", "production"],
                       help="Environment configuration")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Upgrade migrations
    upgrade_parser = subparsers.add_parser("upgrade", help="Run database migrations")
    upgrade_parser.add_argument("target", nargs="?", help="Target revision (default: latest)")
    
    # Rollback migrations
    rollback_parser = subparsers.add_parser("rollback", help="Rollback to specific revision")
    rollback_parser.add_argument("target", help="Target revision")
    rollback_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    
    # Generate migration
    generate_parser = subparsers.add_parser("generate", help="Generate new migration")
    generate_parser.add_argument("message", help="Migration message")
    generate_parser.add_argument("--empty", action="store_true", help="Create empty migration")
    
    # List migrations
    list_parser = subparsers.add_parser("list", help="List all migrations")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    # Show migration
    show_parser = subparsers.add_parser("show", help="Show migration details")
    show_parser.add_argument("revision", help="Migration revision")
    
    # Validate migrations
    subparsers.add_parser("validate", help="Validate migration consistency")
    
    # Status
    subparsers.add_parser("status", help="Show migration status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create migration manager
    migration_manager = MigrationManager(args.env)
    
    # Execute command
    if args.command == "upgrade":
        migration_manager.run_migrations(args.target)
    elif args.command == "rollback":
        migration_manager.rollback_migrations(args.target, confirm=args.yes)
    elif args.command == "generate":
        migration_manager.generate_migration(args.message, auto_generate=not args.empty)
    elif args.command == "list":
        migrations = migration_manager.list_migrations(args.verbose)
        print(f"\n📋 Found {len(migrations)} migrations:")
        for migration in migrations:
            print(f"   {migration['revision']} - {migration['message']}")
    elif args.command == "show":
        migration_manager.show_migration(args.revision)
    elif args.command == "validate":
        migration_manager.validate_migrations()
    elif args.command == "status":
        migration_manager.display_status()


if __name__ == "__main__":
    main()
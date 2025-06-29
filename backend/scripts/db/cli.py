#!/usr/bin/env python3
"""
Unified CLI - Single command-line interface for all database operations

This provides a unified interface for:
- Database management (create, drop, reset, backup, restore)
- Migration management (upgrade, rollback, generate)
- Data seeding (sample data, specific components)
- Database utilities (export, import, statistics, validation)
- Development helpers
"""

import sys
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from .db_manager import DatabaseManager
    from .migrate_manager import MigrationManager
    from .seed_data import DataSeeder
    from .db_utils import DatabaseUtils
except ImportError:
    # Fallback for when running as standalone script
    from db_manager import DatabaseManager
    from migrate_manager import MigrationManager
    from seed_data import DataSeeder
    from db_utils import DatabaseUtils


def create_parser():
    """Create the main argument parser with all subcommands"""
    parser = argparse.ArgumentParser(
        description="Cookbook Creator Database Management CLI",
        epilog="Use 'cookbook-db <command> --help' for command-specific help"
    )
    
    parser.add_argument("--env", default="development",
                       choices=["development", "testing", "production"],
                       help="Environment configuration (default: development)")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Database management commands
    db_group = subparsers.add_parser("db", help="Database management operations")
    db_subparsers = db_group.add_subparsers(dest="db_command")
    
    # db create
    create_parser = db_subparsers.add_parser("create", help="Create database tables")
    create_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    
    # db drop
    drop_parser = db_subparsers.add_parser("drop", help="Drop all database tables")
    drop_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    
    # db reset
    reset_parser = db_subparsers.add_parser("reset", help="Reset database (drop + create + seed)")
    reset_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    reset_parser.add_argument("--no-seed", action="store_true", help="Don't seed sample data")
    
    # db backup
    backup_parser = db_subparsers.add_parser("backup", help="Backup database")
    backup_parser.add_argument("path", nargs="?", help="Backup file path")
    
    # db restore
    restore_parser = db_subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("path", help="Backup file path")
    restore_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    
    # db status
    db_subparsers.add_parser("status", help="Show database status")
    
    # Migration commands
    migrate_group = subparsers.add_parser("migrate", help="Database migration operations")
    migrate_subparsers = migrate_group.add_subparsers(dest="migrate_command")
    
    # migrate upgrade
    upgrade_parser = migrate_subparsers.add_parser("upgrade", help="Run database migrations")
    upgrade_parser.add_argument("target", nargs="?", help="Target revision (default: latest)")
    
    # migrate rollback
    rollback_parser = migrate_subparsers.add_parser("rollback", help="Rollback to specific revision")
    rollback_parser.add_argument("target", help="Target revision")
    rollback_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    
    # migrate generate
    generate_parser = migrate_subparsers.add_parser("generate", help="Generate new migration")
    generate_parser.add_argument("message", help="Migration message")
    generate_parser.add_argument("--empty", action="store_true", help="Create empty migration")
    
    # migrate list
    list_parser = migrate_subparsers.add_parser("list", help="List all migrations")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    # migrate show
    show_parser = migrate_subparsers.add_parser("show", help="Show migration details")
    show_parser.add_argument("revision", help="Migration revision")
    
    # migrate validate
    migrate_subparsers.add_parser("validate", help="Validate migration consistency")
    
    # migrate status
    migrate_subparsers.add_parser("status", help="Show migration status")
    
    # Data seeding commands
    seed_group = subparsers.add_parser("seed", help="Data seeding operations")
    seed_subparsers = seed_group.add_subparsers(dest="seed_command")
    
    # seed all
    seed_all_parser = seed_subparsers.add_parser("all", help="Seed all sample data")
    seed_all_parser.add_argument("--dataset", default="full",
                                choices=["minimal", "full", "demo"],
                                help="Dataset size to seed")
    
    # seed clear
    clear_parser = seed_subparsers.add_parser("clear", help="Clear all data")
    clear_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    
    # seed specific components
    seed_subparsers.add_parser("users", help="Seed only users")
    seed_subparsers.add_parser("ingredients", help="Seed only ingredients")
    seed_subparsers.add_parser("cookbooks", help="Seed only cookbooks")
    seed_subparsers.add_parser("recipes", help="Seed only recipes")
    seed_subparsers.add_parser("tags", help="Seed only tags")
    
    # Utility commands
    utils_group = subparsers.add_parser("utils", help="Database utility operations")
    utils_subparsers = utils_group.add_subparsers(dest="utils_command")
    
    # utils export
    export_parser = utils_subparsers.add_parser("export", help="Export database data")
    export_parser.add_argument("--format", default="json", choices=["json", "csv"],
                              help="Export format")
    export_parser.add_argument("--output", help="Output file path")
    export_parser.add_argument("--include-sensitive", action="store_true",
                              help="Include sensitive data")
    
    # utils import
    import_parser = utils_subparsers.add_parser("import", help="Import database data")
    import_parser.add_argument("input", help="Input file path")
    import_parser.add_argument("--format", default="json", choices=["json"],
                              help="Import format")
    import_parser.add_argument("--merge", default="skip", choices=["skip", "update"],
                              help="Merge strategy for existing records")
    
    # utils stats
    utils_subparsers.add_parser("stats", help="Show database statistics")
    
    # utils validate
    utils_subparsers.add_parser("validate", help="Validate data integrity")
    
    # utils cleanup
    cleanup_parser = utils_subparsers.add_parser("cleanup", help="Clean up orphaned records")
    cleanup_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    
    # Quick commands (shortcuts)
    subparsers.add_parser("init", help="Initialize database (create tables + seed data)")
    subparsers.add_parser("dev-reset", help="Quick development reset (drop + create + seed)")
    subparsers.add_parser("status", help="Show overall status (database + migrations)")
    
    return parser


def execute_command(args):
    """Execute the appropriate command based on parsed arguments"""
    
    # Initialize managers
    db_manager = DatabaseManager(args.env)
    migrate_manager = MigrationManager(args.env)
    seeder = DataSeeder(args.env)
    db_utils = DatabaseUtils(args.env)
    
    # Database management commands
    if args.command == "db":
        if args.db_command == "create":
            return db_manager.create_tables(confirm=args.yes)
        elif args.db_command == "drop":
            return db_manager.drop_tables(confirm=args.yes)
        elif args.db_command == "reset":
            return db_manager.reset_database(confirm=args.yes, seed_data=not args.no_seed)
        elif args.db_command == "backup":
            return db_manager.backup_database(args.path)
        elif args.db_command == "restore":
            return db_manager.restore_database(args.path, confirm=args.yes)
        elif args.db_command == "status":
            db_manager.display_status()
            return True
        else:
            print("❌ Unknown database command")
            return False
    
    # Migration commands
    elif args.command == "migrate":
        if args.migrate_command == "upgrade":
            return migrate_manager.run_migrations(args.target)
        elif args.migrate_command == "rollback":
            return migrate_manager.rollback_migrations(args.target, confirm=args.yes)
        elif args.migrate_command == "generate":
            return migrate_manager.generate_migration(args.message, auto_generate=not args.empty)
        elif args.migrate_command == "list":
            migrations = migrate_manager.list_migrations(args.verbose)
            print(f"\n📋 Found {len(migrations)} migrations:")
            for migration in migrations:
                print(f"   {migration['revision']} - {migration['message']}")
            return True
        elif args.migrate_command == "show":
            return migrate_manager.show_migration(args.revision)
        elif args.migrate_command == "validate":
            return migrate_manager.validate_migrations()
        elif args.migrate_command == "status":
            migrate_manager.display_status()
            return True
        else:
            print("❌ Unknown migration command")
            return False
    
    # Seeding commands
    elif args.command == "seed":
        if args.seed_command == "all":
            result = seeder.seed_all(args.dataset)
            return bool(result)
        elif args.seed_command == "clear":
            return seeder.clear_all_data(confirm=args.yes)
        elif args.seed_command == "users":
            seeder.seed_users()
            return True
        elif args.seed_command == "ingredients":
            seeder.seed_ingredients()
            return True
        elif args.seed_command == "cookbooks":
            from app.models import User
            with seeder.app.app_context():
                users = User.query.all()
                seeder.seed_cookbooks(users)
            return True
        elif args.seed_command == "recipes":
            from app.models import User, Cookbook, Ingredient, Tag
            with seeder.app.app_context():
                users = User.query.all()
                cookbooks = Cookbook.query.all()
                ingredients = Ingredient.query.all()
                tags = Tag.query.all()
                seeder.seed_recipes(users, cookbooks, ingredients, tags)
            return True
        elif args.seed_command == "tags":
            seeder.seed_tags()
            return True
        else:
            print("❌ Unknown seed command")
            return False
    
    # Utility commands
    elif args.command == "utils":
        if args.utils_command == "export":
            return db_utils.export_data(args.format, args.output, args.include_sensitive)
        elif args.utils_command == "import":
            return db_utils.import_data(args.input, args.format, args.merge)
        elif args.utils_command == "stats":
            db_utils.display_statistics()
            return True
        elif args.utils_command == "validate":
            issues = db_utils.validate_data_integrity()
            total_issues = sum(len(issue_list) for issue_list in issues.values())
            print(f"🔍 Found {total_issues} data integrity issues:")
            for category, issue_list in issues.items():
                if issue_list and category != "validation_error":
                    print(f"\n{category.replace('_', ' ').title()}:")
                    for issue in issue_list:
                        print(f"   - {issue}")
            return total_issues == 0
        elif args.utils_command == "cleanup":
            return db_utils.cleanup_orphaned_records(confirm=args.yes)
        else:
            print("❌ Unknown utils command")
            return False
    
    # Quick commands
    elif args.command == "init":
        print("🚀 Initializing database...")
        if db_manager.create_tables(confirm=True):
            seeder.seed_all()
            return True
        return False
    
    elif args.command == "dev-reset":
        print("🔄 Development reset...")
        return db_manager.reset_database(confirm=True, seed_data=True)
    
    elif args.command == "status":
        print("📊 Overall System Status")
        print("=" * 60)
        db_manager.display_status()
        print("\n")
        migrate_manager.display_status()
        return True
    
    else:
        print("❌ Unknown command")
        return False


def main():
    """Main CLI entry point"""
    parser = create_parser()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    args = parser.parse_args()
    
    # If command group specified but no subcommand, show help for that group
    if hasattr(args, 'command') and args.command in ['db', 'migrate', 'seed', 'utils']:
        if not hasattr(args, f'{args.command}_command') or getattr(args, f'{args.command}_command') is None:
            parser.parse_args([args.command, '--help'])
            return
    
    # Set up verbose logging if requested
    if args.verbose:
        print(f"🔧 Environment: {args.env}")
        print(f"📝 Command: {args.command}")
    
    try:
        # Execute the command
        success = execute_command(args)
        
        if success:
            if args.verbose:
                print("✅ Command completed successfully")
        else:
            if args.verbose:
                print("❌ Command failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
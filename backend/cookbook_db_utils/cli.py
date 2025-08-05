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

from cookbook_db_utils.db_manager import DatabaseManager
from cookbook_db_utils.migrate_manager import MigrationManager
from cookbook_db_utils.seed_data import DataSeeder
from cookbook_db_utils.db_utils import DatabaseUtils


def create_parser():
    """Create the main argument parser with all subcommands"""
    parser = argparse.ArgumentParser(
        description="Cookbook Creator Database Management CLI",
        epilog="Use 'cookbook-db <command> --help' for command-specific help",
    )

    parser.add_argument(
        "--env",
        default="development",
        choices=["development", "testing", "production"],
        help="Environment configuration (default: development)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Database management commands
    db_group = subparsers.add_parser("db", help="Database management operations")
    db_subparsers = db_group.add_subparsers(dest="db_command")

    # db create
    create_parser = db_subparsers.add_parser("create", help="Create database tables")
    create_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation"
    )

    # db drop
    drop_parser = db_subparsers.add_parser("drop", help="Drop all database tables")
    drop_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation"
    )

    # db reset
    reset_parser = db_subparsers.add_parser(
        "reset", help="Reset database (drop + create + seed)"
    )
    reset_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation"
    )
    reset_parser.add_argument(
        "--no-seed", action="store_true", help="Don't seed sample data"
    )
    reset_parser.add_argument("--users-only", action="store_true", help="Reset only user-related tables, preserve recipes/cookbooks")

    # db backup
    backup_parser = db_subparsers.add_parser("backup", help="Backup database")
    backup_parser.add_argument("path", nargs="?", help="Backup file path")

    # db restore
    restore_parser = db_subparsers.add_parser(
        "restore", help="Restore database from backup"
    )
    restore_parser.add_argument("path", help="Backup file path")
    restore_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation"
    )

    # db status
    db_subparsers.add_parser("status", help="Show database status")

    # Migration commands
    migrate_group = subparsers.add_parser(
        "migrate", help="Database migration operations"
    )
    migrate_subparsers = migrate_group.add_subparsers(dest="migrate_command")

    # migrate upgrade
    upgrade_parser = migrate_subparsers.add_parser(
        "upgrade", help="Run database migrations"
    )
    upgrade_parser.add_argument(
        "target", nargs="?", help="Target revision (default: latest)"
    )

    # migrate rollback
    rollback_parser = migrate_subparsers.add_parser(
        "rollback", help="Rollback to specific revision"
    )
    rollback_parser.add_argument("target", help="Target revision")
    rollback_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation"
    )

    # migrate generate
    generate_parser = migrate_subparsers.add_parser(
        "generate", help="Generate new migration"
    )
    generate_parser.add_argument("message", help="Migration message")
    generate_parser.add_argument(
        "--empty", action="store_true", help="Create empty migration"
    )

    # migrate list
    list_parser = migrate_subparsers.add_parser("list", help="List all migrations")
    list_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )

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
    seed_all_parser.add_argument(
        "--dataset",
        default="full",
        choices=["minimal", "full", "demo"],
        help="Dataset size to seed",
    )

    # seed clear
    clear_parser = seed_subparsers.add_parser("clear", help="Clear all data")
    clear_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation"
    )

    # seed specific components
    seed_subparsers.add_parser("users", help="Seed only users")
    seed_subparsers.add_parser("users-only", help="Seed only users (recommended for PDF workflow)")
    seed_subparsers.add_parser("ingredients", help="Seed only ingredients")
    seed_subparsers.add_parser("cookbooks", help="Seed only cookbooks")
    seed_subparsers.add_parser("recipes", help="Seed only recipes")

    # seed PDF cookbook
    pdf_parser = seed_subparsers.add_parser(
        "pdf-cookbook", help="Seed cookbook from PDF file"
    )
    pdf_parser.add_argument(
        "pdf_path",
        help="Path to PDF cookbook file (required)",
    )
    pdf_parser.add_argument(
        "--title",
        help="Cookbook title (if not extractable from PDF)",
    )
    pdf_parser.add_argument(
        "--author",
        help="Cookbook author (if not extractable from PDF)",
    )
    pdf_parser.add_argument(
        "--user-id",
        type=int,
        help="User ID to associate recipes with (creates admin user if not provided)",
    )
    pdf_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse recipes but don't commit to database",
    )
    pdf_parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing cookbook data first",
    )
    pdf_parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM-based text extraction, use only pdfplumber",
    )
    pdf_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing recipes with the same title",
    )
    pdf_parser.add_argument(
        "--no-historical-conversions",
        action="store_true",
        help="Disable historical measurement conversions for modern cookbooks",
    )
    pdf_parser.add_argument(
        "--no-google-books",
        action="store_true",
        help="Disable Google Books API metadata extraction",
    )
    pdf_parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum number of pages to process (default: process all pages)",
    )
    pdf_parser.add_argument(
        "--skip-pages",
        type=int,
        default=0,
        help="Number of pages to skip at the beginning (default: 0)",
    )

    # Backward compatibility: keep historical-cookbook command
    historical_parser = seed_subparsers.add_parser(
        "historical-cookbook", help="[DEPRECATED] Use pdf-cookbook instead"
    )
    historical_parser.add_argument(
        "--pdf-path",
        default="/Users/baasman/projects/cookbook-creator/backend/scripts/seed_data/175_choice_recipes_mainly_furnished_by_members_of_the_chicago_womens_club-1887.pdf",
        help="Path to historical cookbook PDF",
    )
    historical_parser.add_argument(
        "--user-id", type=int, help="User ID to associate recipes with"
    )
    historical_parser.add_argument(
        "--dry-run", action="store_true", help="Parse recipes but don't commit to database"
    )
    historical_parser.add_argument(
        "--clear", action="store_true", help="Clear existing cookbook data first"
    )
    historical_parser.add_argument(
        "--no-llm", action="store_true", help="Disable LLM-based text extraction"
    )
    historical_parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing recipes"
    )

    # Utility commands
    utils_group = subparsers.add_parser("utils", help="Database utility operations")
    utils_subparsers = utils_group.add_subparsers(dest="utils_command")

    # utils export
    export_parser = utils_subparsers.add_parser("export", help="Export database data")
    export_parser.add_argument(
        "--format", default="json", choices=["json", "csv"], help="Export format"
    )
    export_parser.add_argument("--output", help="Output file path")
    export_parser.add_argument(
        "--include-sensitive", action="store_true", help="Include sensitive data"
    )

    # utils import
    import_parser = utils_subparsers.add_parser("import", help="Import database data")
    import_parser.add_argument("input", help="Input file path")
    import_parser.add_argument(
        "--format", default="json", choices=["json"], help="Import format"
    )
    import_parser.add_argument(
        "--merge",
        default="skip",
        choices=["skip", "update"],
        help="Merge strategy for existing records",
    )

    # utils stats
    utils_subparsers.add_parser("stats", help="Show database statistics")

    # utils validate
    utils_subparsers.add_parser("validate", help="Validate data integrity")

    # utils cleanup
    cleanup_parser = utils_subparsers.add_parser(
        "cleanup", help="Clean up orphaned records"
    )
    cleanup_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation"
    )

    # utils export-all
    export_all_parser = utils_subparsers.add_parser(
        "export-all", help="Export all database content including user data (creates ZIP file with images)"
    )
    export_all_parser.add_argument("--output", help="Output file path (will be .zip)")
    export_all_parser.add_argument(
        "--include-users", action="store_true", 
        help="Include user-specific data (notes, comments, collections)"
    )

    # utils export-content
    export_content_parser = utils_subparsers.add_parser(
        "export-content", help="Export only content data (recipes, cookbooks, etc.) with images - ideal for environment migrations"
    )
    export_content_parser.add_argument("--output", help="Output file path (will be .zip)")

    # utils import-to-admin
    import_admin_parser = utils_subparsers.add_parser(
        "import-to-admin", help="Import content and assign ownership to admin user (supports ZIP and JSON files)"
    )
    import_admin_parser.add_argument("input", help="Input file path (.zip or .json) (required)")
    import_admin_parser.add_argument(
        "--admin-username", default="admin", 
        help="Username for admin user (default: admin)"
    )
    import_admin_parser.add_argument(
        "--create-admin", action="store_true",
        help="Create admin user if not exists"
    )
    import_admin_parser.add_argument(
        "--dry-run", action="store_true",
        help="Test import without committing changes"
    )

    # Quick commands (shortcuts)
    subparsers.add_parser(
        "init", help="Initialize database (create tables + seed data)"
    )
    subparsers.add_parser(
        "dev-reset", help="Quick development reset (drop + create + seed)"
    )
    subparsers.add_parser("status", help="Show overall status (database + migrations)")

    return parser


def execute_command(args):
    """Execute the appropriate command based on parsed arguments"""

    # Initialize managers
    db_manager = DatabaseManager(args.env)
    migrate_manager = MigrationManager(args.env)
    seeder = DataSeeder(args.env)
    db_utils = DatabaseUtils(args.env)

    # Always log which database is being used
    db_uri = db_manager.app.config["SQLALCHEMY_DATABASE_URI"]
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "")
        print(f"🗄️  Using SQLite database: {db_path}")
    elif db_uri.startswith("postgresql"):
        # Extract host and database name from PostgreSQL URI for security
        import re

        match = re.search(r"postgresql://[^@]+@([^:/]+):?(\d+)?/([^?]+)", db_uri)
        if match:
            host, port, dbname = match.groups()
            port_str = f":{port}" if port else ""
            print(f"🗄️  Using PostgreSQL database: {dbname} on {host}{port_str}")
        else:
            print(f"🗄️  Using PostgreSQL database: [connection string parsed]")
    else:
        print(
            f"🗄️  Using database: {db_uri.split('://')[0] if '://' in db_uri else 'Unknown'}"
        )

    print(f"🌍 Environment: {args.env}")
    print("")

    # Database management commands
    if args.command == "db":
        if args.db_command == "create":
            return db_manager.create_tables(confirm=args.yes)
        elif args.db_command == "drop":
            return db_manager.drop_tables(confirm=args.yes)
        elif args.db_command == "reset":
            return db_manager.reset_database(
                confirm=args.yes, 
                seed_data=not args.no_seed, 
                users_only=args.users_only
            )
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
            return migrate_manager.generate_migration(
                args.message, auto_generate=not args.empty
            )
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
        elif args.seed_command == "users-only":
            result = seeder.seed_users_only()
            return bool(result)
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
                tags = []  # Simplified for this version
                seeder.seed_recipes(users, cookbooks, ingredients, tags)
            return True
        elif args.seed_command == "pdf-cookbook":
            return seed_pdf_cookbook(args)
        elif args.seed_command == "historical-cookbook":
            print("⚠️  WARNING: 'historical-cookbook' command is deprecated. Use 'pdf-cookbook' instead.")
            return seed_historical_cookbook(args)
        else:
            print("❌ Unknown seed command")
            return False

    # Utility commands
    elif args.command == "utils":
        if args.utils_command == "export":
            return db_utils.export_data(
                args.format, args.output, args.include_sensitive
            )
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
        elif args.utils_command == "export-all":
            return db_utils.export_all_content(
                args.output, args.include_users
            )
        elif args.utils_command == "export-content":
            return db_utils.export_content_only(args.output)
        elif args.utils_command == "import-to-admin":
            return db_utils.import_to_admin(
                args.input, args.admin_username, args.create_admin, args.dry_run
            )
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
        # Use users-only seeding by default for PDF workflow
        success = db_manager.drop_tables(confirm=True)
        if success:
            success = db_manager.create_tables(confirm=True)
            if success:
                result = seeder.seed_users_only()
                return bool(result)
        return success

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


def seed_pdf_cookbook(args):
    """Handle PDF cookbook seeding command"""
    from cookbook_db_utils.pdf_cookbook_seeder import PDFCookbookSeeder
    from pathlib import Path
    from datetime import datetime

    print("📖 PDF Cookbook Seeding")
    print("=" * 50)

    # Check if PDF file exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        print("Please check the file path and try again.")
        return False

    # Build cookbook metadata from arguments if provided
    cookbook_metadata = None
    if args.title or args.author:
        cookbook_metadata = {
            "title": args.title or pdf_path.stem.replace("_", " ").title(),
            "author": args.author or "Unknown",
            "description": f"User-specified cookbook: {args.title or pdf_path.name}",
            "publisher": "",
            "isbn": "",
            "publication_date": None,
            "source": "user_provided"
        }

    print(f"📄 PDF: {pdf_path.name}")
    if cookbook_metadata:
        print(f"📚 Title: {cookbook_metadata['title']} (user-specified)")
        print(f"✍️  Author: {cookbook_metadata['author']} (user-specified)")
    else:
        print(f"📚 Metadata: {'Google Books API' if not args.no_google_books else 'Filename extraction'}")
    print(f"🌍 Environment: {args.env}")
    print(f"👤 User ID: {args.user_id or 'Create admin user'}")
    print(f"🧪 Dry run: {'Yes' if args.dry_run else 'No'}")
    print(f"🤖 LLM extraction: {'Disabled' if args.no_llm else 'Enabled (Claude Haiku)'}")
    print(f"🔄 Overwrite existing: {'Yes' if args.overwrite else 'No'}")
    print(f"📏 Historical conversions: {'Disabled' if args.no_historical_conversions else 'Enabled'}")
    print(f"📚 Google Books API: {'Disabled' if args.no_google_books else 'Enabled'}")
    if args.skip_pages > 0:
        print(f"⏭️  Skip pages: {args.skip_pages} pages at beginning")
    if args.max_pages:
        print(f"📄 Max pages: {args.max_pages} pages")
    print("")

    # Handle clear option
    if args.clear:
        print("🗑️  Clearing existing cookbook data...")
        seeder = PDFCookbookSeeder(
            args.env,
            use_llm=not args.no_llm,
            enable_historical_conversions=not args.no_historical_conversions
        )
        # For clearing, we need to get the title somehow
        clear_title = cookbook_metadata["title"] if cookbook_metadata else pdf_path.stem.replace("_", " ").title()
        success = seeder.clear_cookbook_data(
            cookbook_title=clear_title, confirm=True
        )
        if not success:
            print("❌ Failed to clear existing data")
            return False
        print("✅ Existing data cleared")
        print("")

    try:
        # Initialize seeder
        seeder = PDFCookbookSeeder(
            args.env,
            use_llm=not args.no_llm,
            enable_historical_conversions=not args.no_historical_conversions
        )

        # Run the seeding process
        print("🚀 Starting PDF cookbook processing...")
        result = seeder.seed_pdf_cookbook(
            pdf_path=str(pdf_path),
            cookbook_metadata=cookbook_metadata,
            user_id=args.user_id,
            dry_run=args.dry_run,
            overwrite_existing=args.overwrite,
            use_google_books=not args.no_google_books,
            max_pages=args.max_pages,
            skip_pages=args.skip_pages,
        )

        # Display results
        print("\n📊 Processing Results:")
        print("=" * 50)

        if result["success"]:
            print("✅ Processing completed successfully!")
            print(f"📖 Cookbook: {result.get('cookbook', {}).get('title', 'Unknown')}")
            print(f"🍽️  Recipes created: {result['recipes_created']}")
            print(f"📋 Total recipes found: {result['total_recipes_found']}")

            stats = result.get("statistics", {})
            print(f"\n📈 Detailed Statistics:")
            print(f"   📝 Recipes processed: {stats.get('recipes_processed', 0)}")
            print(f"   ✅ Recipes created: {stats.get('recipes_created', 0)}")
            print(f"   ❌ Recipes failed: {stats.get('recipes_failed', 0)}")
            print(f"   📄 Non-recipe pages skipped: {stats.get('non_recipe_pages_skipped', 0)}")
            print(f"   🥕 Ingredients created: {stats.get('ingredients_created', 0)}")
            print(f"   📋 Instructions created: {stats.get('instructions_created', 0)}")
            print(f"   📸 Images created: {stats.get('images_created', 0)}")

            if stats.get("errors"):
                print(f"\n⚠️  Errors encountered:")
                for error in stats["errors"][:5]:  # Show first 5 errors
                    print(f"   - {error}")
                if len(stats["errors"]) > 5:
                    print(f"   ... and {len(stats['errors']) - 5} more errors")

            if args.dry_run:
                print(f"\n🧪 DRY RUN: No changes were committed to the database")
                print(f"   Run without --dry-run to actually create the recipes")
            else:
                print(f"\n🎉 PDF cookbook successfully seeded to database!")

            return True

        else:
            print("❌ Processing failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")

            stats = result.get("statistics", {})
            if stats.get("errors"):
                print(f"\nErrors encountered:")
                for error in stats["errors"]:
                    print(f"   - {error}")

            return False

    except Exception as e:
        print(f"❌ Unexpected error during processing: {e}")
        import traceback

        print("\nFull traceback:")
        traceback.print_exc()
        return False


def seed_historical_cookbook(args):
    """Handle historical cookbook seeding command (backward compatibility)"""
    from cookbook_db_utils.pdf_cookbook_seeder import PDFCookbookSeeder
    from pathlib import Path

    print("📖 Historical Cookbook Seeding (Legacy Mode)")
    print("=" * 50)

    # Check if PDF file exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        print("Please check the file path and try again.")
        return False

    print(f"📄 PDF: {pdf_path.name}")
    print(f"🌍 Environment: {args.env}")
    print(f"👤 User ID: {args.user_id or 'Create admin user'}")
    print(f"🧪 Dry run: {'Yes' if args.dry_run else 'No'}")
    print(f"🤖 LLM extraction: {'Disabled' if args.no_llm else 'Enabled (Claude Haiku)'}")
    print(f"🔄 Overwrite existing: {'Yes' if args.overwrite else 'No'}")
    print("")

    # Handle clear option
    if args.clear:
        print("🗑️  Clearing existing historical cookbook data...")
        seeder = PDFCookbookSeeder(args.env, use_llm=not args.no_llm)
        success = seeder.clear_cookbook_data(
            cookbook_title="175 Choice Recipes", confirm=True
        )
        if not success:
            print("❌ Failed to clear existing data")
            return False
        print("✅ Existing data cleared")
        print("")

    try:
        # Initialize seeder
        seeder = PDFCookbookSeeder(args.env, use_llm=not args.no_llm)

        # Define cookbook metadata
        from datetime import datetime

        cookbook_metadata = {
            "title": "175 Choice Recipes",
            "author": "Members of the Chicago Women's Club",
            "description": "A collection of 175 choice recipes mainly furnished by members of the Chicago Women's Club, published in 1887. This historical cookbook represents traditional American cooking of the late 19th century.",
            "publisher": "Chicago Women's Club",
            "publication_date": datetime(1887, 1, 1),
            "isbn": "",  # ISBN didn't exist in 1887
        }

        # Run the seeding process
        print("🚀 Starting historical cookbook processing...")
        result = seeder.seed_pdf_cookbook(
            pdf_path=str(pdf_path),
            cookbook_metadata=cookbook_metadata,
            user_id=args.user_id,
            dry_run=args.dry_run,
            overwrite_existing=args.overwrite,
        )

        # Display results
        print("\n📊 Processing Results:")
        print("=" * 50)

        if result["success"]:
            print("✅ Processing completed successfully!")
            print(f"📖 Cookbook: {result.get('cookbook', {}).get('title', 'Unknown')}")
            print(f"🍽️  Recipes created: {result['recipes_created']}")
            print(f"📋 Total recipes found: {result['total_recipes_found']}")

            stats = result.get("statistics", {})
            print(f"\n📈 Detailed Statistics:")
            print(f"   📝 Recipes processed: {stats.get('recipes_processed', 0)}")
            print(f"   ✅ Recipes created: {stats.get('recipes_created', 0)}")
            print(f"   ❌ Recipes failed: {stats.get('recipes_failed', 0)}")
            print(f"   📄 Non-recipe pages skipped: {stats.get('non_recipe_pages_skipped', 0)}")
            print(f"   🥕 Ingredients created: {stats.get('ingredients_created', 0)}")
            print(f"   📋 Instructions created: {stats.get('instructions_created', 0)}")
            print(f"   📸 Images created: {stats.get('images_created', 0)}")

            if stats.get("errors"):
                print(f"\n⚠️  Errors encountered:")
                for error in stats["errors"][:5]:  # Show first 5 errors
                    print(f"   - {error}")
                if len(stats["errors"]) > 5:
                    print(f"   ... and {len(stats['errors']) - 5} more errors")

            if args.dry_run:
                print(f"\n🧪 DRY RUN: No changes were committed to the database")
                print(f"   Run without --dry-run to actually create the recipes")
            else:
                print(f"\n🎉 Historical cookbook successfully seeded to database!")

            return True

        else:
            print("❌ Processing failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")

            stats = result.get("statistics", {})
            if stats.get("errors"):
                print(f"\nErrors encountered:")
                for error in stats["errors"]:
                    print(f"   - {error}")

            return False

    except Exception as e:
        print(f"❌ Unexpected error during processing: {e}")
        import traceback

        print("\nFull traceback:")
        traceback.print_exc()
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
    if hasattr(args, "command") and args.command in ["db", "migrate", "seed", "utils"]:
        if (
            not hasattr(args, f"{args.command}_command")
            or getattr(args, f"{args.command}_command") is None
        ):
            parser.parse_args([args.command, "--help"])
            return

    # Set up verbose logging if requested
    if args.verbose:
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
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

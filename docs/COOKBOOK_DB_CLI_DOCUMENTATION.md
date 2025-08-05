# Cookbook Database CLI Documentation

The Cookbook Database CLI (`cookbook_db_utils.cli`) provides a comprehensive command-line interface for managing all aspects of the Cookbook Creator database system. This unified CLI handles database operations, migrations, data seeding, utilities, and PDF cookbook processing.

## Table of Contents

- [Getting Started](#getting-started)
- [Global Options](#global-options)
- [Database Management Commands](#database-management-commands)
- [Migration Management Commands](#migration-management-commands)
- [Data Seeding Commands](#data-seeding-commands)
- [Utility Commands](#utility-commands)
- [Quick Commands](#quick-commands)
- [PDF Cookbook Processing](#pdf-cookbook-processing)
- [Examples](#examples)
- [Environment Configuration](#environment-configuration)

## Getting Started

### Installation

The CLI is part of the cookbook database utilities. Run commands using:

```bash
uv run python -m cookbook_db_utils.cli [command] [options]
```

### Basic Usage

```bash
# Show all available commands
uv run python -m cookbook_db_utils.cli --help

# Show help for a specific command group
uv run python -m cookbook_db_utils.cli db --help

# Show help for a specific command
uv run python -m cookbook_db_utils.cli db create --help
```

## Global Options

These options are available for all commands:

| Option | Description | Default |
|--------|-------------|---------|
| `--env {development,testing,production}` | Environment configuration | `development` |
| `--verbose`, `-v` | Enable verbose output | `false` |
| `--help`, `-h` | Show help message | - |

### Environment Examples

```bash
# Use development environment (default)
uv run python -m cookbook_db_utils.cli db status

# Use production environment
uv run python -m cookbook_db_utils.cli --env production db status

# Enable verbose output
uv run python -m cookbook_db_utils.cli --verbose db create
```

## Database Management Commands

The `db` command group handles database table operations.

### `db create`
Create database tables.

```bash
uv run python -m cookbook_db_utils.cli db create [--yes]
```

**Options:**
- `--yes`, `-y`: Skip confirmation prompt

**Examples:**
```bash
# Create tables with confirmation
uv run python -m cookbook_db_utils.cli db create

# Create tables without confirmation
uv run python -m cookbook_db_utils.cli db create --yes
```

### `db drop`
Drop all database tables.

```bash
uv run python -m cookbook_db_utils.cli db drop [--yes]
```

**Options:**
- `--yes`, `-y`: Skip confirmation prompt

**Examples:**
```bash
# Drop all tables with confirmation
uv run python -m cookbook_db_utils.cli db drop

# Drop all tables without confirmation  
uv run python -m cookbook_db_utils.cli db drop --yes
```

### `db reset`
Reset database (drop + create + optional seed).

```bash
uv run python -m cookbook_db_utils.cli db reset [--yes] [--no-seed]
```

**Options:**
- `--yes`, `-y`: Skip confirmation prompt
- `--no-seed`: Don't seed sample data after reset

**Examples:**
```bash
# Full reset with sample data
uv run python -m cookbook_db_utils.cli db reset --yes

# Reset without seeding data
uv run python -m cookbook_db_utils.cli db reset --yes --no-seed
```

### `db backup`
Backup database to a file.

```bash
uv run python -m cookbook_db_utils.cli db backup [path]
```

**Arguments:**
- `path`: Optional backup file path (auto-generated if not provided)

**Examples:**
```bash
# Auto-generate backup filename
uv run python -m cookbook_db_utils.cli db backup

# Specify backup location
uv run python -m cookbook_db_utils.cli db backup /path/to/backup.sql
```

### `db restore`
Restore database from backup file.

```bash
uv run python -m cookbook_db_utils.cli db restore path [--yes]
```

**Arguments:**
- `path`: Backup file path (required)

**Options:**
- `--yes`, `-y`: Skip confirmation prompt

**Examples:**
```bash
# Restore from backup with confirmation
uv run python -m cookbook_db_utils.cli db restore /path/to/backup.sql

# Restore without confirmation
uv run python -m cookbook_db_utils.cli db restore /path/to/backup.sql --yes
```

### `db status`
Show database connection status and table information.

```bash
uv run python -m cookbook_db_utils.cli db status
```

## Migration Management Commands

The `migrate` command group handles database schema migrations.

### `migrate upgrade`
Run database migrations to upgrade schema.

```bash
uv run python -m cookbook_db_utils.cli migrate upgrade [target]
```

**Arguments:**
- `target`: Optional target revision (defaults to latest)

**Examples:**
```bash
# Upgrade to latest migration
uv run python -m cookbook_db_utils.cli migrate upgrade

# Upgrade to specific revision
uv run python -m cookbook_db_utils.cli migrate upgrade abc123
```

### `migrate rollback`
Rollback to a specific migration revision.

```bash
uv run python -m cookbook_db_utils.cli migrate rollback target [--yes]
```

**Arguments:**
- `target`: Target revision to rollback to (required)

**Options:**
- `--yes`, `-y`: Skip confirmation prompt

**Examples:**
```bash
# Rollback with confirmation
uv run python -m cookbook_db_utils.cli migrate rollback abc123

# Rollback without confirmation
uv run python -m cookbook_db_utils.cli migrate rollback abc123 --yes
```

### `migrate generate`
Generate a new migration file.

```bash
uv run python -m cookbook_db_utils.cli migrate generate message [--empty]
```

**Arguments:**
- `message`: Migration description (required)

**Options:**
- `--empty`: Create empty migration file

**Examples:**
```bash
# Auto-generate migration from model changes
uv run python -m cookbook_db_utils.cli migrate generate "Add user preferences table"

# Create empty migration for manual editing
uv run python -m cookbook_db_utils.cli migrate generate "Custom changes" --empty
```

### `migrate list`
List all available migrations.

```bash
uv run python -m cookbook_db_utils.cli migrate list [--verbose]
```

**Options:**
- `--verbose`, `-v`: Show detailed migration information

### `migrate show`
Show details of a specific migration.

```bash
uv run python -m cookbook_db_utils.cli migrate show revision
```

**Arguments:**
- `revision`: Migration revision to display (required)

### `migrate validate`
Validate migration consistency and detect issues.

```bash
uv run python -m cookbook_db_utils.cli migrate validate
```

### `migrate status`
Show current migration status and pending migrations.

```bash
uv run python -m cookbook_db_utils.cli migrate status
```

## Data Seeding Commands

The `seed` command group handles populating the database with sample or real data.

### `seed all`
Seed all sample data (users, ingredients, cookbooks, recipes).

```bash
uv run python -m cookbook_db_utils.cli seed all [--dataset {minimal,full,demo}]
```

**Options:**
- `--dataset`: Dataset size to seed
  - `minimal`: Basic data for development
  - `full`: Complete sample dataset
  - `demo`: Demo-ready dataset with realistic data

**Examples:**
```bash
# Seed full dataset
uv run python -m cookbook_db_utils.cli seed all

# Seed minimal dataset for development
uv run python -m cookbook_db_utils.cli seed all --dataset minimal

# Seed demo dataset
uv run python -m cookbook_db_utils.cli seed all --dataset demo
```

### `seed clear`
Clear all data from the database.

```bash
uv run python -m cookbook_db_utils.cli seed clear [--yes]
```

**Options:**
- `--yes`, `-y`: Skip confirmation prompt

### Component-Specific Seeding

Seed specific data components:

```bash
# Seed only users
uv run python -m cookbook_db_utils.cli seed users

# Seed only ingredients
uv run python -m cookbook_db_utils.cli seed ingredients

# Seed only cookbooks
uv run python -m cookbook_db_utils.cli seed cookbooks

# Seed only recipes
uv run python -m cookbook_db_utils.cli seed recipes
```

### `seed pdf-cookbook`
**🆕 NEW:** Process and seed recipes from PDF cookbook files with intelligent metadata extraction.

```bash
uv run python -m cookbook_db_utils.cli seed pdf-cookbook pdf_path [options]
```

**Arguments:**
- `pdf_path`: Path to PDF cookbook file (required)

**Options:**
- `--title TITLE`: Override cookbook title (otherwise uses Google Books API)
- `--author AUTHOR`: Override cookbook author (otherwise uses Google Books API)
- `--user-id USER_ID`: User ID to associate recipes with (creates admin user if not provided)
- `--dry-run`: Parse recipes but don't commit to database
- `--clear`: Clear existing cookbook data first
- `--no-llm`: Disable LLM-based text extraction, use only pdfplumber
- `--overwrite`: Overwrite existing recipes with the same title
- `--no-historical-conversions`: Disable historical measurement conversions for modern cookbooks
- `--no-google-books`: Disable Google Books API metadata extraction
- `--max-pages MAX_PAGES`: Maximum number of pages to process (default: process all pages)
- `--skip-pages SKIP_PAGES`: Number of pages to skip at the beginning (default: 0)

**Examples:**
```bash
# Process PDF with automatic Google Books metadata
uv run python -m cookbook_db_utils.cli seed pdf-cookbook "Joy_of_Cooking.pdf"

# Process with manual metadata
uv run python -m cookbook_db_utils.cli seed pdf-cookbook cookbook.pdf --title "My Cookbook" --author "Chef Name"

# Process modern cookbook without historical conversions
uv run python -m cookbook_db_utils.cli seed pdf-cookbook modern_cookbook.pdf --no-historical-conversions

# Dry run to test without committing
uv run python -m cookbook_db_utils.cli seed pdf-cookbook cookbook.pdf --dry-run

# Process offline without Google Books API
uv run python -m cookbook_db_utils.cli seed pdf-cookbook cookbook.pdf --no-google-books

# Overwrite existing recipes
uv run python -m cookbook_db_utils.cli seed pdf-cookbook cookbook.pdf --overwrite

# Process only first 10 pages
uv run python -m cookbook_db_utils.cli seed pdf-cookbook cookbook.pdf --max-pages 10

# Skip first 5 pages (table of contents, etc.)
uv run python -m cookbook_db_utils.cli seed pdf-cookbook cookbook.pdf --skip-pages 5

# Skip first 3 pages and process next 20 pages
uv run python -m cookbook_db_utils.cli seed pdf-cookbook cookbook.pdf --skip-pages 3 --max-pages 20
```

### `seed historical-cookbook` (Deprecated)
**⚠️ DEPRECATED:** Use `pdf-cookbook` instead. Maintained for backward compatibility.

```bash
uv run python -m cookbook_db_utils.cli seed historical-cookbook [options]
```

This command is deprecated and will show a warning. Use `pdf-cookbook` for all new projects.

## Utility Commands

The `utils` command group provides database maintenance and analysis tools.

### `utils export`
Export database data to various formats.

```bash
uv run python -m cookbook_db_utils.cli utils export [options]
```

**Options:**
- `--format {json,csv}`: Export format (default: json)
- `--output OUTPUT`: Output file path (auto-generated if not provided)
- `--include-sensitive`: Include sensitive data (passwords, tokens, etc.)

**Examples:**
```bash
# Export to JSON (default)
uv run python -m cookbook_db_utils.cli utils export

# Export to CSV
uv run python -m cookbook_db_utils.cli utils export --format csv

# Export to specific file
uv run python -m cookbook_db_utils.cli utils export --output backup.json

# Include sensitive data
uv run python -m cookbook_db_utils.cli utils export --include-sensitive
```

### `utils import`
Import database data from files.

```bash
uv run python -m cookbook_db_utils.cli utils import input [options]
```

**Arguments:**
- `input`: Input file path (required)

**Options:**
- `--format {json}`: Import format (default: json)
- `--merge {skip,update}`: Merge strategy for existing records (default: skip)

**Examples:**
```bash
# Import from JSON file
uv run python -m cookbook_db_utils.cli utils import data.json

# Import with update strategy
uv run python -m cookbook_db_utils.cli utils import data.json --merge update
```

### `utils stats`
Show comprehensive database statistics.

```bash
uv run python -m cookbook_db_utils.cli utils stats
```

Displays:
- Record counts for all tables
- Database size information
- Performance metrics
- Index usage statistics

### `utils validate`
Validate data integrity and find issues.

```bash
uv run python -m cookbook_db_utils.cli utils validate
```

Checks for:
- Orphaned records
- Missing foreign key relationships
- Data consistency issues
- Constraint violations

### `utils cleanup`
Clean up orphaned records and fix data issues.

```bash
uv run python -m cookbook_db_utils.cli utils cleanup [--yes]
```

**Options:**
- `--yes`, `-y`: Skip confirmation prompt

### `utils export-all`
Export all database content including user data, metadata, and image files. Creates a ZIP archive containing both database records and associated image files.

```bash
uv run python -m cookbook_db_utils.cli utils export-all [options]
```

**Options:**
- `--output OUTPUT`: Output file path (will be .zip, auto-generated if not provided)
- `--include-users`: Include user-specific data (notes, comments, collections)

**Examples:**
```bash
# Export all content to auto-generated ZIP file
uv run python -m cookbook_db_utils.cli utils export-all

# Export with user data to specific ZIP file
uv run python -m cookbook_db_utils.cli utils export-all --output full_backup.zip --include-users

# Export from production environment
uv run python -m cookbook_db_utils.cli --env production utils export-all --output prod_full_export.zip
```

### `utils export-content`
Export only content data (recipes, cookbooks, ingredients, tags, etc.) with associated image files, but without user-specific data. Creates a ZIP archive ideal for migrating content between environments.

```bash
uv run python -m cookbook_db_utils.cli utils export-content [options]
```

**Options:**
- `--output OUTPUT`: Output file path (will be .zip, auto-generated if not provided)

**Examples:**
```bash
# Export content for environment migration
uv run python -m cookbook_db_utils.cli utils export-content --output content_export.zip

# Export content from production to transfer to development
uv run python -m cookbook_db_utils.cli --env production utils export-content --output prod_content.zip
```

### `utils import-to-admin`
Import content from export files and assign ownership to admin user. Supports both ZIP files (with images) and legacy JSON files (data only). Perfect for transferring content between environments where users don't exist. Preserves original recipe privacy settings (public/private status) and copies image files to the target environment.

```bash
uv run python -m cookbook_db_utils.cli utils import-to-admin input [options]
```

**Arguments:**
- `input`: Input file path (.zip or .json) (required)

**Options:**
- `--admin-username USERNAME`: Username for admin user (default: admin)
- `--create-admin`: Create admin user if not exists
- `--dry-run`: Test import without committing changes

**Examples:**
```bash
# Import content ZIP and assign to existing admin user
uv run python -m cookbook_db_utils.cli utils import-to-admin prod_content.zip

# Import with custom admin username
uv run python -m cookbook_db_utils.cli utils import-to-admin prod_content.zip --admin-username cookbook_admin

# Import and create admin user if needed
uv run python -m cookbook_db_utils.cli utils import-to-admin prod_content.zip --create-admin

# Test import without committing (includes image file validation)
uv run python -m cookbook_db_utils.cli utils import-to-admin prod_content.zip --dry-run --create-admin

# Import legacy JSON file (data only, no images)
uv run python -m cookbook_db_utils.cli utils import-to-admin legacy_export.json --create-admin
```

## Quick Commands

Convenient shortcuts for common development tasks.

### `init`
Initialize database (create tables + seed data).

```bash
uv run python -m cookbook_db_utils.cli init
```

Equivalent to:
```bash
uv run python -m cookbook_db_utils.cli db create --yes
uv run python -m cookbook_db_utils.cli seed all
```

### `dev-reset`
Quick development reset (drop + create + seed).

```bash
uv run python -m cookbook_db_utils.cli dev-reset
```

Equivalent to:
```bash
uv run python -m cookbook_db_utils.cli db reset --yes
```

### `status`
Show overall system status (database + migrations).

```bash
uv run python -m cookbook_db_utils.cli status
```

Displays:
- Database connection status
- Migration status
- Table information
- System health

## PDF Cookbook Processing

### 🆕 Intelligent Metadata Extraction

The PDF cookbook processing system now includes intelligent metadata extraction using:

1. **Google Books API Integration**:
   - Automatically searches for cookbook metadata
   - Extracts title, author, publisher, publication date, ISBN
   - Uses multiple search strategies for best matches
   - Filters results for cookbook-specific content

2. **Filename Analysis**:
   - Parses PDF filenames for title and author information  
   - Handles common naming patterns:
     - `Author - Title.pdf`
     - `Title by Author.pdf`
     - `Author_Title_YEAR.pdf`

3. **PDF Metadata Extraction**:
   - Reads embedded PDF metadata
   - Combines with Google Books data for comprehensive information

4. **Smart Recipe Detection**:
   - Enhanced page filtering for modern cookbooks
   - Skips non-recipe pages (introductions, indexes, etc.)
   - Confidence scoring for recipe content
   - Supports both historical and modern cookbook layouts

### Processing Features

- **LLM-Enhanced Text Extraction**: Uses Claude Haiku for accurate OCR and text extraction
- **Recipe Segmentation**: Intelligent parsing of recipe content from pages
- **Image Extraction**: Saves PDF pages as recipe images for web display
- **Historical Conversions**: Optional conversion of vintage measurements
- **Duplicate Handling**: Overwrite or skip existing recipes
- **Validation**: Comprehensive recipe content validation

## Examples

### Common Workflows

#### Setting up a new development environment:
```bash
# Initialize database with sample data
uv run python -m cookbook_db_utils.cli init
```

#### Processing a PDF cookbook:
```bash
# Automatic processing with Google Books metadata
uv run python -m cookbook_db_utils.cli seed pdf-cookbook "Julia_Child_Mastering_French_Cooking.pdf"

# Test processing without committing
uv run python -m cookbook_db_utils.cli seed pdf-cookbook cookbook.pdf --dry-run

# Process with specific metadata
uv run python -m cookbook_db_utils.cli seed pdf-cookbook cookbook.pdf --title "My Cookbook" --author "Chef Name"
```

#### Content migration between environments (with images):
```bash
# Export content from production (creates ZIP with images)
uv run python -m cookbook_db_utils.cli --env production utils export-content --output prod_content.zip

# Reset development database and import content
uv run python -m cookbook_db_utils.cli --env development db reset --users-only -y
uv run python -m cookbook_db_utils.cli --env development utils import-to-admin prod_content.zip --create-admin

# Test import first with dry-run (validates images too)
uv run python -m cookbook_db_utils.cli --env development utils import-to-admin prod_content.zip --dry-run --create-admin

# Note: Privacy settings (public/private) and image files are preserved during import
```

#### Database maintenance:
```bash
# Check database health
uv run python -m cookbook_db_utils.cli status

# Validate data integrity
uv run python -m cookbook_db_utils.cli utils validate

# Clean up issues
uv run python -m cookbook_db_utils.cli utils cleanup

# Create backup
uv run python -m cookbook_db_utils.cli db backup
```

#### Migration management:
```bash
# Check migration status
uv run python -m cookbook_db_utils.cli migrate status

# Run pending migrations
uv run python -m cookbook_db_utils.cli migrate upgrade

# Generate new migration
uv run python -m cookbook_db_utils.cli migrate generate "Add new feature"
```

### Production Workflows

#### Production database setup:
```bash
# Set production environment
export FLASK_ENV=production

# Create tables (no sample data)
uv run python -m cookbook_db_utils.cli --env production db create --yes

# Run migrations
uv run python -m cookbook_db_utils.cli --env production migrate upgrade
```

#### Production backup:
```bash
# Create timestamped backup
uv run python -m cookbook_db_utils.cli --env production db backup

# Export data for analysis
uv run python -m cookbook_db_utils.cli --env production utils export --format json
```

## Environment Configuration

### Database Environments

The CLI supports three environments:

- **`development`** (default): Local development with SQLite
- **`testing`**: Test environment with isolated database
- **`production`**: Production environment with PostgreSQL

### Configuration Files

Environment-specific settings are managed through:
- Flask configuration files
- Environment variables
- Database connection strings

### Environment Variables

Key environment variables:
- `FLASK_ENV`: Flask application environment
- `DATABASE_URL`: Database connection string
- `ANTHROPIC_API_KEY`: For LLM-enhanced PDF processing
- `REDIS_URL`: For caching (optional)

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure proper database permissions
2. **Migration Conflicts**: Use `migrate validate` to check consistency
3. **PDF Processing Issues**: Check LLM availability and API keys
4. **Memory Issues**: Use `--no-llm` for large PDFs
5. **Network Issues**: Use `--no-google-books` for offline processing

### Debug Mode

Enable verbose output for troubleshooting:
```bash
uv run python -m cookbook_db_utils.cli --verbose [command]
```

### Log Files

Check application logs for detailed error information and processing status.

---

## Version History

- **v2.0.0**: Added PDF cookbook processing with Google Books integration
- **v1.5.0**: Enhanced migration management and validation
- **v1.0.0**: Initial unified CLI with database management

For more information, see the individual module documentation or run any command with `--help`.
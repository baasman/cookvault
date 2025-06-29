# Database Management Utilities

A comprehensive suite of database management tools for the Cookbook Creator application.

## Overview

This directory contains a complete set of utilities for managing the Cookbook Creator database, including:

- **Database Management**: Create, drop, reset, backup, and restore operations
- **Migration Management**: Handle database schema changes with Alembic/Flask-Migrate
- **Data Seeding**: Populate database with sample data for development and testing
- **Database Utilities**: Import/export data, statistics, validation, and maintenance
- **Development Helpers**: Quick utilities for active development workflows

## Quick Start

The easiest way to get started is with the unified CLI:

```bash
# Initialize database with sample data
./cookbook-db init

# Or for quick development reset
./cookbook-db dev-reset

# Show overall status
./cookbook-db status
```

## Installation & Setup

No additional installation required - the scripts use the existing Flask application dependencies.

### Prerequisites

- Python 3.8+
- Flask application properly configured
- Database connection available (SQLite for development)

### Making Scripts Executable

```bash
chmod +x cookbook-db
```

## Usage Guide

### Unified CLI Interface (`cookbook-db`)

The main interface for all database operations:

```bash
./cookbook-db --help                    # Show all available commands
./cookbook-db <command> --help          # Help for specific command
./cookbook-db --env production <cmd>    # Use specific environment
```

#### Quick Commands

```bash
./cookbook-db init              # Initialize database (create + seed)
./cookbook-db dev-reset         # Quick development reset
./cookbook-db status            # Show overall system status
```

#### Database Management

```bash
./cookbook-db db create         # Create all tables
./cookbook-db db drop           # Drop all tables (with confirmation)
./cookbook-db db reset          # Reset database (drop + create + seed)
./cookbook-db db backup         # Backup database to file
./cookbook-db db restore file   # Restore from backup file
./cookbook-db db status         # Show database status
```

#### Migration Management

```bash
./cookbook-db migrate upgrade              # Run latest migrations
./cookbook-db migrate upgrade abc123       # Upgrade to specific revision
./cookbook-db migrate rollback def456      # Rollback to revision
./cookbook-db migrate generate "message"   # Generate new migration
./cookbook-db migrate list                 # List all migrations
./cookbook-db migrate status               # Show migration status
./cookbook-db migrate validate             # Validate migration consistency
```

#### Data Seeding

```bash
./cookbook-db seed all                     # Seed all sample data
./cookbook-db seed all --dataset minimal   # Minimal dataset
./cookbook-db seed users                   # Seed only users
./cookbook-db seed ingredients             # Seed only ingredients
./cookbook-db seed cookbooks               # Seed only cookbooks
./cookbook-db seed recipes                 # Seed only recipes
./cookbook-db seed clear                   # Clear all data
```

#### Database Utilities

```bash
./cookbook-db utils export --format json     # Export to JSON
./cookbook-db utils export --format csv      # Export to CSV
./cookbook-db utils import data.json         # Import from JSON
./cookbook-db utils stats                    # Show database statistics
./cookbook-db utils validate                 # Validate data integrity
./cookbook-db utils cleanup                  # Clean up orphaned records
```

### Individual Scripts

Each component can also be run independently:

#### Database Manager (`db_manager.py`)

Core database operations:

```bash
python db_manager.py create --yes          # Create tables
python db_manager.py drop                  # Drop tables (with prompt)
python db_manager.py reset                 # Full reset
python db_manager.py backup backup.db      # Create backup
python db_manager.py restore backup.db     # Restore backup
python db_manager.py status                # Show status
```

#### Migration Manager (`migrate_manager.py`)

Migration operations:

```bash
python migrate_manager.py upgrade          # Run migrations
python migrate_manager.py rollback abc123  # Rollback to revision
python migrate_manager.py generate "msg"   # Generate migration
python migrate_manager.py list             # List migrations
python migrate_manager.py validate         # Validate migrations
```

#### Data Seeder (`seed_data.py`)

Sample data creation:

```bash
python seed_data.py seed                   # Seed all data
python seed_data.py seed --dataset demo    # Demo dataset
python seed_data.py users                  # Seed users only
python seed_data.py clear                  # Clear all data
```

#### Database Utilities (`db_utils.py`)

Import/export and analysis:

```bash
python db_utils.py export --format json    # Export data
python db_utils.py import data.json        # Import data
python db_utils.py stats                   # Show statistics
python db_utils.py validate                # Validate integrity
python db_utils.py cleanup                 # Clean up orphans
```

#### Development Helpers (`dev_helpers.py`)

Development workflow utilities:

```bash
python dev_helpers.py quick-reset          # Quick reset
python dev_helpers.py create-user admin --role admin  # Create test user
python dev_helpers.py minimal              # Minimal dataset
python dev_helpers.py performance --count 500  # Performance dataset
python dev_helpers.py snapshot dev_state   # Create snapshot
python dev_helpers.py restore dev_state    # Restore snapshot
python dev_helpers.py setup                # Fresh dev environment
```

## Sample Data

The seeding system provides several datasets:

### Full Dataset (Default)

- 4 sample users (admin, chef_gordon, baker_julia, home_cook)
- 4 sample cookbooks with publication details
- 24 common ingredients across categories
- 20 recipe tags
- 3 complete recipes with ingredients and instructions
- Sample processing jobs in various states

### Minimal Dataset

- Basic admin and test users
- Essential ingredients (salt, pepper, oil, garlic, onion)
- One test cookbook and recipe
- Minimal for quick testing

### Demo Dataset

- Curated selection for demonstrations
- Professional-looking sample data
- Balanced across all categories

### Performance Dataset

- Large number of records for performance testing
- Configurable recipe count (default: 100)
- Realistic relationships and data distribution

## Database Schema

The application uses 12 main models:

### Recipe Domain
- `Recipe` - Main recipe model with metadata
- `Cookbook` - Recipe collections
- `Ingredient` - Master ingredient database
- `Tag` - Recipe tagging system
- `Instruction` - Step-by-step instructions
- `RecipeImage` - Recipe photos
- `ProcessingJob` - OCR processing pipeline
- `recipe_ingredients` - Many-to-many with quantities

### User Domain
- `User` - User management with roles
- `Password` - Password history tracking
- `UserSession` - Session management
- `UserRole` - Admin/User roles
- `UserStatus` - Account status tracking

## Environment Configuration

The scripts support multiple environments:

- **development** (default): SQLite database, debug enabled
- **testing**: Separate SQLite database for tests
- **production**: PostgreSQL support, optimized settings

Set environment with `--env` flag:

```bash
./cookbook-db --env production db status
```

## Backup and Recovery

### Automatic Backups

The system creates automatic backups before destructive operations:

- Before database restore
- During development resets
- When requested manually

### Manual Backup

```bash
./cookbook-db db backup my_backup.db
```

### Restore from Backup

```bash
./cookbook-db db restore my_backup.db
```

### Development Snapshots

Quick snapshots for development:

```bash
python dev_helpers.py snapshot "before_feature_x"
python dev_helpers.py restore "before_feature_x"
python dev_helpers.py list-snapshots
```

## Import/Export

### Export Data

Export all data to JSON:

```bash
./cookbook-db utils export --format json --output my_data.json
```

Export to CSV (creates multiple files):

```bash
./cookbook-db utils export --format csv --output my_data
```

Include sensitive data (passwords, sessions):

```bash
./cookbook-db utils export --include-sensitive
```

### Import Data

Import from JSON:

```bash
./cookbook-db utils import my_data.json
```

Merge strategies:
- `skip` (default): Skip existing records
- `update`: Update existing records

## Data Validation

### Integrity Checks

The system validates:

- Foreign key relationships
- Required data presence
- Data consistency rules
- Orphaned records

Run validation:

```bash
./cookbook-db utils validate
```

### Automatic Cleanup

Remove orphaned records:

```bash
./cookbook-db utils cleanup
```

This removes:
- Instructions without recipes
- Processing jobs without recipes
- Inactive sessions older than 30 days

## Development Workflows

### Starting New Feature Development

```bash
# Create fresh environment
./cookbook-db dev-reset

# Or restore from clean snapshot
python dev_helpers.py restore fresh_dev
```

### Testing with Different Data Sets

```bash
# Minimal for unit tests
python dev_helpers.py minimal

# Performance testing
python dev_helpers.py performance --count 1000

# Back to full dataset
./cookbook-db seed all
```

### Quick Status Check

```bash
./cookbook-db status
python dev_helpers.py stats
```

## Troubleshooting

### Common Issues

1. **Migration Conflicts**
   ```bash
   ./cookbook-db migrate validate
   ./cookbook-db migrate status
   ```

2. **Database Connection Issues**
   ```bash
   ./cookbook-db db status
   ```

3. **Orphaned Data**
   ```bash
   ./cookbook-db utils validate
   ./cookbook-db utils cleanup
   ```

4. **Performance Issues**
   ```bash
   ./cookbook-db utils stats
   ```

### Error Recovery

If operations fail:

1. Check database connectivity
2. Validate environment configuration
3. Review error messages for specific issues
4. Restore from backup if needed

### Getting Help

- Use `--help` with any command for detailed usage
- Check error messages for specific guidance
- Review logs for detailed error information
- Use `--verbose` flag for detailed output

## Security Considerations

- Sensitive data (passwords, sessions) excluded from exports by default
- Confirmation prompts for destructive operations
- Backup creation before risky operations
- Environment isolation (dev/test/prod)

## Performance Notes

- Use minimal datasets for development when possible
- Regular cleanup of orphaned records
- Monitor database size with statistics
- Use snapshots for quick state restoration

## Contributing

When adding new utilities:

1. Follow existing patterns for error handling
2. Include confirmation prompts for destructive operations
3. Add comprehensive help text
4. Update this documentation
5. Test with different environments

## Examples

### Daily Development Workflow

```bash
# Morning: fresh start
./cookbook-db dev-reset

# Need clean state for testing
python dev_helpers.py snapshot "pre_test"
# ... run tests ...
python dev_helpers.py restore "pre_test"

# End of day: check what changed
./cookbook-db utils stats
```

### Setting Up Demo Environment

```bash
# Clean reset with demo data
./cookbook-db db reset --yes
./cookbook-db seed all --dataset demo

# Create backup for future demos
./cookbook-db db backup demo_environment.db
```

### Preparing for Production Migration

```bash
# Validate current state
./cookbook-db --env production migrate validate
./cookbook-db --env production utils validate

# Backup before migration
./cookbook-db --env production db backup pre_migration.db

# Run migration
./cookbook-db --env production migrate upgrade
```
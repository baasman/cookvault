# Database Migrations

**Tags:** `operations`, `database`, `migrations`, `alembic`, `flask-migrate`
**Last updated:** 2025-11-14

Complete guide for managing database schema changes using Flask-Migrate and Alembic.

---

## Overview

Cookbook Creator uses **Flask-Migrate** (built on **Alembic**) for database schema versioning and migrations. This guide covers creating, applying, and managing migrations safely.

---

## Quick Reference

```bash
# Show migration status
uv run python -m cookbook_db_utils.cli migrate status

# Apply all pending migrations
uv run python -m cookbook_db_utils.cli migrate upgrade

# Create new migration
uv run python -m cookbook_db_utils.cli migrate generate "description"

# Rollback to specific version
uv run python -m cookbook_db_utils.cli migrate rollback <revision_id>

# List all migrations
uv run python -m cookbook_db_utils.cli migrate list
```

---

## Migration System

### Architecture

```
backend/
├── migrations/
│   ├── versions/           # Migration files
│   ├── alembic.ini        # Alembic configuration
│   ├── env.py             # Migration environment
│   └── script.py.mako     # Migration template
├── app/
│   └── models/            # SQLAlchemy models
└── cookbook_db_utils/
    └── migrate_manager.py  # Migration CLI
```

### How It Works

1. **Models define schema** - SQLAlchemy models in `app/models/`
2. **Alembic tracks changes** - Compares models to database
3. **Migrations bridge versions** - Scripts to upgrade/downgrade
4. **Version control** - Each migration has unique revision ID

---

## Checking Migration Status

### Show Current Status

```bash
uv run python -m cookbook_db_utils.cli migrate status
```

**Output:**
```
Database is at revision: be39cbc74574
Head revision: be39cbc74574
Status: UP TO DATE ✓

Recent migrations:
  be39cbc74574 (head) - add print order fields
  445834817155 - add image fields to instruction table
  aeb529f3d285 - add featured recipe fields
```

### List All Migrations

```bash
uv run python -m cookbook_db_utils.cli migrate list
```

**Shows:**
- Migration revision IDs
- Creation dates
- Migration descriptions
- Current head revision

### Inspect Specific Migration

```bash
uv run python -m cookbook_db_utils.cli migrate show <revision_id>
```

**Details include:**
- Full migration script
- Upgrade and downgrade operations
- Dependencies (down_revision)
- Creation timestamp

---

## Applying Migrations

### Upgrade to Latest

```bash
# Apply all pending migrations
uv run python -m cookbook_db_utils.cli migrate upgrade
```

**Safe for:**
- Production deployments
- Development updates
- CI/CD pipelines

### Upgrade to Specific Version

```bash
# Upgrade to exact revision
uv run python -m cookbook_db_utils.cli migrate upgrade <revision_id>
```

**Use when:**
- Testing specific migration
- Incremental updates needed
- Troubleshooting migration issues

### Verify After Upgrade

```bash
# Check status
uv run python -m cookbook_db_utils.cli migrate status

# Validate database
uv run python -m cookbook_db_utils.cli utils validate
```

---

## Creating New Migrations

### Auto-Generate from Model Changes

**Best practice:** Let Alembic detect changes automatically.

```bash
uv run python -m cookbook_db_utils.cli migrate generate "add user avatar field"
```

**Process:**
1. Modify SQLAlchemy models in `app/models/`
2. Run generate command
3. Review generated migration file
4. Edit if needed
5. Test in development
6. Apply and commit

### Manual Migration

For complex changes not detectable automatically:

```bash
uv run python -m cookbook_db_utils.cli migrate generate "custom indexes" --empty
```

Then edit the migration file manually.

### Migration Naming Conventions

**Good names:**
- `"add user avatar field"`
- `"create print_orders table"`
- `"add index to recipes.created_at"`
- `"rename column user.name to user.username"`

**Bad names:**
- `"update"` (too vague)
- `"fix"` (what fix?)
- `"changes"` (what changes?)

---

## Reviewing Generated Migrations

### What to Check

Always review auto-generated migrations before applying:

**Location:** `backend/migrations/versions/XXXXX_description.py`

#### 1. Check Upgrade Operations

```python
def upgrade():
    # Look for:
    # - Correct table names
    # - Proper data types
    # - NOT NULL constraints (add defaults!)
    # - Index names
    op.add_column('user', sa.Column('avatar', sa.String(255), nullable=True))
```

#### 2. Check Downgrade Operations

```python
def downgrade():
    # Ensure downgrade reverses upgrade
    op.drop_column('user', 'avatar')
```

#### 3. Look for Issues

**Common problems:**
- Missing nullable=True on new columns
- Dropping columns with data (add data migration!)
- Missing indexes
- Foreign key constraints without indexes

### Editing Migrations

**Example: Add default value**

```python
# Generated (unsafe for production):
op.add_column('user', sa.Column('role', sa.String(20), nullable=False))

# Fixed (safe):
op.add_column('user', sa.Column('role', sa.String(20), nullable=False, server_default='USER'))
op.alter_column('user', 'role', server_default=None)  # Remove default
```

---

## Rolling Back Migrations

### Rollback to Specific Version

```bash
# Interactive (asks for confirmation)
uv run python -m cookbook_db_utils.cli migrate rollback <revision_id>

# Skip confirmation
uv run python -m cookbook_db_utils.cli migrate rollback <revision_id> -y
```

**⚠️ Warning:** Rolling back migrations can cause data loss if not careful!

### Safe Rollback Process

1. **Backup first:**
   ```bash
   uv run python -m cookbook_db_utils.cli db backup
   ```

2. **Check what will change:**
   ```bash
   uv run python -m cookbook_db_utils.cli migrate show <target_revision>
   ```

3. **Rollback:**
   ```bash
   uv run python -m cookbook_db_utils.cli migrate rollback <target_revision>
   ```

4. **Verify:**
   ```bash
   uv run python -m cookbook_db_utils.cli migrate status
   ```

### When Rollback Fails

If rollback encounters errors:

```bash
# 1. Check database state
uv run python -m cookbook_db_utils.cli db status

# 2. Manually fix if needed (careful!)
# Access database directly to fix issue

# 3. Mark migration as rolled back
uv run python -m cookbook_db_utils.cli migrate stamp <revision_id>
```

---

## Data Migrations

### When to Use

When schema changes affect existing data:
- Renaming columns (migrate data to new column)
- Changing data types (convert existing values)
- Adding NOT NULL constraints (backfill values)
- Splitting tables (move data)

### Data Migration Pattern

```python
def upgrade():
    # 1. Add new column (nullable)
    op.add_column('user', sa.Column('full_name', sa.String(200), nullable=True))

    # 2. Migrate data
    connection = op.get_bind()
    connection.execute(
        text("UPDATE user SET full_name = first_name || ' ' || last_name")
    )

    # 3. Make NOT NULL if needed
    op.alter_column('user', 'full_name', nullable=False)

    # 4. Drop old columns
    op.drop_column('user', 'first_name')
    op.drop_column('user', 'last_name')

def downgrade():
    # Reverse process
    op.add_column('user', sa.Column('first_name', sa.String(100)))
    op.add_column('user', sa.Column('last_name', sa.String(100)))

    # Split full_name back
    connection = op.get_bind()
    connection.execute(
        text("""
        UPDATE user SET
            first_name = SUBSTR(full_name, 1, INSTR(full_name || ' ', ' ') - 1),
            last_name = SUBSTR(full_name, INSTR(full_name || ' ', ' ') + 1)
        """)
    )

    op.drop_column('user', 'full_name')
```

---

## Testing Migrations

### Test in Development

```bash
# 1. Backup dev database
uv run python -m cookbook_db_utils.cli db backup

# 2. Apply migration
uv run python -m cookbook_db_utils.cli migrate upgrade

# 3. Test application
uv run python run.py

# 4. Test rollback
uv run python -m cookbook_db_utils.cli migrate rollback <previous_revision>

# 5. Reapply
uv run python -m cookbook_db_utils.cli migrate upgrade
```

### Test with Fresh Database

```bash
# Start clean
uv run python -m cookbook_db_utils.cli db reset

# Apply all migrations
uv run python -m cookbook_db_utils.cli migrate upgrade

# Seed data
uv run python -m cookbook_db_utils.cli seed users-only
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Migration tested in development
- [ ] Migration tested with production-like data
- [ ] Rollback tested successfully
- [ ] Backup strategy confirmed
- [ ] Downtime window scheduled (if needed)
- [ ] Team notified

### Deployment Process

**1. Backup Production Database**

```bash
# For PostgreSQL
pg_dump cookbook_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Or using app backup
uv run python -m cookbook_db_utils.cli db backup
```

**2. Apply Migrations**

```bash
# Check current status
uv run python -m cookbook_db_utils.cli --env production migrate status

# Apply migrations
uv run python -m cookbook_db_utils.cli --env production migrate upgrade

# Verify
uv run python -m cookbook_db_utils.cli --env production migrate status
```

**3. Restart Application**

```bash
# Restart web servers to pick up schema changes
systemctl restart cookbook-creator
```

**4. Verify Application**

```bash
# Check health endpoint
curl https://your-domain.com/health

# Check logs
tail -f logs/cookbook-creator.log
```

### If Migration Fails

**Option 1: Rollback**
```bash
uv run python -m cookbook_db_utils.cli --env production migrate rollback <previous_revision>
```

**Option 2: Fix Forward**
```bash
# Create hotfix migration
uv run python -m cookbook_db_utils.cli migrate generate "fix migration issue"
# Edit and apply
uv run python -m cookbook_db_utils.cli --env production migrate upgrade
```

---

## Migration History

### Current Migrations

As of 2025-11-14, the application includes these migrations:

1. `878698479833` - Initial migration (users, recipes, cookbooks, ingredients)
2. `f6bb73209d4e` - Add Stripe payment models
3. `573c9d494ec2` - Add Cloudinary fields to RecipeImage
4. `aeb529f3d285` - Add featured recipe fields
5. `445834817155` - Add image fields to instruction table
6. `be39cbc74574` - Add print order models for Lulu integration

---

## Troubleshooting

### "Database is ahead of migrations"

**Cause:** Database manually modified or migrations skipped.

**Fix:**
```bash
# Option 1: Stamp to current head
uv run python -m cookbook_db_utils.cli migrate stamp head

# Option 2: Generate migration to match
uv run python -m cookbook_db_utils.cli migrate generate "sync with database"
# Review and apply
```

### "Duplicate column/table" error

**Cause:** Migration tries to add existing column/table.

**Fix:**
1. Check database schema manually
2. Edit migration to use `if not exists` or skip if present
3. Or drop problematic migration and regenerate

### "Foreign key constraint failed"

**Cause:** Migration violates database constraints.

**Fix:**
1. Check migration order (dependencies)
2. Add data migration to satisfy constraints
3. Temporarily disable constraints (dangerous!)

### Migration Validation Failed

```bash
uv run python -m cookbook_db_utils.cli migrate validate
```

**Common issues:**
- Migration files missing
- Broken migration chain
- Corrupt alembic_version table

---

## Best Practices

### Do's

✅ **Always backup before migrations**
✅ **Test migrations in development first**
✅ **Review auto-generated migrations**
✅ **Use descriptive migration names**
✅ **Include data migrations when needed**
✅ **Test rollback procedures**
✅ **Keep migrations small and focused**
✅ **Commit migrations with code changes**

### Don'ts

❌ **Don't edit applied migrations**
❌ **Don't skip migrations**
❌ **Don't mix data and schema changes carelessly**
❌ **Don't forget nullable=True on new columns**
❌ **Don't rollback in production without backup**
❌ **Don't manually edit alembic_version table**

---

## See Also

- [Database CLI Documentation](database-cli.md) - Complete CLI reference
- [Backup and Restore](backup-restore.md) - Data protection procedures
- [Deployment Guide](../deployment/production.md) - Production deployment
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

---

[← Back to Operations Guide](README.md) | [Back to Documentation Home](../README.md)

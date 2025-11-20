# Database Backup and Restore

**Tags:** `operations`, `backup`, `restore`, `disaster-recovery`, `database`
**Last updated:** 2025-11-14

Complete guide for backing up and restoring the Cookbook Creator database, including disaster recovery procedures.

---

## Quick Reference

```bash
# Create backup
uv run python -m cookbook_db_utils.cli db backup

# Restore from backup (with confirmation)
uv run python -m cookbook_db_utils.cli db restore /path/to/backup.db

# Export content with images
uv run python -m cookbook_db_utils.cli utils export-content --output content.zip

# Import content to admin user
uv run python -m cookbook_db_utils.cli utils import-to-admin content.zip --admin-username admin
```

---

## Backup Strategy

### What to Back Up

**Database:**
- All tables and data
- Schema structure
- Indexes and constraints

**Files:**
- Uploaded recipe images
- Generated PDFs
- User avatars

**Configuration:**
- Environment variables
- Application configuration
- Migration history

---

## Database Backups

### Automatic Backup

Creates timestamped backup of entire database:

```bash
uv run python -m cookbook_db_utils.cli db backup
```

**Output:** `cookbook_db_dev_backup_20251114_153045.db`

**Backup location:** Same directory as database file

**What's backed up:**
- All tables
- All data
- Schema structure
- Alembic version history

### Custom Backup Location

```bash
uv run python -m cookbook_db_utils.cli db backup /path/to/backup.db
```

### Backup File Names

**Automatic naming format:**
```
cookbook_db_{env}_backup_{YYYYMMDD}_{HHMMSS}.db
```

**Examples:**
- `cookbook_db_dev_backup_20251114_153045.db`
- `cookbook_db_production_backup_20251114_080000.db`

---

## Restore Operations

### Basic Restore

Restore from a backup file:

```bash
uv run python -m cookbook_db_utils.cli db restore /path/to/backup.db
```

**Process:**
1. Creates pre-restore backup of current database
2. Prompts for confirmation
3. Replaces current database with backup
4. Verifies restore success

**Pre-restore backup:** `cookbook_db_dev_pre_restore_20251114_153100.db`

### Skip Confirmation

For automated scripts:

```bash
uv run python -m cookbook_db_utils.cli db restore /path/to/backup.db -y
```

### Restore to Different Environment

```bash
# Restore production backup to dev environment
uv run python -m cookbook_db_utils.cli --env dev db restore prod_backup.db
```

---

## Content Export/Import

For moving recipes and cookbooks between environments without user data.

### Export Content Only

Export recipes, cookbooks, and images without user-specific data:

```bash
uv run python -m cookbook_db_utils.cli utils export-content --output content.zip
```

**Includes:**
- Recipes (title, description, ingredients, instructions)
- Recipe images
- Cookbooks
- Tags
- Image files

**Excludes:**
- User accounts
- Passwords
- Sessions
- Personal notes
- Comments
- Payment data

### Export with Options

```bash
# Export to specific location
uv run python -m cookbook_db_utils.cli utils export-content --output /backups/content.zip

# Export specific cookbook
uv run python -m cookbook_db_utils.cli utils export-content --cookbook-id 5 --output cookbook5.zip
```

### Import to Admin User

Import content and assign all recipes to an admin user:

```bash
uv run python -m cookbook_db_utils.cli utils import-to-admin content.zip \
    --admin-username admin \
    --create-admin
```

**Options:**
- `--create-admin` - Create admin user if doesn't exist
- `--password PASSWORD` - Set admin password (default: generated)
- `--overwrite` - Replace existing content

**Process:**
1. Extracts ZIP file
2. Creates/finds admin user
3. Imports recipes and assigns to admin
4. Imports images to storage
5. Links cookbooks to admin

### Full Data Export

Export everything including user data:

```bash
uv run python -m cookbook_db_utils.cli utils export-all \
    --output full_backup.zip \
    --include-users
```

**Includes:**
- All content (recipes, cookbooks, images)
- User accounts and profiles
- Personal notes and comments
- Subscription data
- Payment history (excluding sensitive details)

**Warning:** Contains sensitive user data. Handle securely!

---

## File Backups

### Uploaded Images

**Location:** `backend/uploads/`

**Backup command:**
```bash
# Using tar
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz backend/uploads/

# Using rsync for incremental
rsync -av --progress backend/uploads/ /backup/uploads/
```

### Cloudinary Images

If using Cloudinary as primary storage, images are backed up automatically.

**Verify Cloudinary backup:**
- Check Cloudinary dashboard
- Download media library archive
- Use Cloudinary Admin API

---

## Backup Schedule

### Recommended Schedule

| Environment | Frequency | Retention | Method |
|-------------|-----------|-----------|---------|
| **Development** | Daily | 7 days | Automated script |
| **Staging** | Daily | 14 days | Automated script |
| **Production** | Every 6 hours | 30 days | Automated + manual |

### Production Backup Script

**Location:** `scripts/backup.sh`

```bash
#!/bin/bash
# Production backup script

BACKUP_DIR="/backups/cookbook-creator"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump cookbook_db > "$BACKUP_DIR/db_$DATE.sql"

# Files backup
tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" backend/uploads/

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "db_*.sql" -mtime +30 -delete
find "$BACKUP_DIR" -name "uploads_*.tar.gz" -mtime +30 -delete

# Log
echo "Backup completed: $DATE" >> "$BACKUP_DIR/backup.log"
```

### Automated Backups with Cron

```bash
# Edit crontab
crontab -e

# Add backup schedule (every 6 hours)
0 */6 * * * /path/to/scripts/backup.sh

# Or daily at 2 AM
0 2 * * * /path/to/scripts/backup.sh
```

---

## Disaster Recovery

### Recovery Scenarios

#### Scenario 1: Accidental Data Deletion

**Problem:** User accidentally deleted recipes or data.

**Solution:**
```bash
# 1. Find most recent backup
ls -lt backups/

# 2. Restore from backup
uv run python -m cookbook_db_utils.cli db restore backups/latest.db

# 3. Verify data
uv run python -m cookbook_db_utils.cli db status
```

#### Scenario 2: Database Corruption

**Problem:** Database file corrupted or unreadable.

**Solution:**
```bash
# 1. Stop application
systemctl stop cookbook-creator

# 2. Attempt database repair (SQLite)
sqlite3 cookbook.db "PRAGMA integrity_check;"

# 3. If repair fails, restore from backup
uv run python -m cookbook_db_utils.cli db restore backups/latest.db

# 4. Run migrations if needed
uv run python -m cookbook_db_utils.cli migrate upgrade

# 5. Restart application
systemctl start cookbook-creator
```

#### Scenario 3: Failed Migration

**Problem:** Migration failed, database in inconsistent state.

**Solution:**
```bash
# 1. Restore pre-migration backup
uv run python -m cookbook_db_utils.cli db restore backups/before_migration.db

# 2. Fix migration issue
# Edit migration file or create hotfix

# 3. Reapply migration
uv run python -m cookbook_db_utils.cli migrate upgrade
```

#### Scenario 4: Complete System Failure

**Problem:** Server crash, complete data loss.

**Solution:**
```bash
# 1. Set up new server
# Install dependencies, configure environment

# 2. Restore latest database backup
uv run python -m cookbook_db_utils.cli db restore /remote/backup/latest.db

# 3. Restore file uploads
tar -xzf /remote/backup/uploads_latest.tar.gz -C backend/

# 4. Run migrations to latest
uv run python -m cookbook_db_utils.cli migrate upgrade

# 5. Verify application
uv run python run.py
```

---

## Backup Verification

### Test Restore Regularly

**Monthly verification:**

```bash
# 1. Create test environment
export FLASK_ENV=testing

# 2. Restore latest backup
uv run python -m cookbook_db_utils.cli --env testing db restore latest_backup.db

# 3. Verify data integrity
uv run python -m cookbook_db_utils.cli --env testing utils validate

# 4. Test application
uv run python run.py

# 5. Document results
echo "Backup verified: $(date)" >> backup_verification.log
```

### Automated Verification Script

```bash
#!/bin/bash
# verify_backup.sh

BACKUP_FILE="$1"
TEST_DB="test_restore.db"

# Restore to test database
python -m cookbook_db_utils.cli db restore "$BACKUP_FILE" --output "$TEST_DB" -y

# Run integrity checks
python -m cookbook_db_utils.cli utils validate --database "$TEST_DB"

# Check record counts
python -m cookbook_db_utils.cli db status --database "$TEST_DB"

# Cleanup
rm "$TEST_DB"

echo "Backup verification complete"
```

---

## Point-in-Time Recovery

For PostgreSQL production databases:

### Enable WAL Archiving

**postgresql.conf:**
```
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backup/wal_archive/%f'
```

### Create Base Backup

```bash
pg_basebackup -D /backup/base -Ft -z -P
```

### Restore to Specific Time

```bash
# 1. Stop PostgreSQL
systemctl stop postgresql

# 2. Restore base backup
tar -xzf /backup/base/base.tar.gz -C /var/lib/postgresql/data

# 3. Create recovery.conf
cat > /var/lib/postgresql/data/recovery.conf <<EOF
restore_command = 'cp /backup/wal_archive/%f %p'
recovery_target_time = '2025-11-14 15:30:00'
EOF

# 4. Start PostgreSQL
systemctl start postgresql
```

---

## Offsite Backups

### Cloud Storage

**AWS S3:**
```bash
# Upload backup
aws s3 cp backup.db s3://cookbook-backups/$(date +%Y%m%d)/backup.db

# Automated with script
aws s3 sync /local/backups s3://cookbook-backups/ --exclude "*" --include "*.db"
```

**Google Cloud Storage:**
```bash
gsutil cp backup.db gs://cookbook-backups/$(date +%Y%m%d)/backup.db
```

### Backup Encryption

**Encrypt before upload:**
```bash
# Encrypt backup
gpg --encrypt --recipient admin@example.com backup.db

# Upload encrypted backup
aws s3 cp backup.db.gpg s3://cookbook-backups/
```

**Decrypt for restore:**
```bash
# Download
aws s3 cp s3://cookbook-backups/backup.db.gpg .

# Decrypt
gpg --decrypt backup.db.gpg > backup.db
```

---

## Backup Storage Management

### Retention Policy

**Development:** 7 days
```bash
find /backups -name "dev_*.db" -mtime +7 -delete
```

**Production:** 30 days full, 90 days monthly
```bash
# Keep daily for 30 days
find /backups/daily -name "*.db" -mtime +30 -delete

# Keep monthly for 90 days
find /backups/monthly -name "*.db" -mtime +90 -delete
```

### Backup Size Monitoring

```bash
# Check backup sizes
du -h /backups/*.db | sort -hr

# Alert if backup size unusual
LAST_SIZE=$(stat -f%z latest_backup.db)
AVG_SIZE=50000000  # 50MB average

if [ $LAST_SIZE -lt $(($AVG_SIZE / 2)) ]; then
    echo "Warning: Backup size unusually small!"
fi
```

---

## Best Practices

### Do's

✅ **Automate daily backups**
✅ **Test restores regularly (monthly)**
✅ **Store backups offsite**
✅ **Encrypt sensitive backups**
✅ **Document backup procedures**
✅ **Monitor backup success/failure**
✅ **Keep multiple backup generations**
✅ **Backup before major changes**

### Don'ts

❌ **Don't rely on single backup**
❌ **Don't skip backup verification**
❌ **Don't store only on same server**
❌ **Don't ignore backup failures**
❌ **Don't forget file backups (uploads)**
❌ **Don't expose backups publicly**

---

## Troubleshooting

### Backup Failed - Disk Full

```bash
# Check disk space
df -h

# Clean old backups
find /backups -mtime +30 -delete

# Compress backups
gzip backup.db
```

### Restore Failed - Version Mismatch

```bash
# Check migration version in backup
sqlite3 backup.db "SELECT version_num FROM alembic_version;"

# Apply missing migrations after restore
uv run python -m cookbook_db_utils.cli migrate upgrade
```

### Backup File Corrupted

```bash
# Verify backup integrity
sqlite3 backup.db "PRAGMA integrity_check;"

# If corrupted, use previous backup
ls -lt /backups/ | head -5
```

---

## Emergency Contacts

**For backup emergencies:**

1. **Check backup status:** `backup.log`
2. **Verify last successful backup:** `ls -lt /backups/`
3. **Contact:** Database administrator
4. **Escalate if:** Data loss > 24 hours

---

## See Also

- [Database Migrations](database-migrations.md) - Schema change management
- [Database CLI](database-cli.md) - Complete CLI reference
- [Deployment Guide](../deployment/production.md) - Production deployment
- [Troubleshooting](troubleshooting.md) - Common issues

---

[← Back to Operations Guide](README.md) | [Back to Documentation Home](../README.md)

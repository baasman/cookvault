# Operations Guide

**Tags:** `operations`, `database`, `maintenance`, `monitoring`, `devops`
**Last updated:** 2025-11-14

Complete guide for database operations, monitoring, maintenance, and system administration.

---

## 📖 Documentation

### 🗄️ Database Management

#### [Database CLI](database-cli.md)
Complete CLI tool reference for database operations:
- Database initialization and reset
- Migration management
- Data seeding and cleanup
- Backup and restore
- User management
- PDF processing workflows
- Validation and statistics

#### [Database Migrations](database-migrations.md)
Schema change management with Flask-Migrate/Alembic:
- Creating and applying migrations
- Rolling back changes
- Data migrations
- Testing migrations
- Production deployment procedures
- Troubleshooting migration issues

#### [Backup and Restore](backup-restore.md)
Data protection and disaster recovery:
- Automated backup strategies
- Restore procedures
- Content export/import
- Point-in-time recovery
- Offsite backup management
- Disaster recovery scenarios

### 📊 Monitoring & Maintenance

#### [Monitoring and Logging](monitoring.md)
System health and observability:
- Health check endpoints
- System metrics
- Log management and analysis
- Performance monitoring
- Alerting strategies
- Troubleshooting checklists

---

## 🚀 Quick Start

### Initial Setup

```bash
# Initialize database
uv run python -m cookbook_db_utils.cli init

# Seed test users (development)
uv run python -m cookbook_db_utils.cli seed users-only

# Check status
uv run python -m cookbook_db_utils.cli status
```

### Daily Operations

```bash
# Check system health
curl http://localhost:5001/health

# View application logs
tail -f logs/cookbook-creator.log

# Check database status
uv run python -m cookbook_db_utils.cli db status

# Backup database
uv run python -m cookbook_db_utils.cli db backup
```

---

## 📋 Common Tasks

### Database Operations

**Initialize new database:**
```bash
uv run python -m cookbook_db_utils.cli init
```

**Apply pending migrations:**
```bash
uv run python -m cookbook_db_utils.cli migrate upgrade
```

**Create backup:**
```bash
uv run python -m cookbook_db_utils.cli db backup
```

**Restore from backup:**
```bash
uv run python -m cookbook_db_utils.cli db restore /path/to/backup.db
```

**Check database status:**
```bash
uv run python -m cookbook_db_utils.cli db status
```

### Migrations

**Create new migration:**
```bash
uv run python -m cookbook_db_utils.cli migrate generate "description of changes"
```

**Check migration status:**
```bash
uv run python -m cookbook_db_utils.cli migrate status
```

**List all migrations:**
```bash
uv run python -m cookbook_db_utils.cli migrate list
```

**Rollback to specific version:**
```bash
uv run python -m cookbook_db_utils.cli migrate rollback <revision_id>
```

### User Management

**Create admin user:**
```bash
uv run python -m cookbook_db_utils.cli user create-admin \
    --username admin \
    --email admin@example.com \
    --password secure_password
```

**List users:**
```bash
uv run python -m cookbook_db_utils.cli user list
```

**Grant admin privileges:**
```bash
uv run python -m cookbook_db_utils.cli user make-admin <username>
```

### Data Management

**Seed test data:**
```bash
# Users only (recommended)
uv run python -m cookbook_db_utils.cli seed users-only

# All test data
uv run python -m cookbook_db_utils.cli seed all
```

**Validate data integrity:**
```bash
uv run python -m cookbook_db_utils.cli utils validate
```

**Clean up orphaned records:**
```bash
uv run python -m cookbook_db_utils.cli utils cleanup
```

**View statistics:**
```bash
uv run python -m cookbook_db_utils.cli utils stats
```

---

## 🔧 Maintenance Schedule

### Daily

- [ ] **Monitor logs** for errors and warnings
  ```bash
  grep ERROR logs/cookbook-creator.log | tail -20
  ```

- [ ] **Check disk space**
  ```bash
  df -h
  ```

- [ ] **Verify backup success**
  ```bash
  ls -lh backups/ | tail -5
  ```

- [ ] **Review health check**
  ```bash
  curl http://localhost:5001/api/health
  ```

### Weekly

- [ ] **Database cleanup**
  ```bash
  uv run python -m cookbook_db_utils.cli utils cleanup
  ```

- [ ] **Clear old sessions** (> 30 days)
  ```sql
  DELETE FROM user_session WHERE last_accessed < NOW() - INTERVAL '30 days';
  ```

- [ ] **Analyze database performance**
  ```bash
  uv run python -m cookbook_db_utils.cli utils stats
  ```

- [ ] **Review slow queries**
  ```sql
  SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
  ```

### Monthly

- [ ] **Verify backup restore** (test restore procedure)
- [ ] **Update dependencies** (security patches)
- [ ] **Review access logs** for suspicious activity
- [ ] **Rotate log files**
- [ ] **Database vacuum** (PostgreSQL)
  ```sql
  VACUUM ANALYZE;
  ```

---

## 📈 Performance Optimization

### Database Indexing

**Analyze query patterns:**
```sql
-- Find most frequent queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 20;

-- Find slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

**Add indexes for common queries:**
```sql
-- Index on frequently filtered columns
CREATE INDEX idx_recipes_user_id ON recipes(user_id);
CREATE INDEX idx_recipes_is_public ON recipes(is_public);

-- Composite index for multiple filters
CREATE INDEX idx_recipes_user_public ON recipes(user_id, is_public);

-- Index for sorting
CREATE INDEX idx_recipes_created_at_desc ON recipes(created_at DESC);
```

### Query Optimization

**Use EXPLAIN ANALYZE:**
```sql
EXPLAIN ANALYZE
SELECT r.*, u.username
FROM recipes r
JOIN users u ON r.user_id = u.id
WHERE r.is_public = true
ORDER BY r.created_at DESC
LIMIT 20;
```

**Look for:**
- Sequential scans (add indexes)
- High cost operations
- Inefficient joins

---

## 🚨 Monitoring & Alerting

### Key Metrics

**Application Metrics:**
- Response time (< 200ms normal, alert > 1000ms)
- Error rate (< 0.5% normal, alert > 2%)
- CPU usage (< 50% normal, alert > 80%)
- Memory usage (< 60% normal, alert > 85%)

**Database Metrics:**
- Connection count (alert if > 80% of pool)
- Query time (alert if > 500ms average)
- Database size (alert if growth > 20%/week)
- Lock wait time (alert if > 100ms)

**API Metrics:**
- Upload success rate (alert if < 90%)
- Authentication success (alert if < 95%)
- Cache hit rate (alert if < 60%)

### Health Check Endpoints

**Basic health:**
```bash
curl http://localhost:5001/health
```

**Detailed health with components:**
```bash
curl http://localhost:5001/api/health
```

**System metrics (admin only):**
```bash
curl http://localhost:5001/system/metrics \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## 🆘 Troubleshooting

### Service Won't Start

1. **Check logs:**
   ```bash
   tail -100 logs/cookbook-creator.log
   ```

2. **Verify environment:**
   ```bash
   env | grep FLASK
   env | grep DATABASE
   ```

3. **Check port availability:**
   ```bash
   lsof -i :5001
   ```

4. **Verify database connection:**
   ```bash
   uv run python -m cookbook_db_utils.cli db status
   ```

### Database Connection Issues

1. **Check database is running:**
   ```bash
   # PostgreSQL
   systemctl status postgresql

   # Or check connection
   psql -h localhost -U username -d cookbook_db -c "SELECT 1;"
   ```

2. **Verify connection string:**
   ```bash
   echo $DATABASE_URL
   ```

3. **Check connection pool:**
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

4. **Reset connections if needed:**
   ```bash
   # Restart application
   systemctl restart cookbook-creator
   ```

### Performance Issues

1. **Check system resources:**
   ```bash
   top
   free -h
   df -h
   iostat
   ```

2. **Analyze slow queries:**
   ```bash
   grep "Query took" logs/cookbook-creator.log | \
     awk '{print $NF}' | \
     sort -rn | \
     head -20
   ```

3. **Check database performance:**
   ```sql
   SELECT * FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

---

## 🔐 Security

### Database Security

**Access Control:**
- Use strong passwords
- Limit connections by IP
- Enable SSL/TLS for connections
- Regular password rotation
- Principle of least privilege

**Audit Logging:**
```sql
-- Enable audit logging (PostgreSQL)
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
```

**Backup Security:**
- Encrypt backups at rest
- Secure backup storage access
- Test restore procedures
- Document recovery processes

### Application Security

- Keep dependencies updated
- Monitor security advisories
- Regular security audits
- Implement rate limiting
- Validate all inputs

---

## 📞 Support & Escalation

### When to Escalate

**Immediate escalation (P0):**
- Service completely down
- Data loss or corruption
- Security breach

**Urgent escalation (P1):**
- Severe performance degradation
- Database unavailable
- Failed backups

**Normal support (P2):**
- Minor bugs
- Performance optimization
- Feature questions

### Escalation Process

1. **Check documentation** first
2. **Review logs** for errors
3. **Attempt basic troubleshooting**
4. **Escalate** if unresolved:
   - Describe issue clearly
   - Provide error logs
   - Note troubleshooting attempted
   - Assess severity/impact

---

## 📚 Additional Resources

### Internal Documentation

- **[Database CLI Reference](database-cli.md)** - Complete CLI documentation
- **[Migration Guide](database-migrations.md)** - Schema change management
- **[Backup Guide](backup-restore.md)** - Data protection procedures
- **[Monitoring Guide](monitoring.md)** - System health and logging

### External Resources

- **Flask-Migrate Documentation:** https://flask-migrate.readthedocs.io/
- **Alembic Documentation:** https://alembic.sqlalchemy.org/
- **PostgreSQL Documentation:** https://www.postgresql.org/docs/
- **SQLAlchemy Documentation:** https://docs.sqlalchemy.org/

---

## See Also

- [Deployment Guide](../deployment/production.md) - Production deployment
- [Architecture Overview](../architecture/overview.md) - System design
- [API Reference](../api/README.md) - API documentation
- [Development Guide](../development/README.md) - Development workflow

---

[← Back to Documentation Home](../README.md)

# Monitoring and Logging

**Tags:** `operations`, `monitoring`, `logging`, `observability`, `health-checks`
**Last updated:** 2025-11-14

Complete guide for monitoring the Cookbook Creator application, analyzing logs, and maintaining system health.

---

## Quick Reference

```bash
# Check application health
curl http://localhost:5001/health

# View live logs
tail -f logs/cookbook-creator.log

# Check database status
uv run python -m cookbook_db_utils.cli db status

# View application statistics
uv run python -m cookbook_db_utils.cli utils stats

# Check system metrics (admin only)
curl http://localhost:5001/system/metrics -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## Health Checks

### Basic Health Check

**Endpoint:** `GET /health`

**Purpose:** Quick service availability check

**Response:**
```json
{
  "status": "healthy",
  "service": "cookbook-creator-backend",
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK` - Service healthy
- `503 Service Unavailable` - Service down

**Use for:**
- Load balancer health checks
- Uptime monitoring
- Quick status verification

### Detailed Health Check

**Endpoint:** `GET /api/health`

**Purpose:** Component-level health verification

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 15
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "upload_directory": {
      "status": "healthy",
      "writable": true
    }
  },
  "timestamp": "2025-11-14T15:30:00Z"
}
```

**Component Statuses:**
- `healthy` - Component functioning normally
- `degraded` - Component slow but operational
- `unhealthy` - Component unavailable

**Use for:**
- Detailed diagnostics
- Component-level monitoring
- Troubleshooting

---

## System Metrics

### Application Metrics (Admin Only)

**Endpoint:** `GET /system/metrics`

**Authentication:** Admin token required

**Response:**
```json
{
  "process": {
    "memory": {
      "rss": 45678910,
      "vms": 123456789,
      "percent": 5.2
    },
    "cpu": {
      "percent": 12.5,
      "num_threads": 15
    },
    "uptime_seconds": 86400
  },
  "system": {
    "memory": {
      "total": 8589934592,
      "available": 4294967296,
      "percent": 50.0
    },
    "cpu": {
      "percent": 25.5,
      "count": 4
    },
    "disk": {
      "total": 500000000000,
      "used": 250000000000,
      "free": 250000000000,
      "percent": 50.0
    }
  },
  "timestamp": "2025-11-14T15:30:00Z"
}
```

**Use for:**
- Performance monitoring
- Resource planning
- Capacity management
- Load testing analysis

### Database Statistics

```bash
uv run python -m cookbook_db_utils.cli utils stats
```

**Output:**
```
Database Statistics
===================
Total Users: 150
Total Recipes: 1,250
Total Cookbooks: 85
Total Ingredients: 3,400
Total Recipe Images: 890

Storage:
- Database Size: 45.2 MB
- Image Storage: 2.3 GB

Recent Activity (24h):
- New Recipes: 12
- Recipe Views: 3,450
- API Requests: 15,600
```

---

## Logging

### Log Configuration

**Production Logging:**
- **Level:** WARNING (configurable via `LOG_LEVEL` env var)
- **File:** `logs/cookbook-creator.log`
- **Rotation:** 10MB per file, 10 file backup
- **Format:** `%(asctime)s %(levelname)s [%(name)s] %(message)s`

**Log Levels:**
- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational messages
- `WARNING` - Warning messages (default production)
- `ERROR` - Error messages
- `CRITICAL` - Critical failures

### Setting Log Level

```bash
# Environment variable
export LOG_LEVEL=INFO

# In .env file
LOG_LEVEL=INFO
```

### Log Locations

**Application Logs:**
```
logs/cookbook-creator.log        # Main application log
logs/cookbook-creator.log.1      # Rotated log (oldest)
logs/cookbook-creator.log.2
...
```

**Migration Logs:**
```
logs/migrations.log              # Alembic migration log
```

**Access Logs (Nginx/Apache):**
```
/var/log/nginx/access.log
/var/log/nginx/error.log
```

---

## Viewing Logs

### Real-Time Log Monitoring

**Follow live logs:**
```bash
tail -f logs/cookbook-creator.log
```

**Follow with filtering:**
```bash
# Only errors
tail -f logs/cookbook-creator.log | grep ERROR

# Only specific module
tail -f logs/cookbook-creator.log | grep "app.api.recipes"
```

### Log Analysis

**Recent errors:**
```bash
grep ERROR logs/cookbook-creator.log | tail -20
```

**Count errors by type:**
```bash
grep ERROR logs/cookbook-creator.log | cut -d' ' -f4- | sort | uniq -c | sort -rn
```

**Failed authentication attempts:**
```bash
grep "Invalid credentials" logs/cookbook-creator.log | wc -l
```

**API response times (if logged):**
```bash
grep "Request completed" logs/cookbook-creator.log | \
  awk '{print $NF}' | \
  sort -n | \
  awk '{sum+=$1} END {print "Average:", sum/NR, "ms"}'
```

---

## Key Metrics to Monitor

### Application Metrics

| Metric | Normal Range | Alert Threshold | Action |
|--------|--------------|-----------------|--------|
| **Response Time** | < 200ms | > 1000ms | Investigate slow queries |
| **Error Rate** | < 0.5% | > 2% | Check error logs |
| **CPU Usage** | < 50% | > 80% | Scale up or optimize |
| **Memory Usage** | < 60% | > 85% | Check for leaks |
| **Disk Usage** | < 70% | > 90% | Clean up or expand |

### Database Metrics

| Metric | Normal Range | Alert Threshold | Action |
|--------|--------------|-----------------|--------|
| **Connection Count** | < 50 | > 80 (of 100 pool) | Check connection leaks |
| **Query Time** | < 100ms | > 500ms | Optimize queries |
| **Database Size** | Varies | Growth > 20%/week | Review data retention |
| **Lock Wait Time** | < 10ms | > 100ms | Check for deadlocks |

### API Metrics

| Metric | Normal Range | Alert Threshold | Action |
|--------|--------------|-----------------|--------|
| **Upload Success Rate** | > 95% | < 90% | Check OCR service |
| **Authentication Success** | > 98% | < 95% | Check auth service |
| **Cache Hit Rate** | > 80% | < 60% | Review cache strategy |

---

## Alerting

### Critical Alerts

**Immediate action required:**

1. **Service Down**
   - Health check fails for 5 minutes
   - Action: Restart service, check logs

2. **Database Unreachable**
   - Cannot connect to database
   - Action: Check database server, network

3. **Disk Full**
   - Disk usage > 95%
   - Action: Clean logs, expand storage

4. **High Error Rate**
   - Error rate > 5% for 10 minutes
   - Action: Check error logs, rollback if needed

### Warning Alerts

**Investigation needed:**

1. **High Response Time**
   - Average response > 1s for 15 minutes
   - Action: Check database queries, CPU usage

2. **Memory Leak**
   - Memory usage steadily increasing
   - Action: Monitor for leak, restart if needed

3. **Failed Backups**
   - Backup job failed
   - Action: Check disk space, run manual backup

### Setting Up Alerts

**Example: Email alerts for errors**

```python
# In logging configuration
import logging
from logging.handlers import SMTPHandler

if not app.debug:
    mail_handler = SMTPHandler(
        mailhost='smtp.gmail.com',
        fromaddr='alerts@cookbook.com',
        toaddrs=['admin@cookbook.com'],
        subject='Cookbook Creator Error'
    )
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)
```

---

## Common Issues

### High CPU Usage

**Symptoms:**
- Slow API responses
- High system load

**Diagnosis:**
```bash
# Check process CPU
ps aux | grep python | head -5

# Check system load
uptime

# Profile application
python -m cProfile run.py
```

**Common causes:**
- OCR processing bottleneck
- Inefficient database queries
- Infinite loops
- Too many concurrent requests

**Solutions:**
- Optimize OCR batch processing
- Add database indexes
- Increase worker count
- Implement rate limiting

### High Memory Usage

**Symptoms:**
- Application crashes with OOM
- Slow performance over time

**Diagnosis:**
```bash
# Check memory usage
ps aux | grep python

# Monitor memory growth
watch -n 5 'ps aux | grep python | grep -v grep'
```

**Common causes:**
- Memory leaks in image processing
- Large result sets loaded to memory
- Caching too much data

**Solutions:**
- Use streaming for large responses
- Implement pagination
- Clear caches periodically
- Restart workers regularly

### Database Connection Exhaustion

**Symptoms:**
- "Too many connections" errors
- API timeouts

**Diagnosis:**
```bash
# Check active connections (PostgreSQL)
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Show connection details
psql -c "SELECT * FROM pg_stat_activity ORDER BY backend_start;"
```

**Solutions:**
- Increase connection pool size
- Fix connection leaks (close connections)
- Implement connection timeouts
- Use connection pooling (PgBouncer)

---

## Performance Monitoring

### Request Tracing

Add timing middleware to track request performance:

```python
import time
from flask import request

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def log_request(response):
    duration = (time.time() - request.start_time) * 1000
    app.logger.info(f"{request.method} {request.path} - {response.status_code} - {duration:.2f}ms")
    return response
```

### Slow Query Logging

Enable PostgreSQL slow query logging:

```sql
-- Set threshold to 100ms
ALTER DATABASE cookbook_db SET log_min_duration_statement = 100;

-- View slow queries
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Database Query Analysis

```bash
# Analyze query performance
uv run python -m cookbook_db_utils.cli utils analyze-queries

# Show most expensive queries
grep "Query took" logs/cookbook-creator.log | \
  awk '{print $NF}' | \
  sort -rn | \
  head -10
```

---

## Monitoring Tools

### Recommended Tools

**Application Performance Monitoring (APM):**
- **Sentry** - Error tracking and performance
- **New Relic** - Full-stack monitoring
- **Datadog** - Infrastructure and application monitoring

**Log Management:**
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk** - Enterprise log analysis
- **Papertrail** - Cloud log management

**Uptime Monitoring:**
- **UptimeRobot** - Simple uptime checks
- **Pingdom** - Website monitoring
- **StatusCake** - Performance monitoring

**Infrastructure:**
- **Prometheus + Grafana** - Metrics and dashboards
- **Nagios** - Infrastructure monitoring
- **Zabbix** - Enterprise monitoring

### Setting Up Basic Monitoring

**Health check with cron:**
```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:5001/health || echo "Service down!" | mail -s "Alert" admin@example.com
```

**Log monitoring with logrotate:**
```
/path/to/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload cookbook-creator
    endscript
}
```

---

## Troubleshooting Checklist

### Service Won't Start

- [ ] Check logs: `tail -f logs/cookbook-creator.log`
- [ ] Verify environment variables: `env | grep FLASK`
- [ ] Check port availability: `lsof -i :5001`
- [ ] Verify database connection: `uv run python -m cookbook_db_utils.cli db status`
- [ ] Check file permissions: `ls -la`

### Slow Performance

- [ ] Check CPU usage: `top`
- [ ] Check memory: `free -h`
- [ ] Check disk I/O: `iostat`
- [ ] Analyze slow queries: See [Slow Query Logging](#slow-query-logging)
- [ ] Check database indexes: Run `EXPLAIN` on slow queries
- [ ] Review recent code changes

### Database Issues

- [ ] Verify database is running
- [ ] Check connection pool: `SELECT count(*) FROM pg_stat_activity;`
- [ ] Run integrity check: `uv run python -m cookbook_db_utils.cli utils validate`
- [ ] Check disk space: `df -h`
- [ ] Review migration status: `uv run python -m cookbook_db_utils.cli migrate status`

---

## See Also

- [Database CLI](database-cli.md) - Database management commands
- [Backup and Restore](backup-restore.md) - Data protection
- [Database Migrations](database-migrations.md) - Schema changes
- [Deployment Guide](../deployment/production.md) - Production setup

---

[← Back to Operations Guide](README.md) | [Back to Documentation Home](../README.md)

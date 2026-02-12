# Log Aggregation Setup Guide

This guide covers setting up centralized log aggregation for Cookle production services using Papertrail.

---

## Why Log Aggregation?

With multiple services (backend, frontend, worker, database), logs are scattered across Render's individual service dashboards. A log aggregation service:

- **Centralizes all logs** in one searchable interface
- **Enables saved searches** for quick issue identification
- **Provides alerting** on error patterns
- **Retains logs longer** than Render's default retention

---

## Option 1: Papertrail (Recommended)

Papertrail offers a free tier (50MB/month, 7 days retention) suitable for small applications.

### Step 1: Create Papertrail Account

1. Go to https://papertrailapp.com
2. Sign up for a free account
3. Verify your email

### Step 2: Get Your Log Destination

1. After signing in, go to **Settings** > **Log Destinations**
2. Click **Create Log Destination**
3. Note the destination URL, it looks like:
   ```
   logs.papertrailapp.com:XXXXX
   ```
   (XXXXX is your unique port number)

### Step 3: Configure Render Log Drain

1. Go to Render Dashboard: https://dashboard.render.com
2. For **each service** (backend, worker):
   - Click on the service
   - Go to **Settings** tab
   - Scroll to **Log Streams**
   - Click **Add Log Stream**
   - Select **Papertrail**
   - Enter your Papertrail host: `logs.papertrailapp.com`
   - Enter your port: `XXXXX`
   - Click **Save**

3. Repeat for all services you want to monitor:
   - [ ] Backend web service
   - [ ] Celery worker (if applicable)

### Step 4: Verify Logs Are Flowing

1. Go to Papertrail **Events** page
2. You should see logs appearing from your services
3. Each service will have its own "system" identifier

---

## Setting Up Saved Searches

In Papertrail, create saved searches for quick access to common issues.

### Search 1: All Errors (500s)

**Name:** `Production Errors`
**Query:**
```
("ERROR" OR "error" OR "Exception" OR "500" OR "Internal Server Error")
```

### Search 2: Authentication Failures

**Name:** `Auth Failures`
**Query:**
```
("Invalid credentials" OR "Authentication failed" OR "Unauthorized" OR "401" OR "403")
```

### Search 3: Slow Requests

**Name:** `Slow Requests`
**Query:**
```
("took" AND ("5000ms" OR "6000ms" OR "7000ms" OR "8000ms" OR "9000ms" OR "10000ms"))
```
Or if using structured logging with duration:
```
duration:>5000
```

### Search 4: Database Issues

**Name:** `Database Issues`
**Query:**
```
("database" OR "PostgreSQL" OR "connection" OR "pool") AND ("error" OR "failed" OR "timeout")
```

### Search 5: Redis Issues

**Name:** `Redis Issues`
**Query:**
```
("redis" OR "Redis") AND ("error" OR "failed" OR "connection" OR "timeout")
```

### Creating Saved Searches

1. Go to **Events** page
2. Enter the search query
3. Click **Save Search**
4. Name it and save

---

## Setting Up Alerts

Configure alerts to be notified of issues automatically.

### Alert 1: High Error Rate

1. Go to saved search "Production Errors"
2. Click **Create Alert**
3. Configure:
   - **Alert when:** Count exceeds 10 in 5 minutes
   - **Notification:** Email (or Slack webhook)
4. Save

### Alert 2: Critical Errors

1. Create search: `("CRITICAL" OR "fatal" OR "panic")`
2. Click **Create Alert**
3. Configure:
   - **Alert when:** Count exceeds 1 in 5 minutes
   - **Notification:** Email
4. Save

### Alert 3: Authentication Spike

1. Go to saved search "Auth Failures"
2. Click **Create Alert**
3. Configure:
   - **Alert when:** Count exceeds 20 in 10 minutes
   - **Notification:** Email
4. Save

---

## Option 2: Render Native Logs

If you prefer not to use an external service, Render provides basic log viewing:

### Accessing Logs

1. Go to Render Dashboard
2. Click on any service
3. Click **Logs** tab
4. Use the search box to filter

### Limitations

- No saved searches
- No alerting
- Limited retention
- Can't search across multiple services at once

---

## Option 3: Better Stack (Logtail)

Better Stack offers a modern alternative with a generous free tier.

### Setup

1. Sign up at https://betterstack.com
2. Create a new source for each service
3. Configure Render log drain with the provided endpoint
4. Set up alerts in Better Stack dashboard

---

## Log Format Best Practices

For better searchability, ensure your application logs include:

```python
# Good log format
logger.info("Recipe created", extra={
    "user_id": user.id,
    "recipe_id": recipe.id,
    "duration_ms": 150
})

# Results in searchable structured data
```

### Current Log Format

The backend uses Python's standard logging:
```
2026-02-12 10:30:45,123 INFO [app.api.recipes] Recipe created for user 123
```

---

## Troubleshooting

### Logs Not Appearing in Papertrail

1. **Check Log Drain Configuration:**
   - Verify host and port are correct
   - Ensure log drain is enabled (green status)

2. **Check Service Is Running:**
   - Render service must be active to send logs

3. **Wait a Few Minutes:**
   - Log drain setup can take 2-3 minutes to start flowing

### Search Not Finding Expected Results

1. **Check Time Range:**
   - Papertrail defaults to last hour
   - Expand range if needed

2. **Check Query Syntax:**
   - Papertrail uses specific search syntax
   - Wrap phrases in quotes

---

## Quick Reference

| Service | Dashboard | Purpose |
|---------|-----------|---------|
| Papertrail | https://papertrailapp.com | Log aggregation |
| Render Logs | https://dashboard.render.com | Native logs |
| Better Stack | https://betterstack.com | Alternative |

### Recommended Saved Searches

| Name | Query | Alert? |
|------|-------|--------|
| Production Errors | `ERROR OR Exception OR 500` | Yes (>10/5min) |
| Auth Failures | `Invalid credentials OR 401` | Yes (>20/10min) |
| Slow Requests | `duration:>5000` | No |
| Database Issues | `database error OR connection failed` | Yes (>5/5min) |
| Redis Issues | `redis error OR redis connection` | Yes (>5/5min) |

---

## See Also

- [Monitoring Guide](monitoring.md) - Application metrics
- [Alerting Setup](ALERTING_SETUP.md) - Sentry and uptime alerts
- [Incident Response](incident-response.md) - Responding to issues

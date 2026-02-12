# Incident Response Guide

**Last Updated:** February 12, 2026

This document outlines how to respond to production incidents affecting Cookle (CookVault).

---

## Severity Levels

| Level | Name | Description | Response Time | Examples |
|-------|------|-------------|---------------|----------|
| **P1** | Critical | Complete service outage or data loss | < 15 min | App unreachable, database corruption, security breach |
| **P2** | High | Major feature broken, significant user impact | < 1 hour | Login broken, recipe upload failing, payments down |
| **P3** | Medium | Feature degraded, workaround available | < 4 hours | Slow performance, image processing delays, minor UI bugs |
| **P4** | Low | Minor issue, minimal user impact | < 24 hours | Cosmetic issues, non-critical feature bugs |

---

## Key Contacts

| Role | Name | Contact | Availability |
|------|------|---------|--------------|
| Primary On-Call | Boudewijn | boudeyz@gmail.com | Primary contact |

**External Services:**
- **Render Support:** support@render.com or dashboard
- **Stripe Support:** dashboard.stripe.com/support
- **Sentry:** sentry.io dashboard for error details
- **Cloudinary:** cloudinary.com dashboard

---

## Incident Response Process

### 1. Detection
Incidents can be detected via:
- **Sentry alerts** - Error rate spikes, new issues
- **UptimeRobot** - Downtime alerts (when configured)
- **User reports** - Customer complaints
- **Manual checks** - Health endpoint monitoring

### 2. Assessment
1. Check health endpoints:
   ```bash
   curl https://cookvault-exaq.onrender.com/health
   curl https://cookvault-exaq.onrender.com/api/health
   ```
2. Review Sentry for recent errors
3. Check Render dashboard for service status
4. Determine severity level (P1-P4)

### 3. Communication
- P1/P2: Immediately notify stakeholders
- Document incident start time
- Post status updates every 30 minutes for P1, hourly for P2

### 4. Resolution
- Follow relevant runbook below
- Document all actions taken
- Test fix before declaring resolved

### 5. Post-Incident
- Create post-mortem for P1/P2 incidents
- Document root cause and preventive measures
- Update runbooks if needed

---

## Runbooks

### Database Connection Failures

**Symptoms:**
- Health check shows database unhealthy
- API returns 500 errors
- Sentry shows SQLAlchemy connection errors

**Diagnosis:**
```bash
# Check Render dashboard for database status
# View recent logs in Render

# From Render shell (if available):
psql $DATABASE_URL -c "SELECT 1"
```

**Resolution Steps:**

1. **Check if database is running:**
   - Go to Render dashboard > PostgreSQL service
   - Check status and recent events

2. **Check connection limits:**
   - Free tier: 1 connection limit
   - Paid tier: Higher limits
   - May need to restart backend to clear stale connections

3. **Restart backend service:**
   - Render dashboard > Web Service > Manual Deploy
   - Or: Suspend then Resume

4. **If database is down:**
   - Check Render status page for outages
   - Contact Render support for P1

5. **If connection pool exhausted:**
   - Check for connection leaks in code
   - Restart service to clear connections
   - Consider upgrading database plan

**Prevention:**
- Monitor connection count
- Use connection pooling
- Implement proper connection cleanup

---

### Redis Unavailable

**Symptoms:**
- Health check shows Redis unhealthy
- Caching not working
- Rate limiting not functioning
- Celery tasks stuck

**Diagnosis:**
```bash
# Check Render dashboard for Redis status
# View logs for Redis connection errors
```

**Resolution Steps:**

1. **Check Redis service status:**
   - Render dashboard > Redis/Key-Value service
   - Check memory usage and status

2. **If memory full:**
   - Clear cache keys if possible
   - Upgrade plan for more memory
   - Review cache eviction policy

3. **If Redis is down:**
   - Restart the Redis service in Render
   - Check Render status page

4. **App graceful degradation:**
   - App should continue working without cache
   - Rate limiting will be less accurate
   - Monitor for cascading failures

**Prevention:**
- Set appropriate maxmemory policy
- Monitor memory usage
- Consider Redis persistence settings

---

### High Error Rate

**Symptoms:**
- Sentry alert for error spike
- Multiple 500 errors in logs
- Users reporting failures

**Diagnosis:**
1. Go to Sentry dashboard
2. Check "Issues" sorted by frequency
3. Look for common stack traces
4. Check if errors correlate with recent deploy

**Resolution Steps:**

1. **Identify the error pattern:**
   - Is it one error type or many?
   - Is it affecting all users or specific ones?
   - Did it start after a deploy?

2. **If caused by recent deploy:**
   ```bash
   # Roll back to previous deploy in Render
   # Dashboard > Deploys > Select previous successful deploy > Rollback
   ```

3. **If caused by external service:**
   - Check Stripe, Cloudinary, Anthropic status
   - Implement circuit breaker if not present
   - Add fallback behavior

4. **If caused by bad data:**
   - Identify affected records
   - Fix data or add defensive code
   - Deploy fix

5. **If cause unknown:**
   - Enable DEBUG logging temporarily
   - Add more error context
   - Monitor closely

**Prevention:**
- Test thoroughly before deploy
- Use feature flags for risky changes
- Monitor error rate after deploys

---

### Celery Worker Down

**Symptoms:**
- Background jobs not processing
- Recipe processing stuck in "processing" state
- Queue backing up

**Diagnosis:**
```bash
# Check worker service in Render dashboard
# View worker logs for errors
```

**Resolution Steps:**

1. **Check worker service status:**
   - Render dashboard > Background Worker service
   - Check if it's running

2. **If worker crashed:**
   - Check logs for crash reason
   - Restart worker service

3. **If queue is backed up:**
   - Worker may be overwhelmed
   - Check for stuck/long-running tasks
   - Scale up workers if needed

4. **If Redis connection issue:**
   - See "Redis Unavailable" runbook
   - Worker needs Redis for task queue

5. **Recovery of stuck jobs:**
   - Jobs may need to be manually retried
   - Check database for "processing" status recipes
   - Update status or re-queue

**Prevention:**
- Set task timeouts
- Monitor queue depth
- Add retry logic with exponential backoff

---

### Frontend Not Loading

**Symptoms:**
- Blank page on cookvault-frontend.onrender.com
- JavaScript errors in browser console
- Assets not loading

**Diagnosis:**
1. Check browser developer console for errors
2. Check Render dashboard for frontend service status
3. Check if it's a DNS or SSL issue

**Resolution Steps:**

1. **Check service status:**
   - Render dashboard > Static Site service
   - Check recent deploy status

2. **If deploy failed:**
   - Check build logs for errors
   - TypeScript/build errors need code fix
   - Redeploy after fixing

3. **If assets 404:**
   - May be routing issue
   - Check that `_redirects` or routing is configured

4. **If CORS errors:**
   - Check backend CORS configuration
   - Verify allowed origins include frontend URL

5. **If blank but no errors:**
   - May be React rendering issue
   - Check ErrorBoundary for caught errors

**Prevention:**
- Test build locally before push
- Monitor TypeScript errors in CI
- Use error boundaries

---

### API Rate Limiting Issues

**Symptoms:**
- Users getting 429 Too Many Requests
- Legitimate traffic being blocked

**Diagnosis:**
```bash
# Check rate limit configuration in backend
# Review logs for rate limit hits
```

**Resolution Steps:**

1. **If limits too strict:**
   - Review rate limit settings in code
   - Adjust RATELIMIT_DEFAULT env var

2. **If abuse detected:**
   - Keep limits, investigate source
   - Consider IP blocking if necessary

3. **Temporary relief:**
   - Restart backend (clears rate limit counters if Redis is cache-only)
   - Increase limits temporarily

**Prevention:**
- Set reasonable default limits
- Monitor rate limit hit frequency
- Consider per-endpoint limits

---

### Payment Processing Failures

**Symptoms:**
- Users unable to purchase/subscribe
- Stripe webhook failures
- Payment stuck in pending

**Diagnosis:**
1. Check Stripe dashboard for failed payments
2. Check webhook logs in Stripe
3. Check backend logs for Stripe errors

**Resolution Steps:**

1. **Check Stripe service status:**
   - status.stripe.com

2. **If webhook failing:**
   - Check webhook endpoint is responding
   - Verify webhook secret is configured
   - Check Stripe dashboard for failed webhook attempts

3. **If API key issue:**
   - Verify STRIPE_SECRET_KEY is set correctly
   - Check if key was rotated

4. **For stuck payments:**
   - May need manual intervention in Stripe dashboard
   - Update order status in database if needed

**Prevention:**
- Monitor webhook success rate
- Set up Stripe alerts
- Test webhook endpoint regularly

---

## Quick Reference Commands

### Health Checks
```bash
# Basic health
curl https://cookvault-exaq.onrender.com/health

# Detailed health
curl https://cookvault-exaq.onrender.com/api/health
```

### Render Dashboard
- Services: https://dashboard.render.com
- PostgreSQL: Check "PostgreSQL" in services
- Redis: Check "Key Value" in services

### Sentry
- Dashboard: https://sentry.io
- Filter by environment: `environment:production`

### Logs
- Access via Render dashboard for each service
- Click on service > "Logs" tab

---

## Post-Incident Template

After resolving P1/P2 incidents, create a post-mortem:

```markdown
# Post-Incident Report: [Title]

**Date:** YYYY-MM-DD
**Severity:** P1/P2
**Duration:** X hours Y minutes
**Impact:** [Description of user impact]

## Timeline
- HH:MM - Incident detected via [source]
- HH:MM - [Action taken]
- HH:MM - [Resolution]
- HH:MM - Incident resolved

## Root Cause
[What caused the incident]

## Resolution
[What was done to fix it]

## Prevention
[What will be done to prevent recurrence]
- [ ] Action item 1
- [ ] Action item 2

## Lessons Learned
[What we learned from this incident]
```

---

## See Also

- [Monitoring Guide](monitoring.md) - Metrics and logging
- [Alerting Setup](ALERTING_SETUP.md) - Configure alerts
- [Backup and Restore](backup-restore.md) - Data recovery

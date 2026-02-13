# Performance Baseline and Tuning Guide

**Tags:** `operations`, `performance`, `monitoring`, `optimization`, `baseline`
**Last updated:** 2026-02-13

Comprehensive guide for performance expectations, monitoring, and optimization.

---

## Performance SLOs (Service Level Objectives)

### Response Time Targets

| Endpoint Category | p50 (Median) | p95 | p99 | Max Acceptable |
|-------------------|--------------|-----|-----|----------------|
| **Health Check** | < 10ms | < 50ms | < 100ms | 200ms |
| **Authentication** | < 100ms | < 300ms | < 500ms | 1s |
| **Recipe List (paginated)** | < 200ms | < 500ms | < 1s | 2s |
| **Recipe Detail** | < 150ms | < 400ms | < 800ms | 1.5s |
| **Recipe Create/Update** | < 300ms | < 800ms | < 1.5s | 3s |
| **Image Upload** | < 500ms | < 2s | < 5s | 10s |
| **OCR Processing** | < 5s | < 15s | < 30s | 60s |
| **PDF Export** | < 3s | < 10s | < 20s | 45s |
| **Search** | < 300ms | < 800ms | < 1.5s | 3s |

### Error Rate Targets

| Scenario | Max Error Rate | Measurement Window |
|----------|---------------|-------------------|
| Normal operation | < 0.5% | 5 minutes |
| High load (2x normal) | < 1% | 5 minutes |
| Peak load (5x normal) | < 2% | 5 minutes |
| Stress test (10x normal) | < 5% | 5 minutes |

### Availability Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Uptime | 99.5% | Monthly |
| Health check success | 99.9% | Daily |
| Scheduled maintenance | < 2 hours | Monthly |

---

## Throughput Baselines

### Concurrent User Capacity

| Instance Type | Concurrent Users | Requests/sec | Notes |
|---------------|------------------|--------------|-------|
| Render Starter | 10-20 | 15-30 | Development only |
| Render Standard | 50-100 | 50-100 | Small production |
| Render Pro | 200-500 | 150-300 | Medium production |
| Render Pro+ | 500-1000 | 300-600 | Large production |

### Background Job Capacity

| Worker Config | OCR Jobs/min | PDF Jobs/min | Notes |
|---------------|--------------|--------------|-------|
| 1 worker | 2-3 | 5-10 | Minimum viable |
| 2 workers | 5-6 | 10-20 | Standard production |
| 4 workers | 10-12 | 20-40 | High volume |

---

## Performance Monitoring Setup

### Sentry Configuration

**Backend** (`backend/app/__init__.py`):
```python
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    traces_sample_rate=0.1,      # 10% of transactions
    profiles_sample_rate=0.1,    # 10% profiling
    send_default_pii=False,
    environment=os.environ.get("FLASK_ENV", "production"),
)
```

**Frontend** (`frontend/src/contexts/CookieConsentContext.tsx`):
```typescript
Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  tracesSampleRate: 0.1,  // 10% of transactions
  environment: import.meta.env.MODE,
});
```

### Key Sentry Features

1. **Transaction Tracing**: Automatic capture of HTTP request durations
2. **Database Query Spans**: SQLAlchemy integration captures query times
3. **Performance Profiling**: CPU profiling for slow transactions
4. **Web Vitals**: Frontend Core Web Vitals (LCP, FID, CLS)

### Adjusting Sample Rates

| Environment | traces_sample_rate | profiles_sample_rate | Reasoning |
|-------------|-------------------|---------------------|-----------|
| Development | 1.0 | 1.0 | Full visibility for debugging |
| Staging | 0.5 | 0.5 | Catch issues before production |
| Production (low traffic) | 0.2 | 0.1 | More data, manageable volume |
| Production (high traffic) | 0.05 | 0.05 | Cost control, sufficient sampling |

---

## Key Metrics to Monitor

### Application Metrics

| Metric | Source | Alert Threshold | Action |
|--------|--------|-----------------|--------|
| Request duration p95 | Sentry | > 2s for 5 min | Investigate slow queries |
| Error rate | Sentry | > 1% for 5 min | Check error logs |
| Apdex score | Sentry | < 0.8 | Review performance trends |
| Transaction throughput | Sentry | Drops > 50% | Check for outages |

### Infrastructure Metrics

| Metric | Source | Alert Threshold | Action |
|--------|--------|-----------------|--------|
| CPU usage | Render / System | > 80% for 5 min | Scale up or optimize |
| Memory usage | Render / System | > 85% | Check for memory leaks |
| Disk usage | Render / System | > 90% | Clean up or expand |
| Database connections | PostgreSQL | > 80% of pool | Check connection leaks |

### Business Metrics

| Metric | Expected Range | Alert If |
|--------|----------------|----------|
| Recipe uploads/hour | 5-50 | < 1 for 2 hours (during business hours) |
| OCR success rate | > 90% | < 80% |
| Active users/day | Varies | Drops > 50% from baseline |

---

## Performance Testing

### Load Test Scenarios

Run these tests monthly or before major releases.

**1. Baseline Test** (establishes normal operation metrics)
```bash
locust -f scripts/load_test.py \
    --host=http://localhost:5001 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=5m \
    --headless
```

Expected results:
- Response time p95: < 500ms
- Error rate: < 0.5%
- Throughput: > 15 req/s

**2. Stress Test** (finds breaking point)
```bash
locust -f scripts/load_test.py \
    --host=http://localhost:5001 \
    --users=100 \
    --spawn-rate=10 \
    --run-time=10m \
    --headless
```

Expected results:
- Graceful degradation (not crashes)
- Error rate: < 5%
- Memory stable (no leaks)

**3. Endurance Test** (detects memory leaks)
```bash
locust -f scripts/load_test.py \
    --host=http://localhost:5001 \
    --users=20 \
    --spawn-rate=2 \
    --run-time=1h \
    --headless
```

Expected results:
- Memory usage stable over time
- No increasing response times
- Error rate remains constant

### Load Test Report

After running tests, generate reports:
```bash
python scripts/load_test_report.py
```

Reports saved to `scripts/reports/` with:
- Response time distributions
- Throughput charts
- Error analysis
- Resource utilization

---

## Performance Tuning Guide

### Quick Wins

#### 1. Database Query Optimization

**Enable query logging** (development):
```python
# In config
SQLALCHEMY_ECHO = True
```

**Add missing indexes**:
```sql
-- Check for missing indexes on common queries
CREATE INDEX idx_recipes_user_id ON recipes(user_id);
CREATE INDEX idx_recipes_cookbook_id ON recipes(cookbook_id);
CREATE INDEX idx_recipes_created_at ON recipes(created_at);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
```

**Use eager loading** to avoid N+1 queries:
```python
# Bad: N+1 queries
recipes = Recipe.query.filter_by(user_id=user_id).all()
for recipe in recipes:
    print(recipe.ingredients)  # Additional query per recipe

# Good: Single query with joins
recipes = Recipe.query.options(
    joinedload(Recipe.ingredients),
    joinedload(Recipe.images)
).filter_by(user_id=user_id).all()
```

#### 2. Response Caching

**Redis caching for expensive queries**:
```python
from flask_caching import Cache

@cache.cached(timeout=300, key_prefix='public_recipes')
def get_public_recipes():
    return Recipe.query.filter_by(is_public=True).all()
```

**HTTP caching headers**:
```python
@app.after_request
def add_cache_headers(response):
    if request.method == 'GET' and response.status_code == 200:
        response.cache_control.max_age = 60
        response.cache_control.public = True
    return response
```

#### 3. Image Optimization

**Cloudinary transformations** (already configured):
```python
# Thumbnail generation
cloudinary.uploader.upload(file,
    eager=[
        {"width": 300, "height": 300, "crop": "fill"},
        {"width": 800, "height": 600, "crop": "limit"}
    ]
)
```

**Lazy loading in frontend**:
```tsx
<img loading="lazy" src={recipe.thumbnail_url} />
```

#### 4. Connection Pooling

**PostgreSQL pool settings**:
```python
# In config
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_POOL_TIMEOUT = 20
SQLALCHEMY_POOL_RECYCLE = 1800
SQLALCHEMY_MAX_OVERFLOW = 5
```

### Advanced Optimization

#### 1. Query Analysis

**Find slow queries**:
```sql
-- PostgreSQL slow query log
ALTER DATABASE cookbook_db SET log_min_duration_statement = 100;

-- View slow queries
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Analyze query plans**:
```sql
EXPLAIN ANALYZE SELECT * FROM recipes
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 20;
```

#### 2. Background Job Optimization

**Batch processing**:
```python
# Instead of processing one at a time
for image in images:
    process_image(image)

# Process in batches
from itertools import batched
for batch in batched(images, 10):
    process_images_batch(batch)
```

**Priority queues**:
```python
# High priority for small jobs
celery_app.send_task('process_image', priority=1)

# Low priority for large exports
celery_app.send_task('export_cookbook', priority=10)
```

#### 3. Frontend Performance

**Bundle optimization** (vite.config.ts):
```typescript
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        vendor: ['react', 'react-dom', 'react-router-dom'],
        query: ['@tanstack/react-query'],
      }
    }
  }
}
```

**React Query optimization**:
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 30 * 60 * 1000, // 30 minutes
      refetchOnWindowFocus: false,
    },
  },
});
```

---

## Capacity Planning

### Resource Scaling Guidelines

| Users | Web Instances | Workers | DB Plan | Redis |
|-------|--------------|---------|---------|-------|
| < 100 | 1 Starter | 1 | Free | Free |
| 100-500 | 1 Standard | 2 | Starter | Starter |
| 500-2000 | 2 Standard | 4 | Pro 4GB | Pro |
| 2000-5000 | 2 Pro | 8 | Pro 8GB | Pro |
| 5000+ | Auto-scale | Auto-scale | Pro 16GB+ | Pro+ |

### Scaling Triggers

| Metric | Scale Up When | Scale Down When |
|--------|---------------|-----------------|
| CPU | > 70% for 10 min | < 30% for 30 min |
| Memory | > 80% for 5 min | < 40% for 30 min |
| Response time | p95 > 2s for 5 min | p95 < 500ms for 30 min |
| Queue depth | > 100 jobs for 5 min | < 10 jobs for 30 min |

---

## Performance Checklist

### Before Release

- [ ] Load test passes baseline thresholds
- [ ] No new N+1 queries introduced
- [ ] Database migrations are indexed
- [ ] Bundle size hasn't increased significantly
- [ ] No memory leaks in new features

### Monthly Review

- [ ] Review Sentry performance trends
- [ ] Analyze slow transaction reports
- [ ] Check database query statistics
- [ ] Review error rate trends
- [ ] Update capacity projections

### Quarterly

- [ ] Run full load test suite
- [ ] Review and update performance SLOs
- [ ] Database query optimization review
- [ ] Infrastructure cost analysis
- [ ] Performance benchmark comparison

---

## Troubleshooting Slow Performance

### Quick Diagnosis

```bash
# Check current system load
uptime

# Check memory usage
free -h

# Check database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory
redis-cli INFO memory | grep used_memory_human

# Check Celery queue depth
celery -A app.celery inspect active
```

### Common Issues and Fixes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Slow recipe list | Missing index on user_id | Add index |
| Slow search | Full table scan | Add full-text search index |
| High memory | Image processing leaks | Restart workers, optimize PIL usage |
| Database timeouts | Connection exhaustion | Increase pool size |
| Frontend slow | Large bundle | Code splitting |
| OCR timeouts | Anthropic rate limit | Implement retry with backoff |

---

## See Also

- [Load Testing Guide](../development/load-testing.md) - Detailed test setup
- [Monitoring Guide](monitoring.md) - Log analysis and alerts
- [Incident Response](incident-response.md) - When things go wrong
- [API Rate Limits](../api/overview.md#rate-limiting) - API throttling

---

[Back to Operations](README.md) | [Back to Documentation Home](../README.md)

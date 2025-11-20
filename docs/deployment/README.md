# Deployment Guide

**Tags:** `deployment`, `production`, `render`, `hosting`
**Last updated:** 2025-11-14

Production deployment guides for Cookbook Creator.

---

## Deployment Options

Cookbook Creator is deployed on **Render** with the following services:

- **Web Service** - Flask backend API
- **Static Site** - React frontend
- **PostgreSQL** - Database
- **Redis** - Cache and task queue

---

## Deployment Documentation

### Production Deployment
➡️ **[Production Deployment Guide](production.md)**

Complete guide to deploying to production:
- Render setup and configuration
- Environment variables
- Database setup
- SSL/TLS configuration
- Domain setup
- Monitoring

### Environment Variables
➡️ **[Environment Variables Reference](environment-variables.md)**

Complete list of configuration variables:
- Required variables
- Optional variables
- Variable descriptions
- Example values

### Troubleshooting
➡️ **[Deployment Troubleshooting](troubleshooting.md)**

Common deployment issues and solutions:
- Build failures
- Runtime errors
- Database connection issues
- Performance problems

---

## Quick Deploy Checklist

### Pre-Deployment

- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] Secrets rotated (if needed)
- [ ] Monitoring configured

### Backend Deployment

- [ ] Build succeeds
- [ ] Database migrations run
- [ ] Health check passes
- [ ] API endpoints responding
- [ ] Background jobs running

### Frontend Deployment

- [ ] Build succeeds
- [ ] Assets uploaded to CDN
- [ ] Service worker updated
- [ ] Routes working correctly
- [ ] API connection working

### Post-Deployment

- [ ] Smoke tests pass
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Verify integrations working
- [ ] Test critical user flows

---

## Deployment Process

### 1. Prepare Release

```bash
# Ensure main branch is up to date
git checkout main
git pull origin main

# Run tests
cd backend && uv run pytest
cd frontend && npm test

# Build locally to verify
cd backend && uv run python -m build
cd frontend && npm run build
```

### 2. Deploy Backend

Backend deploys automatically on push to `main` branch.

**Manual deployment:**
```bash
# Via Render CLI
render deploy -s your-backend-service-id

# Or via Render Dashboard
# 1. Go to your backend service
# 2. Click "Manual Deploy"
# 3. Select branch to deploy
```

### 3. Deploy Frontend

Frontend deploys automatically on push to `main` branch.

**Manual deployment:**
```bash
# Via Render CLI
render deploy -s your-frontend-service-id
```

### 4. Run Migrations

```bash
# SSH into Render service
render ssh your-backend-service-id

# Run migrations
uv run python scripts/cookbook_db_cli.py migrate
```

### 5. Verify Deployment

```bash
# Check backend health
curl https://your-api.com/health

# Check frontend
curl https://your-app.com

# Monitor logs
render logs -s your-backend-service-id --tail
```

---

## Rollback Procedure

If a deployment causes issues:

### 1. Immediate Rollback

```bash
# Via Render Dashboard
# 1. Go to service
# 2. Click "Deploys"
# 3. Find last working deploy
# 4. Click "Redeploy"
```

### 2. Rollback Database Migrations

```bash
# SSH into service
render ssh your-backend-service-id

# Rollback one migration
uv run python scripts/cookbook_db_cli.py downgrade -1

# Or rollback to specific version
uv run python scripts/cookbook_db_cli.py downgrade <migration_id>
```

### 3. Verify Rollback

- Check error rates return to normal
- Verify critical functionality works
- Monitor user reports

---

## Monitoring & Alerts

### Health Checks

- **Backend:** `GET /health`
- **Database:** Connection pool status
- **Redis:** Ping command

### Metrics to Monitor

- **Response times** - API latency
- **Error rates** - 4xx and 5xx responses
- **Database** - Connection pool, slow queries
- **Memory** - Heap usage, memory leaks
- **CPU** - Usage spikes

### Alerts

Configure alerts for:
- Error rate > 1%
- Response time > 2s (p95)
- Memory usage > 80%
- Database connections > 80% of pool
- Failed background jobs

---

## Security Considerations

### Secrets Management

- Store secrets in Render environment variables
- Never commit secrets to repository
- Rotate secrets regularly
- Use different secrets for each environment

### SSL/TLS

- HTTPS enforced for all traffic
- TLS 1.2+ only
- Automatic certificate renewal

### Database Security

- Enable SSL for database connections
- Use strong passwords
- Restrict database access by IP
- Regular backups

---

## See Also

- [Environment Variables](environment-variables.md)
- [Database Operations](../operations/database-cli.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Architecture Overview](../architecture/overview.md)

---

[← Back to Documentation Home](../README.md)

# Production Deployment Guide

**Tags:** `deployment`, `production`, `render`, `docker`, `devops`
**Last updated:** 2025-11-14

Complete guide for deploying Cookbook Creator to production environments.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Render Deployment (Recommended)](#render-deployment-recommended)
- [Docker Deployment](#docker-deployment)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Verification & Testing](#verification--testing)
- [Troubleshooting](#troubleshooting)
- [Monitoring & Maintenance](#monitoring--maintenance)

---

## Quick Start

### Render Deployment (Recommended)

```bash
# 1. Install Render CLI
brew install render
# Or: curl -fsSL https://raw.githubusercontent.com/render-oss/cli/refs/heads/main/bin/install.sh | sh

# 2. Login to Render
render login

# 3. Configure environment variables
cp .env.production.example .env.production
# Edit .env.production with your database URLs and API keys

# 4. Deploy
./scripts/render-deploy.sh
```

### Docker Deployment

```bash
# 1. Configure environment
cp .env.production.example .env.production
# Edit .env.production with your values

# 2. Build frontend
cd frontend && npm install && npm run build && cd ..

# 3. Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

---

## Prerequisites

### Required Software

- **Docker & Docker Compose** (for Docker deployment)
- **Git** - Version control
- **Node.js 18+** - Frontend build
- **Python 3.11+** - Backend runtime

### Required Services

- **PostgreSQL 14+** - Primary database
- **Redis 5+** - Caching and session storage
- **Render Account** (for Render deployment) or server with Docker

### Required API Keys

- **Anthropic Claude API Key** - AI-powered recipe extraction
  - Sign up at: https://console.anthropic.com
- **Cloudinary Account** - Cloud image storage (recommended)
  - Sign up at: https://cloudinary.com
- **Stripe Keys** - Payment processing (if using subscriptions)
  - Sign up at: https://stripe.com
- **Google Books API Key** - Cookbook metadata (optional)
  - Get key at: https://console.cloud.google.com

---

## Render Deployment (Recommended)

Render provides managed hosting with automatic deployments, SSL, and scaling.

### Step 1: Create Render Services

#### 1.1 Create PostgreSQL Database

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "PostgreSQL"
3. Configure:
   - **Name:** `cookbook-creator-db`
   - **Database:** `cookbook_creator`
   - **User:** `cookbook_user`
   - **Region:** Choose closest to your users
   - **Plan:** Choose based on needs (Free for testing)
4. Click "Create Database"
5. **Save the Internal and External Database URLs**

#### 1.2 Create Redis Instance

1. Click "New +" → "Redis"
2. Configure:
   - **Name:** `cookbook-creator-redis`
   - **Region:** Same as database
   - **Plan:** Choose based on needs
3. Click "Create Redis"
4. **Save the Internal and External Redis URLs**

#### 1.3 Deploy Backend Service

1. Click "New +" → "Web Service"
2. Connect your Git repository
3. Configure:
   - **Name:** `cookbook-creator-api`
   - **Region:** Same as database
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:**
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     gunicorn -w 4 -b 0.0.0.0:$PORT run:app
     ```
   - **Plan:** Choose based on needs (Starter or higher recommended)

4. Add Environment Variables (see [Environment Configuration](#environment-configuration))

5. Click "Create Web Service"

#### 1.4 Deploy Frontend Service

1. Click "New +" → "Static Site"
2. Connect your Git repository
3. Configure:
   - **Name:** `cookbook-creator-app`
   - **Branch:** `main`
   - **Root Directory:** `frontend`
   - **Build Command:**
     ```bash
     npm install && npm run build
     ```
   - **Publish Directory:** `dist`

4. Add Environment Variables:
   ```
   VITE_API_URL=https://your-backend-service.onrender.com/api
   ```

5. Click "Create Static Site"

### Step 2: Configure Environment Variables

In your **Backend Web Service**, add these environment variables:

**Flask Configuration:**
```
FLASK_ENV=production
SECRET_KEY=[Generate with: python -c "import secrets; print(secrets.token_hex(32))"]
```

**Database:**
```
DATABASE_URL=[Your Render PostgreSQL Internal Database URL]
```

**Redis:**
```
REDIS_URL=[Your Render Redis Internal URL]
```

**API Keys:**
```
ANTHROPIC_API_KEY=[Your Anthropic API key]
CLOUDINARY_CLOUD_NAME=[Your Cloudinary cloud name]
CLOUDINARY_API_KEY=[Your Cloudinary API key]
CLOUDINARY_API_SECRET=[Your Cloudinary API secret]
STRIPE_SECRET_KEY=[Your Stripe secret key]
STRIPE_WEBHOOK_SECRET=[Your Stripe webhook secret]
```

**CORS:**
```
CORS_ORIGINS=https://your-frontend.onrender.com
```

**Session Security:**
```
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_DOMAIN=.onrender.com
SESSION_COOKIE_SAMESITE=None
```

### Step 3: Initialize Database

After backend service is deployed:

1. Open Render Shell for your backend service
2. Run migrations:
   ```bash
   uv run python scripts/cookbook_db_cli.py migrate
   ```

3. Create admin user (optional):
   ```bash
   uv run python scripts/cookbook_db_cli.py create-user \
     --email admin@example.com \
     --password your-secure-password \
     --admin
   ```

### Step 4: Configure Stripe Webhooks

1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to Developers → Webhooks
3. Click "Add endpoint"
4. Endpoint URL: `https://your-backend-service.onrender.com/api/payments/webhook`
5. Select events to listen for:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
6. Copy the Webhook Signing Secret
7. Add to Render environment variables as `STRIPE_WEBHOOK_SECRET`

---

## Docker Deployment

For self-hosted or custom infrastructure deployment.

### Step 1: Prepare Environment

```bash
# Clone repository
git clone https://github.com/yourusername/cookbook-creator.git
cd cookbook-creator

# Copy environment template
cp .env.production.example .env.production

# Generate secret key
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Edit .env.production with your configuration
nano .env.production
```

### Step 2: Build Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### Step 3: Docker Compose Deployment

**Option A: Full Stack (All services)**

```bash
# Start all services (app, database, redis)
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

**Option B: With Nginx Reverse Proxy**

```bash
# Start with nginx proxy
docker-compose -f docker-compose.prod.yml --profile nginx up -d

# Check all services
docker-compose -f docker-compose.prod.yml --profile nginx ps
```

**Option C: App Only (External Database)**

```bash
# Build production image
docker build -f Dockerfile.prod -t cookbook-creator:latest .

# Run with external services
docker run -d \
  --name cookbook-creator \
  -p 8000:8000 \
  --env-file .env.production \
  cookbook-creator:latest
```

### Step 4: Initialize Database

```bash
# Wait for services to start
sleep 30

# Run database migrations
docker-compose -f docker-compose.prod.yml exec app \
  uv run python scripts/cookbook_db_cli.py migrate

# Create admin user (optional)
docker-compose -f docker-compose.prod.yml exec app \
  uv run python scripts/cookbook_db_cli.py create-user \
  --email admin@example.com \
  --password admin123 \
  --admin
```

---

## Environment Configuration

### Required Environment Variables

**Flask Configuration:**
```bash
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-very-secure-secret-key-here
```

**Database:**
```bash
DATABASE_URL=postgresql://user:password@host:5432/cookbook_creator
```

**Redis:**
```bash
REDIS_URL=redis://host:6379/0
```

**AI Services:**
```bash
ANTHROPIC_API_KEY=your-anthropic-api-key
```

**Cloudinary (Image Storage):**
```bash
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
USE_CLOUDINARY=true
```

**Stripe (Payment Processing):**
```bash
STRIPE_SECRET_KEY=sk_live_your-stripe-key
STRIPE_PUBLISHABLE_KEY=pk_live_your-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
STRIPE_PREMIUM_PRICE=299  # Price in cents ($2.99)
FREE_TIER_UPLOAD_LIMIT=10
```

**Security & Sessions:**
```bash
SESSION_COOKIE_SECURE=true  # HTTPS only
SESSION_COOKIE_DOMAIN=yourdomain.com
SESSION_COOKIE_SAMESITE=Lax  # Or 'None' for cross-origin
PERMANENT_SESSION_LIFETIME=3600  # 1 hour
```

**CORS:**
```bash
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**File Upload:**
```bash
MAX_CONTENT_LENGTH=16777216  # 16MB
MAX_UPLOAD_SIZE=8  # 8MB
JPEG_QUALITY=85
```

**Logging:**
```bash
LOG_LEVEL=INFO
LOG_FILE=logs/cookbook-creator.log
```

### Generating Secure Keys

**Secret Key:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Database Password:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Database Setup

### Running Migrations

**Render:**
```bash
# Via Render Shell
uv run python scripts/cookbook_db_cli.py migrate
```

**Docker:**
```bash
docker-compose -f docker-compose.prod.yml exec app \
  uv run python scripts/cookbook_db_cli.py migrate
```

### Creating Admin User

```bash
uv run python scripts/cookbook_db_cli.py create-user \
  --email admin@example.com \
  --password your-secure-password \
  --admin
```

### Database Backups

**PostgreSQL Backup:**
```bash
# Render (via Render Dashboard)
# Go to Database → Settings → Backups

# Docker
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U cookbook_user cookbook_creator > backup.sql
```

**Restore:**
```bash
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U cookbook_user cookbook_creator < backup.sql
```

---

## Verification & Testing

### Health Checks

```bash
# Basic health check
curl https://your-api.com/health

# Expected response:
# {"status": "healthy"}

# Detailed health check
curl https://your-api.com/api/health

# Expected response:
# {
#   "status": "healthy",
#   "checks": {
#     "database": true,
#     "redis": true
#   }
# }
```

### Test API Endpoints

```bash
# Test user registration
curl -X POST https://your-api.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'

# Test user login
curl -X POST https://your-api.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}' \
  -c cookies.txt

# Test authenticated endpoint
curl -X GET https://your-api.com/api/recipes \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

### Frontend Access

```bash
# Open in browser
open https://your-frontend.com

# Test with curl
curl -I https://your-frontend.com
```

---

## Troubleshooting

### Backend Issues

**Service won't start:**
- Check logs: `render logs -s your-service-id --tail`
- Verify environment variables are set
- Ensure database URL is correct
- Check Redis connection

**Database connection errors:**
- Use Internal Database URL (not External) on Render
- Format: `postgresql://user:password@internal-host/database`
- Verify database is running and accessible

**Redis connection errors:**
- Use Internal Redis URL on Render
- Format: `redis://internal-host:6379/0`
- Verify Redis instance is running

**Session/Authentication issues:**
- Check `SESSION_COOKIE_SECURE=true` (HTTPS required)
- Verify `SESSION_COOKIE_DOMAIN` matches your domain
- For cross-origin: `SESSION_COOKIE_SAMESITE=None; Secure`

### Frontend Issues

**API connection errors:**
- Verify `VITE_API_URL` points to correct backend URL
- Check CORS configuration in backend
- Ensure backend is accessible from frontend

**Static files not loading:**
- Check build completed successfully
- Verify `dist/` directory contains built files
- Check nginx/server configuration

**Blank page after deployment:**
- Check browser console for errors
- Verify API is responding
- Check routing configuration

### Database Connection Format

**Render Internal URL (Use this):**
```
postgresql://user:password@internal-host.oregon-postgres.render.com/database
```

**External URL (Don't use for apps):**
```
postgresql://user:password@external-host.oregon-postgres.render.com/database
```

---

## Monitoring & Maintenance

### Logs

**Render:**
```bash
# Tail logs
render logs -s your-service-id --tail

# View recent logs
render logs -s your-service-id
```

**Docker:**
```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs

# Follow specific service
docker-compose -f docker-compose.prod.yml logs -f app
```

### Performance Monitoring

Monitor these metrics:

- **Response Times:** API latency (target: <200ms p95)
- **Error Rates:** 4xx and 5xx responses (target: <1%)
- **Database:** Connection pool usage, slow queries
- **Memory:** Heap usage, memory leaks
- **CPU:** Usage spikes, bottlenecks

### Regular Maintenance

**Daily:**
- Review error logs
- Check service health
- Monitor disk space

**Weekly:**
- Database vacuum (PostgreSQL)
- Clear old sessions
- Review slow queries

**Monthly:**
- Update dependencies
- Rotate secrets
- Review security patches
- Test backup restoration

### Scaling

**Render:**
- Increase instance type for more resources
- Enable autoscaling in service settings
- Consider upgrading database plan

**Docker:**
- Scale services: `docker-compose up --scale app=3`
- Add load balancer (nginx)
- Optimize connection pools

---

## Production Checklist

Before going live:

- [ ] All environment variables configured
- [ ] Database migrations run successfully
- [ ] SSL/HTTPS enabled and working
- [ ] CORS configured correctly
- [ ] Session security enabled
- [ ] Rate limiting configured
- [ ] Error tracking set up (e.g., Sentry)
- [ ] Database backups automated
- [ ] Monitoring and alerts configured
- [ ] Stripe webhooks configured (if using payments)
- [ ] Admin user created
- [ ] Health checks passing
- [ ] Performance tested
- [ ] Security headers enabled
- [ ] Secrets rotated from defaults

---

## See Also

- [Environment Variables Reference](environment-variables.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Database Operations](../operations/database-cli.md)
- [Architecture Overview](../architecture/overview.md)

---

[← Back to Deployment Guide](README.md) | [Back to Documentation Home](../README.md)

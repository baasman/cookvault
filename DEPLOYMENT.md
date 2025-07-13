# Cookbook Creator - Production Deployment Guide

This guide covers deploying the Cookbook Creator application to production environments.

## Quick Start

1. **Copy environment variables**:
   ```bash
   cp .env.production.example .env.production
   # Edit .env.production with your values
   ```

2. **Deploy with Docker Compose**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Prerequisites

### Required Software
- Docker & Docker Compose
- Git

### Required Services
- PostgreSQL database
- Redis server
- (Optional) Nginx reverse proxy

### Required API Keys
- **Anthropic Claude API Key** - For recipe parsing
- **Google Books API Key** - For cookbook metadata

## Environment Configuration

### Required Environment Variables

Copy `.env.production.example` to `.env.production` and configure:

```bash
# CRITICAL: Generate a secure secret key
SECRET_KEY=your-very-secure-secret-key-here

# Database credentials
POSTGRES_PASSWORD=your-secure-postgres-password

# API keys
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_BOOKS_API_KEY=your-google-books-api-key

# Domain configuration
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Generating a Secure Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

**Full stack with all services**:
```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

**With Nginx reverse proxy**:
```bash
docker-compose -f docker-compose.prod.yml --profile nginx up -d
```

### Option 2: Individual Services

**Build and run application only**:
```bash
# Build image
docker build -f Dockerfile.prod -t cookbook-creator .

# Run with external database
docker run -d \
  --name cookbook-creator \
  -p 8000:8000 \
  --env-file .env.production \
  cookbook-creator
```

### Option 3: Cloud Platforms

#### Heroku
```bash
# Create Heroku app
heroku create your-app-name

# Add buildpacks
heroku buildpacks:add --index 1 heroku-community/apt
heroku buildpacks:add --index 2 heroku/nodejs
heroku buildpacks:add --index 3 heroku/python

# Create Aptfile for tesseract
echo "tesseract-ocr\ntesseract-ocr-eng" > Aptfile

# Set environment variables
heroku config:set SECRET_KEY=your-secret-key
heroku config:set ANTHROPIC_API_KEY=your-api-key
heroku config:set GOOGLE_BOOKS_API_KEY=your-api-key

# Add database
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini

# Deploy
git push heroku main
```

#### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and initialize
railway login
railway init

# Deploy
railway up
```

#### DigitalOcean App Platform
1. Connect your Git repository
2. Set environment variables in the dashboard
3. Configure build settings:
   - Build command: `npm run build` (frontend)
   - Run command: `./start.sh` (backend)

## Database Setup

### Initial Migration
```bash
# Run database migrations
docker-compose -f docker-compose.prod.yml exec app python -m flask db upgrade

# Or if running manually
export FLASK_ENV=production
python -m flask db upgrade
```

### Seed Data (Optional)
```bash
# Add sample data
docker-compose -f docker-compose.prod.yml exec app python -m flask seed-data
```

## Monitoring & Health Checks

### Health Endpoints
- **Basic**: `GET /health`
- **Detailed**: `GET /api/health`

### Monitoring Services

Both endpoints return JSON with health status:
```json
{
  "status": "healthy",
  "checks": {
    "database": true,
    "redis": true,
    "uploads": true
  },
  "service": "cookbook-creator-backend",
  "version": "1.0.0"
}
```

## Security Considerations

### HTTPS Configuration
- Set `SESSION_COOKIE_SECURE=True` in production
- Configure SSL certificates
- Use Nginx or cloud load balancer for SSL termination

### Environment Security
- Never commit `.env.production` to version control
- Use secrets management (AWS Secrets Manager, etc.)
- Rotate API keys regularly
- Use strong database passwords

### Application Security
- Rate limiting is enabled (60 requests/hour by default)
- Security headers are configured via Talisman
- CORS is restricted to configured origins
- File uploads are validated and size-limited

## Scaling

### Horizontal Scaling
```bash
# Scale application containers
docker-compose -f docker-compose.prod.yml up -d --scale app=3
```

### Performance Tuning
- Adjust `GUNICORN_WORKERS` based on CPU cores
- Configure PostgreSQL connection pooling
- Tune Redis memory limits
- Use CDN for static assets

## Backup & Recovery

### Database Backup
```bash
# Create backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U cookbook_user cookbook_db > backup.sql

# Restore backup
docker-compose -f docker-compose.prod.yml exec -T db psql -U cookbook_user cookbook_db < backup.sql
```

### File Uploads Backup
```bash
# Backup uploads
docker cp $(docker-compose -f docker-compose.prod.yml ps -q app):/app/uploads ./uploads-backup
```

## Troubleshooting

### Common Issues

**1. OCR Not Working**
```bash
# Check tesseract installation
docker-compose -f docker-compose.prod.yml exec app tesseract --version
```

**2. Database Connection Issues**
```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec db pg_isready -U cookbook_user
```

**3. Redis Connection Issues**
```bash
# Check Redis status
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

### Logs
```bash
# Application logs
docker-compose -f docker-compose.prod.yml logs -f app

# Database logs
docker-compose -f docker-compose.prod.yml logs -f db

# All services
docker-compose -f docker-compose.prod.yml logs -f
```

## Performance Optimization

### Frontend Optimization
- Assets are automatically minified and compressed
- Code splitting reduces initial bundle size
- CDN integration for static assets (manual setup)

### Backend Optimization
- Gunicorn with multiple workers
- Database connection pooling
- Redis caching for OCR results
- Rate limiting to prevent abuse

### Infrastructure Optimization
- Use Redis for session storage in multi-instance deployments
- Configure PostgreSQL with appropriate resources
- Set up monitoring with Prometheus/Grafana
- Use load balancer for high availability

## Support

For deployment issues:
1. Check the logs first
2. Verify environment variables
3. Test health endpoints
4. Consult this documentation
5. Open an issue on GitHub
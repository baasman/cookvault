# 🚀 CookVault - Quick Deployment Guide

This guide provides step-by-step commands for deploying the CookVault application to production.

## 📋 Prerequisites Checklist

- [ ] Docker and Docker Compose installed
- [ ] Git repository cloned
- [ ] Anthropic Claude API key
- [ ] Google Books API key (optional)
- [ ] Domain name (for production)

## 🔧 Pre-Deployment Setup

### 1. Environment Configuration

```bash
# Copy the environment template
cp .env.production.example .env.production

# Generate a secure secret key
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Edit the environment file
nano .env.production
```

**Required variables in `.env.production`:**
```bash
SECRET_KEY=your-generated-secret-key-here
POSTGRES_PASSWORD=your-secure-database-password
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_BOOKS_API_KEY=your-google-books-api-key
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 2. Build Frontend Assets

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Verify build was created
ls -la dist/

# Return to root directory
cd ..
```

## 🐳 Docker Deployment

### Option 1: Full Stack (Recommended)

```bash
# Start all services (app, database, redis)
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Test the application
curl http://localhost:8000/health
```

### Option 2: With Nginx Reverse Proxy

```bash
# Start with nginx proxy
docker-compose -f docker-compose.prod.yml --profile nginx up -d

# Check all services including nginx
docker-compose -f docker-compose.prod.yml --profile nginx ps
```

### Option 3: Custom Build

```bash
# Build the production image
docker build -f Dockerfile.prod -t cookvault:latest .

# Run with external services
docker run -d \
  --name cookvault \
  -p 8000:8000 \
  --env-file .env.production \
  cookvault:latest
```

## 🗄️ Database Setup

### Initial Setup

```bash
# Wait for services to start (30 seconds)
sleep 30

# Run database migrations
docker-compose -f docker-compose.prod.yml exec app python -m flask db upgrade

# Create admin user (optional)
docker-compose -f docker-compose.prod.yml exec app python -c "
from app import create_app, db
from app.models.user import User
app = create_app('production')
with app.app_context():
    admin = User(username='admin', email='admin@example.com')
    admin.set_password('admin123')
    admin.role = 'admin'
    db.session.add(admin)
    db.session.commit()
    print('Admin user created')
"
```

### Seed Data (Optional)

```bash
# Add sample recipes and cookbooks
docker-compose -f docker-compose.prod.yml exec app python -m flask seed-data
```

## 🔍 Verification Steps

### 1. Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/api/health | jq

# Expected response:
# {
#   "status": "healthy",
#   "checks": {
#     "database": true,
#     "redis": true,
#     "uploads": true
#   }
# }
```

### 2. Test API Endpoints

```bash
# Test user registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'

# Test user login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}' \
  -c cookies.txt

# Test authenticated endpoint
curl -X GET http://localhost:8000/api/recipes \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

### 3. Frontend Access

```bash
# Open in browser
open http://localhost:8000

# Or test with curl
curl -I http://localhost:8000
```

## ☁️ Cloud Platform Deployment

### Heroku

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
heroku config:set ANTHROPIC_API_KEY=your-api-key
heroku config:set GOOGLE_BOOKS_API_KEY=your-api-key

# Add database and redis
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini

# Add buildpacks for OCR
heroku buildpacks:add --index 1 heroku-community/apt
heroku buildpacks:add --index 2 heroku/nodejs
heroku buildpacks:add --index 3 heroku/python

# Create Aptfile for tesseract
echo -e "tesseract-ocr\ntesseract-ocr-eng" > Aptfile

# Create Procfile
echo "web: cd backend && ./start.sh" > Procfile

# Deploy
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# Run migrations
heroku run python -m flask db upgrade

# Open app
heroku open
```

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and initialize
railway login
railway init

# Set environment variables
railway variables set SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
railway variables set ANTHROPIC_API_KEY=your-api-key
railway variables set GOOGLE_BOOKS_API_KEY=your-api-key

# Add database
railway add postgresql
railway add redis

# Deploy
railway up
```

### DigitalOcean App Platform

```bash
# Create app.yaml
cat > app.yaml << EOF
name: cookvault
services:
- name: web
  source_dir: /
  github:
    repo: your-username/cookvault
    branch: main
  run_command: cd backend && ./start.sh
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  env:
  - key: SECRET_KEY
    value: "your-secret-key"
  - key: ANTHROPIC_API_KEY
    value: "your-api-key"
  - key: GOOGLE_BOOKS_API_KEY
    value: "your-api-key"
databases:
- name: db
  engine: PG
  version: "13"
EOF

# Deploy using doctl CLI
doctl apps create app.yaml
```

### AWS ECS (with Fargate)

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -f Dockerfile.prod -t cookvault .
docker tag cookvault:latest your-account.dkr.ecr.us-east-1.amazonaws.com/cookvault:latest

# Push to ECR
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/cookvault:latest

# Create ECS task definition and service (use AWS Console or CLI)
```

## 🔧 Management Commands

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f app

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 app
```

### Database Operations

```bash
# Database backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U cookbook_user cookbook_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Database restore
docker-compose -f docker-compose.prod.yml exec -T db psql -U cookbook_user cookbook_db < backup_file.sql

# Database shell
docker-compose -f docker-compose.prod.yml exec db psql -U cookbook_user cookbook_db
```

### Application Management

```bash
# Restart application
docker-compose -f docker-compose.prod.yml restart app

# Scale application
docker-compose -f docker-compose.prod.yml up -d --scale app=3

# Update application
git pull
docker-compose -f docker-compose.prod.yml build app
docker-compose -f docker-compose.prod.yml up -d app

# Shell access
docker-compose -f docker-compose.prod.yml exec app bash
```

### File Management

```bash
# Backup uploads
docker cp $(docker-compose -f docker-compose.prod.yml ps -q app):/app/uploads ./uploads-backup

# Restore uploads
docker cp ./uploads-backup $(docker-compose -f docker-compose.prod.yml ps -q app):/app/uploads

# Clear uploads
docker-compose -f docker-compose.prod.yml exec app rm -rf /app/uploads/*
```

## 🚨 Troubleshooting

### Common Issues

**1. Services won't start**
```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check logs for errors
docker-compose -f docker-compose.prod.yml logs

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

**2. Database connection failed**
```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec db pg_isready -U cookbook_user

# Check database logs
docker-compose -f docker-compose.prod.yml logs db

# Reset database
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

**3. OCR not working**
```bash
# Check tesseract installation
docker-compose -f docker-compose.prod.yml exec app tesseract --version

# Test OCR
docker-compose -f docker-compose.prod.yml exec app python -c "
import pytesseract
from PIL import Image
print('OCR is working')
"
```

**4. Frontend not loading**
```bash
# Check if frontend was built
docker-compose -f docker-compose.prod.yml exec app ls -la /app/frontend/dist/

# Rebuild frontend
cd frontend && npm run build && cd ..
docker-compose -f docker-compose.prod.yml build app
docker-compose -f docker-compose.prod.yml up -d app
```

### Performance Monitoring

```bash
# Check resource usage
docker stats

# Check disk usage
docker system df

# Check container processes
docker-compose -f docker-compose.prod.yml top
```

## 🔄 Updates and Maintenance

### Application Updates

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 3. Run migrations (if needed)
docker-compose -f docker-compose.prod.yml exec app python -m flask db upgrade

# 4. Verify deployment
curl http://localhost:8000/health
```

### Security Updates

```bash
# Update base images
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Update dependencies
docker-compose -f docker-compose.prod.yml exec app pip install --upgrade -r requirements.txt
```

## 📊 Monitoring

### Health Monitoring

```bash
# Set up health check monitoring
while true; do
  if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "$(date): App is healthy ✅"
  else
    echo "$(date): App is unhealthy ❌"
    # Send alert (email, slack, etc.)
  fi
  sleep 60
done
```

### Log Monitoring

```bash
# Monitor errors in logs
docker-compose -f docker-compose.prod.yml logs -f app | grep -i error

# Monitor access logs
docker-compose -f docker-compose.prod.yml logs -f app | grep -E "(GET|POST|PUT|DELETE)"
```

## 🔐 Security Checklist

- [ ] Environment variables secured (no secrets in code)
- [ ] Database password is strong
- [ ] CORS origins configured for production domain
- [ ] HTTPS enabled (SSL certificates)
- [ ] Rate limiting configured
- [ ] Security headers enabled
- [ ] Regular backups scheduled
- [ ] Monitoring and alerting set up
- [ ] API keys rotated regularly

## 📞 Support

If you encounter issues:

1. **Check logs**: `docker-compose -f docker-compose.prod.yml logs -f`
2. **Verify environment**: Ensure all required variables are set
3. **Test health endpoints**: `curl http://localhost:8000/health`
4. **Check resource usage**: `docker stats`
5. **Review this guide**: Many issues are covered in troubleshooting

---

**🎉 Congratulations! Your CookVault app is now production-ready!**
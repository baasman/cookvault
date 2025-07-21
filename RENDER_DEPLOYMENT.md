# CookVault - Render Deployment Guide

Quick deployment guide for deploying CookVault to Render.

## Prerequisites

- Render account with "CookVault" project
- Existing PostgreSQL and Redis services in your CookVault project
- Git repository connected to Render
- Render CLI access to your CookVault project

## One-Command Deployment

```bash
# Install Render CLI (if not already installed)
brew install render
# Or: curl -fsSL https://raw.githubusercontent.com/render-oss/cli/refs/heads/main/bin/install.sh | sh

# Login to Render
render login

# Deploy both services
./render-deploy.sh
```

## Manual Deployment Steps

### 1. Environment Variables

Copy and configure environment variables:
```bash
cp .env.production.example .env.production
```

Edit `.env.production` with your values:
- `DATABASE_URL`: Your Render PostgreSQL connection string
- `REDIS_URL`: Your Render Redis connection string  
- `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `GOOGLE_BOOKS_API_KEY`: Your Google Books API key (optional)
- `CORS_ORIGINS`: Your frontend URL (will be set after deployment)

### 2. Deploy via Blueprint

```bash
render blueprint launch render.yaml
```

**Important**: The blueprint will automatically deploy to your CookVault project. If you get permission errors, ensure:
- You have access to the CookVault project
- You're logged in with the correct Render account
- The project name is exactly "CookVault"

**Alternative**: If blueprint deployment fails, use manual deployment:
```bash
./render-deploy.sh --manual
```

### 3. Set Environment Variables in Render Dashboard

After deployment, go to your backend service in Render dashboard and set these as **secrets**:
- SECRET_KEY
- DATABASE_URL  
- REDIS_URL
- ANTHROPIC_API_KEY
- GOOGLE_BOOKS_API_KEY
- CORS_ORIGINS

### 4. Update CORS Origins

Once your frontend is deployed, update the `CORS_ORIGINS` variable in your backend service to include your frontend URL:
```
CORS_ORIGINS=https://your-frontend-url.onrender.com
```

## Service Configuration

The deployment creates two services:

**Backend (cookvault-backend)**
- Type: Web Service
- Runtime: Docker
- Health Check: `/api/health`
- Port: 8000

**Frontend (cookvault-frontend)**  
- Type: Static Site
- Build: `cd frontend && npm ci && npm run build`
- Publish: `./frontend/dist`

## Monitoring

```bash
# View logs
render logs cookvault-backend
render logs cookvault-frontend

# Check status
render services list

# Restart services
render restart cookvault-backend
render restart cookvault-frontend
```

## Testing Deployment

1. **Backend Health Check**:
   ```bash
   curl https://your-backend-url.onrender.com/api/health
   ```

2. **Frontend**: Visit your frontend URL in browser

3. **End-to-End**: Try uploading and processing a recipe

## Troubleshooting

- **Build failing**: Check logs with `render logs [service-name] --build`
- **Health check failing**: Verify environment variables in dashboard
- **API calls failing**: Check CORS_ORIGINS configuration
- **Database errors**: Verify DATABASE_URL format and connectivity

See `DEPLOYMENT.md` for detailed troubleshooting guide.

## File Structure

```
├── render.yaml                 # Render blueprint configuration
├── render-deploy.sh            # Deployment script
├── backend/
│   ├── Dockerfile.render       # Backend Docker configuration
│   └── start.sh                # Backend startup script
├── frontend/
│   ├── nginx.conf              # Frontend nginx configuration  
│   └── package.json            # Frontend dependencies
└── .env.production.example     # Environment variables template
```
# CookVault - Manual Dashboard Deployment

Since your Render CLI doesn't support blueprint deployment, follow these step-by-step instructions to deploy via the Render dashboard.

## 🎯 Dashboard Deployment Steps

### 1. Access Your CookVault Project
1. Go to https://dashboard.render.com
2. **Select your "CookVault" project** from the project dropdown (top left)
3. You should see your existing PostgreSQL and Redis services

### 2. Deploy Backend Service

1. **Click "New +" → "Web Service"**
2. **Connect Repository**:
   - Select "Build and deploy from a Git repository"
   - Connect your GitHub repository containing this code
   - Grant necessary permissions

3. **Configure Backend Service**:
   - **Name**: `cookvault-backend`
   - **Region**: Oregon (US West)
   - **Branch**: `main`
   - **Runtime**: Docker
   - **Dockerfile Path**: `backend/Dockerfile.render`

4. **Advanced Settings**:
   - **Health Check Path**: `/api/health`
   - **Plan**: Starter (or higher based on your needs)

5. **Environment Variables** (Add as secrets):
   ```
   SECRET_KEY=your-generated-secret-key
   DATABASE_URL=your-postgres-connection-string
   REDIS_URL=your-redis-connection-string
   ANTHROPIC_API_KEY=your-anthropic-api-key
   GOOGLE_BOOKS_API_KEY=your-google-books-api-key
   CORS_ORIGINS=https://placeholder.onrender.com
   FLASK_ENV=production
   PORT=8000
   GUNICORN_WORKERS=2
   LOG_LEVEL=info
   ```

6. **Click "Create Web Service"**

### 3. Deploy Frontend Service

1. **Click "New +" → "Static Site"**
2. **Connect Repository**:
   - Use the same repository as backend
   - Select the same branch (`main`)

3. **Configure Frontend Service**:
   - **Name**: `cookvault-frontend`
   - **Build Command**: `cd frontend && npm ci && npm run build`
   - **Publish Directory**: `frontend/dist`

4. **Environment Variables**:
   ```
   VITE_API_URL=https://cookvault-backend-[your-hash].onrender.com
   ```
   (You'll get the exact URL after backend deploys)

5. **Click "Create Static Site"**

### 4. Get Your Database Connection Strings

From your existing services in the CookVault project:

1. **PostgreSQL**:
   - Go to your PostgreSQL service
   - Copy the **External Database URL** or **Internal Database URL**
   - Use this for `DATABASE_URL` in backend service

2. **Redis**:
   - Go to your Redis service
   - Copy the **Redis URL**
   - Use this for `REDIS_URL` in backend service

### 5. Update Environment Variables

After both services are deployed:

1. **Update Backend CORS_ORIGINS**:
   - Go to backend service → Environment tab
   - Update `CORS_ORIGINS` with your actual frontend URL:
     ```
     CORS_ORIGINS=https://cookvault-frontend-[your-hash].onrender.com
     ```

2. **Update Frontend API URL**:
   - Go to frontend service → Environment tab
   - Update `VITE_API_URL` with your actual backend URL:
     ```
     VITE_API_URL=https://cookvault-backend-[your-hash].onrender.com
     ```

### 6. Test Your Deployment

1. **Backend Health Check**:
   ```
   https://cookvault-backend-[your-hash].onrender.com/api/health
   ```
   Should return: `{"status": "healthy", ...}`

2. **Frontend**:
   ```
   https://cookvault-frontend-[your-hash].onrender.com
   ```
   Should load the CookVault application

3. **End-to-End Test**:
   - Try logging in
   - Upload a test recipe
   - Verify everything works

## 🔧 Troubleshooting

### Backend Issues
- **Build failing**: Check build logs in Render dashboard
- **Health check failing**: Verify environment variables are set correctly
- **Database connection**: Ensure `DATABASE_URL` format is correct

### Frontend Issues
- **Build failing**: Ensure `package.json` and dependencies are correct
- **API calls failing**: Check `VITE_API_URL` and `CORS_ORIGINS` configuration
- **404 errors**: Verify `Publish Directory` is set to `frontend/dist`

### Database Connection Format
```
# PostgreSQL
DATABASE_URL=postgresql://user:password@host:port/database

# Redis
REDIS_URL=redis://user:password@host:port
```

## 📱 Monitoring

- **Logs**: Click on each service to view real-time logs
- **Metrics**: Monitor CPU, memory, and request metrics
- **Alerts**: Set up notifications for service health

This manual process will create the exact same setup as the automated blueprint deployment!
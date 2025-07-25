# 🔐 HTTPS Local Testing Setup

This setup allows you to test your application with full HTTPS, secure cookies, and cross-origin requests locally - exactly like your production environment.

## 🚀 Quick Start

```bash
# Run the setup script
./scripts/setup-https-testing.sh

# Or manually:
docker compose -f docker-compose.https.yml up --build
```

## 📋 Access Points

- **Frontend**: https://localhost:3443
- **Backend**: https://localhost:8443
- **API Debug**: https://localhost:8443/api/auth/debug

## 🔧 What This Tests

✅ **Secure Cookies** (`SESSION_COOKIE_SECURE=true`)
✅ **Cross-Origin Requests** (`SameSite=None`)
✅ **HTTPS Enforcement**
✅ **Production-like Environment**
✅ **Session Persistence**
✅ **Talisman Security Headers**

## 🛠️ Configuration

### Environment Variables (.env.https):
```bash
SESSION_COOKIE_SECURE=true          # Secure cookies only
SESSION_COOKIE_SAMESITE=None        # Cross-origin support
CORS_ORIGINS=https://localhost:3443 # Frontend URL
VITE_API_URL=https://localhost:8443/api # Backend API
```

### Key Features:
- **Auto-generated SSL certificates** for localhost
- **Nginx with HTTPS** for frontend
- **Gunicorn with SSL** for backend
- **Production-like security headers**

## 🔍 Testing Session Persistence

1. **Register/Login**: https://localhost:3443
2. **Check cookies** in browser dev tools
3. **Test protected endpoints**: Profile, recipes, etc.
4. **Verify in logs**: No "session token not found" errors

## 🚨 Certificate Warnings

You'll see browser security warnings for self-signed certificates:
- Click **"Advanced"**
- Then **"Proceed to localhost (unsafe)"**
- This is normal for local testing

## 📊 Debugging

```bash
# View all logs
docker-compose -f docker-compose.https.yml logs -f

# View specific service
docker-compose -f docker-compose.https.yml logs -f backend
docker-compose -f docker-compose.https.yml logs -f frontend

# Check certificates
ls -la certs/
```

## 🛑 Cleanup

```bash
# Stop services
docker-compose -f docker-compose.https.yml down

# Remove certificates
rm -rf certs/

# Remove containers and images
docker-compose -f docker-compose.https.yml down --rmi all -v
```

## 🎯 Expected Results

If HTTPS session configuration is working correctly:

1. **Browser dev tools** show secure cookies with `SameSite=None`
2. **No CORS errors** in browser console
3. **Session persists** across page refreshes and API calls
4. **Protected endpoints** work without 401 errors
5. **Backend logs** show successful session restoration

This environment exactly mirrors your Render production setup!
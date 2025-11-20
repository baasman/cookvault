# Local HTTPS Development Setup

**Tags:** `development`, `https`, `ssl`, `testing`, `ngrok`, `docker`
**Last updated:** 2025-11-14

Comprehensive guide for setting up HTTPS in your local development environment. Choose between self-signed certificates for local testing or Ngrok for external access and webhooks.

---

## Overview

Testing your application with HTTPS locally is crucial for:
- **Secure cookies** - Production-like session handling
- **Cross-origin requests** - Testing CORS with `SameSite=None`
- **External services** - Webhooks, OAuth callbacks, payment providers
- **Third-party integrations** - Services requiring HTTPS endpoints
- **Production parity** - Match your production security settings

### Choose Your Approach

| Approach | Use When | Pros | Cons |
|----------|----------|------|------|
| **Self-Signed Certificates** | Local testing, development | Free, offline, fast setup | Certificate warnings, local only |
| **Ngrok** | External access, webhooks, demos | Real HTTPS, external access, no warnings | Requires account, URLs change |

---

## Option 1: Self-Signed Certificates (Recommended for Development)

Use this approach for local development and testing production-like HTTPS behavior without external access needs.

### Quick Start

```bash
# Run the setup script
./scripts/setup-https-testing.sh

# Or manually:
docker compose -f docker-compose.https.yml up --build
```

### Access Points

- **Frontend**: https://localhost:3443
- **Backend**: https://localhost:8443
- **API Debug**: https://localhost:8443/api/auth/debug

### What This Tests

✅ **Secure Cookies** (`SESSION_COOKIE_SECURE=true`)
✅ **Cross-Origin Requests** (`SameSite=None`)
✅ **HTTPS Enforcement**
✅ **Production-like Environment**
✅ **Session Persistence**
✅ **Talisman Security Headers**

### Configuration

#### Environment Variables (`.env.https`):

```bash
SESSION_COOKIE_SECURE=true          # Secure cookies only
SESSION_COOKIE_SAMESITE=None        # Cross-origin support
CORS_ORIGINS=https://localhost:3443 # Frontend URL
VITE_API_URL=https://localhost:8443/api # Backend API
```

#### Key Features:

- **Auto-generated SSL certificates** for localhost
- **Nginx with HTTPS** for frontend
- **Gunicorn with SSL** for backend
- **Production-like security headers**

### Testing Session Persistence

1. **Register/Login**: Visit https://localhost:3443
2. **Check cookies** in browser dev tools (Application → Cookies)
3. **Test protected endpoints**: Navigate to profile, recipes, etc.
4. **Verify in logs**: No "session token not found" errors

```bash
# View all logs
docker-compose -f docker-compose.https.yml logs -f

# View specific service
docker-compose -f docker-compose.https.yml logs -f backend
docker-compose -f docker-compose.https.yml logs -f frontend
```

### Certificate Warnings

You'll see browser security warnings for self-signed certificates:

1. Click **"Advanced"** or **"Show Details"**
2. Then **"Proceed to localhost (unsafe)"** or **"Accept Risk"**
3. This is **normal for local testing** with self-signed certificates

> **Note:** Each browser needs this step only once per session.

### Debugging

```bash
# Check if services are running
docker-compose -f docker-compose.https.yml ps

# Check certificates were generated
ls -la certs/
# Expected: server.crt, server.key

# Test backend HTTPS directly
curl -k https://localhost:8443/api/health

# Check nginx configuration
docker-compose -f docker-compose.https.yml exec frontend cat /etc/nginx/nginx.conf
```

### Cleanup

```bash
# Stop services
docker-compose -f docker-compose.https.yml down

# Remove certificates
rm -rf certs/

# Remove containers, volumes, and images
docker-compose -f docker-compose.https.yml down --rmi all -v
```

### Expected Results

If HTTPS session configuration is working correctly:

1. ✅ **Browser dev tools** show secure cookies with `SameSite=None; Secure`
2. ✅ **No CORS errors** in browser console
3. ✅ **Session persists** across page refreshes and API calls
4. ✅ **Protected endpoints** work without 401 errors
5. ✅ **Backend logs** show successful session restoration

This environment exactly mirrors your Render production setup!

---

## Option 2: Ngrok (For External Access & Webhooks)

Use this approach when you need:
- External access to share with others
- Webhook testing (Stripe, Lulu, etc.)
- OAuth callback testing
- Real HTTPS certificates (no browser warnings)

### Prerequisites

1. **Install ngrok**: https://ngrok.com/download
2. **Create ngrok account**: https://dashboard.ngrok.com/signup
3. **Get auth token**: https://dashboard.ngrok.com/get-started/your-authtoken

### Setup

#### 1. Configure Ngrok Auth Token

```bash
# Copy the ngrok environment template
cp .env.ngrok .env.ngrok.local

# Edit .env.ngrok.local and add your token
NGROK_AUTHTOKEN=your_token_here
```

#### 2. Start the Services

```bash
docker-compose -f docker-compose.ngrok.yml --env-file .env.ngrok.local up --build
```

#### 3. Get Ngrok URLs

Ngrok provides web interfaces to view your public URLs:

- **Backend ngrok interface**: http://localhost:4040
- **Frontend ngrok interface**: http://localhost:4041

Copy the HTTPS URLs displayed (e.g., `https://abc123.ngrok.io`)

#### 4. Update Environment with Ngrok URLs

After getting your ngrok URLs, update the configuration:

```bash
# Edit .env.ngrok.local
NGROK_BACKEND_URL=https://your-backend-url.ngrok.io
NGROK_FRONTEND_URL=https://your-frontend-url.ngrok.io
VITE_API_URL=https://your-backend-url.ngrok.io/api

# Restart frontend to pick up the new API URL
docker-compose -f docker-compose.ngrok.yml restart frontend
```

### Usage

- **Frontend**: Access via ngrok frontend URL (e.g., `https://abc123.ngrok.io`)
- **Backend**: Access via ngrok backend URL (e.g., `https://def456.ngrok.io`)
- **API Endpoint**: `https://def456.ngrok.io/api`

### Benefits

- ✅ **Real HTTPS certificates** (no browser warnings)
- ✅ **External access** for testing from other devices
- ✅ **No certificate management** required
- ✅ **Simple HTTP containers** - ngrok handles HTTPS
- ✅ **Easy debugging** with ngrok web interface
- ✅ **Works with webhooks** and external services

### Monitoring

Ngrok provides excellent debugging interfaces:

- **Backend dashboard**: http://localhost:4040
  - View all backend API requests
  - Inspect request/response details
  - Replay requests for testing

- **Frontend dashboard**: http://localhost:4041
  - View all frontend requests
  - Monitor asset loading
  - Debug routing issues

### Testing Webhooks

Ngrok is ideal for testing webhook integrations:

```bash
# Example: Configure Stripe webhooks with your ngrok URL
# Webhook URL: https://your-backend-url.ngrok.io/api/webhooks/stripe

# Monitor webhooks in real-time
# Visit http://localhost:4040 and watch incoming requests
```

### Troubleshooting

**Issue: "ERR_NGROK_3200 - Tunnel not found"**
- Your ngrok auth token is invalid
- Solution: Check your token at https://dashboard.ngrok.com/get-started/your-authtoken

**Issue: "ERR_NGROK_6022 - Account limit reached"**
- Free ngrok accounts have tunnel limits
- Solution: Upgrade plan or close unused tunnels

**Issue: Frontend can't reach backend**
- Backend URL not updated in frontend environment
- Solution: Update `VITE_API_URL` in `.env.ngrok.local` and restart frontend

**Issue: URLs change every restart**
- Free ngrok provides random URLs
- Solution: Upgrade to ngrok paid plan for custom domains

### Cleanup

```bash
# Stop services
docker-compose -f docker-compose.ngrok.yml down

# Remove containers and volumes
docker-compose -f docker-compose.ngrok.yml down -v
```

---

## Comparison: Self-Signed vs Ngrok

### Self-Signed Certificates

**Best for:**
- Daily development
- Local testing
- Offline development
- Fast iteration

**Limitations:**
- Certificate warnings in browser
- Local access only
- Manual certificate acceptance
- Not suitable for external services

### Ngrok

**Best for:**
- Webhook testing
- External demos
- Mobile device testing
- OAuth callback testing
- Sharing with team

**Limitations:**
- Requires internet connection
- URLs change on free plan
- Account/auth required
- Slight latency

---

## Production Environment Variables

Both setups help you test production-like settings. Here's what should be configured for production:

```bash
# Production .env settings
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=None
SESSION_COOKIE_HTTPONLY=true
CORS_ORIGINS=https://your-production-domain.com
VITE_API_URL=https://your-production-api.com/api

# Optional security headers
TALISMAN_FORCE_HTTPS=true
TALISMAN_STRICT_TRANSPORT_SECURITY=true
```

---

## Common Testing Scenarios

### Scenario 1: Testing Secure Sessions

**Use:** Self-signed certificates
**Steps:**
1. Start HTTPS environment
2. Login to application
3. Check cookies in dev tools
4. Verify `Secure` and `SameSite=None` flags
5. Test session persistence across requests

### Scenario 2: Testing Stripe Webhooks

**Use:** Ngrok
**Steps:**
1. Start ngrok environment
2. Get backend ngrok URL
3. Configure Stripe webhook: `https://your-url.ngrok.io/api/webhooks/stripe`
4. Test payment in Stripe dashboard
5. Monitor webhook delivery at http://localhost:4040

### Scenario 3: Testing OAuth Callbacks

**Use:** Ngrok
**Steps:**
1. Start ngrok environment
2. Get frontend ngrok URL
3. Configure OAuth provider with ngrok callback URL
4. Test OAuth flow
5. Monitor redirects in ngrok dashboard

### Scenario 4: Mobile Device Testing

**Use:** Ngrok
**Steps:**
1. Start ngrok environment
2. Get frontend ngrok URL
3. Open URL on mobile device
4. Test responsive design
5. Test touch interactions

---

## Security Considerations

### Self-Signed Certificates

- ⚠️ **Never use in production** - Self-signed certificates are for development only
- ⚠️ **Don't skip certificate warnings in production browsers** - This disables important security
- ✅ **Safe for localhost** - Only accessible from your machine

### Ngrok

- ⚠️ **Don't commit `.env.ngrok.local`** - Contains your auth token
- ⚠️ **URLs are public** - Anyone with the URL can access your app
- ⚠️ **Free tier limitations** - Consider paid tier for sensitive testing
- ✅ **Secure tunnels** - Ngrok uses TLS encryption
- ✅ **Time-limited** - Tunnels expire, reducing exposure

---

## Troubleshooting

### Self-Signed Certificate Issues

**Browser refuses to accept certificate:**
```bash
# Regenerate certificates
rm -rf certs/
docker-compose -f docker-compose.https.yml up --build
```

**CORS errors despite configuration:**
```bash
# Verify CORS_ORIGINS matches frontend URL
cat .env.https | grep CORS_ORIGINS
# Should be: CORS_ORIGINS=https://localhost:3443
```

**Session not persisting:**
```bash
# Check cookie settings in browser dev tools
# Should see: Secure=true, SameSite=None

# Check backend logs for session errors
docker-compose -f docker-compose.https.yml logs backend | grep -i session
```

### Ngrok Issues

**Tunnel connection failed:**
```bash
# Verify auth token
docker-compose -f docker-compose.ngrok.yml logs | grep -i authtoken

# Test ngrok directly
ngrok http 5001 --authtoken=your_token_here
```

**Frontend can't reach backend API:**
```bash
# Check VITE_API_URL in frontend
docker-compose -f docker-compose.ngrok.yml exec frontend env | grep VITE_API_URL

# Should match backend ngrok URL + /api
```

---

## See Also

- [Development Setup Guide](../getting-started/development-setup.md)
- [Debugging Guide](debugging.md)
- [Testing Guide](testing.md)
- [Deployment Guide](../deployment/production.md)
- [Stripe Integration](../integrations/stripe.md) - Webhook testing

---

[← Back to Development Guide](README.md) | [Back to Documentation Home](../README.md)

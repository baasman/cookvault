# SPA Routing Fix for Production

## Problem
When users refresh the page on routes like `/recipes`, `/cookbooks`, etc., they get a 404 error in production. This is a common issue with Single Page Applications (SPAs) deployed on static hosting services.

## Root Cause
- The React app uses client-side routing (React Router with BrowserRouter)
- When a user navigates to `/recipes` and refreshes, the browser makes a server request for `/recipes`
- The server doesn't have a file at `/recipes`, so it returns 404
- The server needs to serve `index.html` for all routes so React Router can handle the routing

## Solutions Implemented

### 1. Nginx Configuration (`nginx.conf`)
Updated the nginx config to use a more robust SPA fallback pattern:
```nginx
# Handle SPA routing
location / {
    try_files $uri $uri/ @fallback;
}

# Fallback for SPA routes
location @fallback {
    rewrite ^.*$ /index.html last;
}
```

### 2. Static Redirects (`public/_redirects`)
Added a `_redirects` file for platforms that support it:
```
/*    /index.html   200
```

### 3. 404 Fallback (`public/404.html`)
Created a fallback 404.html that redirects to index.html:
```html
<script>
    window.location.replace('/');
</script>
```

### 4. Render Configuration (`render.yaml`)
Added explicit routing configuration for Render:
```yaml
routes:
  - type: rewrite
    source: /*
    destination: /index.html
```

### 5. Vite Configuration
Ensured proper base path configuration in `vite.config.ts`:
```typescript
base: '/',
```

## Deployment Steps

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Verify files are included:**
   - `dist/_redirects`
   - `dist/404.html`
   - `dist/index.html`

3. **Deploy to Render:**
   - The Docker build process will copy these files
   - Nginx will use the updated configuration
   - Static routes will fallback to index.html

## Testing

After deployment, test these scenarios:
1. Navigate to `/recipes` directly in browser ✅
2. Refresh page while on `/recipes` ✅
3. Navigate to `/cookbooks/123` directly ✅
4. Use browser back/forward buttons ✅

## Fallback Chain

The solution provides multiple fallback mechanisms:
1. **Nginx** - Primary routing solution
2. **_redirects** - Platform-specific routing
3. **404.html** - JavaScript redirect fallback
4. **render.yaml** - Render-specific configuration

This ensures the SPA routing works regardless of the hosting platform's specific requirements.
# API Reference

**Tags:** `api`, `rest`, `reference`, `endpoints`, `backend`
**Last updated:** 2025-11-14

Welcome to the Cookbook Creator API reference documentation. This section provides complete documentation for all REST API endpoints, authentication, and integration patterns.

---

## 📖 Getting Started

**New to the API?** Start here:

1. **[API Overview](overview.md)** - Authentication, rate limits, response formats
2. **[Authentication Guide](authentication-endpoints.md)** - Register, login, session management
3. **[Quick Start Examples](#quick-start-examples)** - Common API operations

**Base URL:**
```
Development: http://localhost:5001/api
Production:  https://your-domain.com/api
```

---

## 🔐 Authentication

All authenticated endpoints require a JWT Bearer token or session cookie.

**Get a token:**
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "username", "password": "password"}'
```

**Use the token:**
```bash
curl -X GET http://localhost:5001/api/recipes \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

📚 **Full Documentation:** [Authentication Endpoints](authentication-endpoints.md)

---

## 📚 API Endpoints

### Core Resources

#### 🔐 Authentication & Users
- **[Authentication Endpoints](authentication-endpoints.md)** - Register, login, logout, sessions, password management
- **User Endpoints** *(coming soon)* - Profile management, statistics, preferences

#### 📖 Recipes
- **[Recipe Endpoints](recipes-endpoints.md)** - Recipe CRUD, OCR upload, image management, privacy settings

#### 📚 Cookbooks
- **Cookbook Endpoints** *(coming soon)* - Cookbook management, Google Books integration

#### 👥 Recipe Groups
- **Recipe Groups Endpoints** *(coming soon)* - Custom collections and organization

### Integrations

#### 💳 Payments & Subscriptions
- **Payment Endpoints** *(coming soon)* - Stripe integration, subscriptions, purchases

#### 🖨️ Print-on-Demand
- **Print Order Endpoints** *(coming soon)* - Lulu integration, quotes, order management

### Public Access

#### 🌍 Public Endpoints
- **Public Endpoints** *(coming soon)* - Browse public recipes, platform statistics

### Utilities

#### 📄 Export
- **Export Endpoints** *(coming soon)* - PDF generation, cookbook exports

---

## 🚀 Quick Start Examples

### Register a New User

```bash
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "first_name": "John"
  }'
```

### Upload a Recipe Image for OCR

```bash
curl -X POST http://localhost:5001/api/recipes/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@/path/to/recipe.jpg" \
  -F "cookbook_id=5"
```

### Get Processing Status

```bash
curl -X GET http://localhost:5001/api/recipes/job-status/abc123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Search Public Recipes

```bash
curl -X GET "http://localhost:5001/api/recipes/discover?search=chocolate&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Recipe Ingredients

```bash
curl -X PUT http://localhost:5001/api/recipes/1/ingredients \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredients": [
      {"name": "Flour", "quantity": "2", "unit": "cups"},
      {"name": "Sugar", "quantity": "1", "unit": "cup"}
    ]
  }'
```

---

## 📋 Common Patterns

### Pagination

Most list endpoints support pagination:

```bash
GET /api/recipes?page=2&per_page=20
```

**Response includes:**
```json
{
  "items": [...],
  "total": 150,
  "pages": 8,
  "current_page": 2,
  "per_page": 20,
  "has_next": true,
  "has_prev": true
}
```

### Filtering & Search

```bash
# Search
GET /api/recipes?search=chocolate

# Filter by cookbook
GET /api/recipes?cookbook_id=5

# Filter by ownership
GET /api/recipes?filter=mine
GET /api/recipes?filter=collection
GET /api/recipes?filter=discover
```

### Error Handling

All errors return consistent format:

```json
{
  "error": "Descriptive error message"
}
```

**Common status codes:**
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Rate Limit Exceeded

---

## 🔑 Authentication Methods

### 1. JWT Bearer Token (Recommended)

```http
GET /api/recipes HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Pros:** Stateless, works across domains, suitable for mobile/SPA
**Cons:** Must manage token refresh

### 2. Session Cookie

```http
GET /api/recipes HTTP/1.1
Cookie: session=abc123...
```

**Pros:** Automatic, secure with httpOnly
**Cons:** Requires same-origin or CORS configuration

📚 **Details:** [API Overview - Authentication](overview.md#authentication)

---

## 📊 Rate Limits

| Category | Limit | Window |
|----------|-------|--------|
| Authentication | 10 requests | 1 minute |
| Recipe Upload | 10 uploads | 1 hour |
| Job Status | 60 requests | 1 minute |
| Print Quotes | 10 requests | 1 minute |

**Rate limit headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

📚 **Full Guide:** [API Overview - Rate Limiting](overview.md#rate-limiting)

---

## 🎯 Use Cases

### Digitize a Recipe from a Photo

1. **Upload image** - `POST /api/recipes/upload`
2. **Poll for status** - `GET /api/recipes/job-status/<job_id>`
3. **Get parsed recipe** - Included in completed job status
4. **Edit as needed** - `PUT /api/recipes/<id>/ingredients`, `/instructions`

### Create a Custom Recipe Collection

1. **Create recipe group** - `POST /api/recipe-groups`
2. **Find recipes** - `GET /api/recipes/discover?search=...`
3. **Add to group** - `POST /api/recipe-groups/<id>/recipes/<recipe_id>`
4. **View collection** - `GET /api/recipe-groups/<id>`

### Order a Printed Cookbook

1. **Get print quote** - `POST /api/print-orders/quote`
2. **Create order** - `POST /api/print-orders/`
3. **Process payment** - `POST /api/print-orders/<id>/payment`
4. **Submit for printing** - `POST /api/print-orders/<id>/submit`
5. **Track status** - `GET /api/print-orders/<id>`

---

## 🔧 Development Tools

### Testing with cURL

```bash
# Save token to variable
TOKEN=$(curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"user","password":"pass"}' \
  | jq -r '.access_token')

# Use token in requests
curl -X GET http://localhost:5001/api/recipes \
  -H "Authorization: Bearer $TOKEN"
```

### Testing with HTTPie

```bash
# More readable syntax
http POST localhost:5001/api/auth/login login=user password=pass

# Automatic JSON
http GET localhost:5001/api/recipes Authorization:"Bearer $TOKEN"
```

### Using Postman

1. Import API collection
2. Set `{{baseUrl}}` = `http://localhost:5001/api`
3. Set `{{token}}` = your access token
4. Use Collection Runner for automated tests

---

## 📖 Additional Resources

### Integration Guides

- **[Anthropic Claude](../integrations/anthropic-claude.md)** *(coming soon)* - Recipe OCR and parsing
- **[Cloudinary](../integrations/cloudinary.md)** *(coming soon)* - Image storage and processing
- **[Stripe](../integrations/stripe.md)** *(coming soon)* - Payment processing
- **[Lulu Print](../integrations/lulu-print.md)** - Print-on-demand

### Backend Documentation

- **[Backend README](../../backend/README.md)** - Setup and architecture
- **[Database Schema](../architecture/database-schema.md)** *(coming soon)* - Data models
- **[Operations Guide](../operations/README.md)** - Production operations

### Testing

- **[Testing Guide](../development/testing.md)** *(coming soon)* - Writing API tests
- **[Load Testing](../development/load-testing.md)** - Performance testing

---

## 🐛 Troubleshooting

### Common Issues

**"Invalid token" or "Unauthorized"**
- Token may be expired (tokens last 1 hour)
- Token not included in Authorization header
- Check header format: `Authorization: Bearer <token>`

**"Rate limit exceeded"**
- Wait for rate limit window to reset
- Check `X-RateLimit-Reset` header for reset time
- Consider upgrading to premium tier

**"Upload limit exceeded"**
- Free tier: 10 uploads/month
- Solution: Upgrade to premium or wait for next month

**"File too large"**
- Max file size: 8 MB
- Compress image before uploading
- Use tools like ImageOptim or tinypng.com

**"Recipe not found" for public recipe**
- Check recipe ID is correct
- Ensure recipe is actually public
- Verify you have authentication token

---

## 📞 Support

**Need help?**

- **Documentation:** [docs/README.md](../README.md)
- **Issues:** GitHub Issues
- **Debugging:** [Debugging Guide](../development/debugging.md) *(coming soon)*

---

## 🔄 API Versioning

The API is currently **unversioned**. All endpoints use `/api/` prefix.

**Future:** Breaking changes will introduce versioned endpoints (`/api/v2/`)

---

## See Also

- **[API Overview](overview.md)** - Detailed API reference
- **[Architecture Overview](../architecture/overview.md)** *(coming soon)* - System design
- **[Getting Started](../getting-started/installation.md)** - Setup guide

---

[← Back to Documentation Home](../README.md)

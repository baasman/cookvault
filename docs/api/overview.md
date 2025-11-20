# API Overview

**Tags:** `api`, `rest`, `endpoints`, `authentication`, `reference`
**Last updated:** 2025-11-14

Complete API reference for the Cookbook Creator backend. This guide covers authentication, request/response patterns, error handling, and rate limiting.

---

## Base URL

```
Development: http://localhost:5001/api
Production:  https://your-domain.com/api
```

All API endpoints are prefixed with `/api`.

---

## Authentication

### Authentication Methods

The API supports two authentication methods:

#### 1. JWT Bearer Token (Recommended)

```http
GET /api/recipes HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 2. Session-Based (Cookie)

```http
GET /api/recipes HTTP/1.1
Cookie: session=abc123...
```

### Getting a Token

**Register a new account:**
```bash
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "role": "USER"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

**Login with existing account:**
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "johndoe",
    "password": "SecurePass123!"
  }'
```

### Token Usage

Include the token in the `Authorization` header for all authenticated requests:

```bash
curl -X GET http://localhost:5001/api/recipes \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| **USER** | Standard user | CRUD own recipes/cookbooks, view public content, limited uploads (free tier) |
| **PREMIUM** | Premium subscriber | Unlimited uploads, all USER permissions |
| **ADMIN** | Administrator | Full access to all resources, user management, featured recipes |

---

## Response Format

### Success Response

All successful responses follow this pattern:

```json
{
  "message": "Operation successful",
  "data_key": {
    "id": 1,
    "...": "..."
  }
}
```

### Error Response

All error responses include an error message:

```json
{
  "error": "Resource not found"
}
```

### Paginated Response

Endpoints returning lists use this pagination format:

```json
{
  "items": [...],
  "total": 150,
  "pages": 15,
  "current_page": 1,
  "per_page": 10,
  "has_next": true,
  "has_prev": false
}
```

**Pagination parameters:**
- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 10, max: 100)

---

## HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT, DELETE |
| 201 | Created | Successful POST creating new resource |
| 204 | No Content | Successful DELETE with no response body |
| 400 | Bad Request | Invalid request data or validation error |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

---

## Rate Limiting

Rate limits protect the API from abuse and ensure fair usage.

### Rate Limit Headers

Responses include rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1640995200
```

### Rate Limits by Endpoint Category

| Category | Limit | Window |
|----------|-------|--------|
| **Authentication** | 10 requests | 1 minute |
| **Recipe Upload** | 10 uploads | 1 hour |
| **Job Status** | 60 requests | 1 minute |
| **Print Quotes** | 10 requests | 1 minute |
| **Print Orders** | 5 requests | 1 minute |
| **Webhooks** | 100 requests | 1 hour |

### Rate Limit Exceeded Response

```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

**Status Code:** 429 Too Many Requests

---

## Upload Limits

Free tier users have monthly upload limits:

| Tier | Monthly Uploads | Max File Size |
|------|----------------|---------------|
| **Free** | 10 | 8 MB |
| **Premium** | Unlimited | 8 MB |

**Supported image formats:** PNG, JPG, JPEG, GIF, BMP, TIFF, WebP

---

## File Uploads

### Multipart Form Data

For endpoints accepting file uploads, use `multipart/form-data`:

```bash
curl -X POST http://localhost:5001/api/recipes/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@/path/to/recipe.jpg" \
  -F "cookbook_id=5" \
  -F "page_number=42"
```

### Image Upload Response

```json
{
  "message": "Image uploaded successfully",
  "job_id": "abc123",
  "image_id": 789,
  "status": "processing",
  "status_url": "/api/recipes/job-status/abc123"
}
```

---

## Background Processing

Recipe OCR and PDF generation run in the background. Use job status endpoints to check progress.

### Processing Workflow

1. **Upload image** → Receive `job_id`
2. **Poll status** → Check `/api/recipes/job-status/<job_id>`
3. **Wait for completion** → Status changes to "completed"
4. **Retrieve recipe** → Access parsed recipe data

### Job Status Response

```json
{
  "job": {
    "job_id": "abc123",
    "status": "processing",
    "progress": 50,
    "message": "Extracting text from image..."
  },
  "recipe": null
}
```

**Possible statuses:**
- `pending` - Job queued
- `processing` - Currently processing
- `completed` - Successfully completed
- `failed` - Processing failed

---

## Search & Filtering

Many list endpoints support searching and filtering:

### Search Parameters

```bash
# Search recipes by title/description
GET /api/recipes?search=chocolate+cake

# Filter by cookbook
GET /api/recipes?cookbook_id=5

# Filter by ownership
GET /api/recipes?filter=mine          # My recipes only
GET /api/recipes?filter=collection    # My collection
GET /api/recipes?filter=discover      # Public recipes
```

### Sort Parameters

```bash
# Sort cookbooks
GET /api/cookbooks?sort_by=title
GET /api/cookbooks?sort_by=recipe_count
GET /api/cookbooks?sort_by=created_at
```

---

## Privacy & Access Control

### Recipe Privacy

- **Private recipes**: Only visible to owner and admins
- **Public recipes**: Visible to all users
- **Published recipes**: Public with published timestamp

### Cookbook Access

- **Free cookbooks**: Accessible to all users
- **Purchasable cookbooks**: Require purchase for full access
- **User-created cookbooks**: Always accessible to creator

---

## Error Handling

### Validation Errors

```json
{
  "error": "Validation failed",
  "details": {
    "email": ["Invalid email format"],
    "password": ["Password must be at least 8 characters"]
  }
}
```

### Authentication Errors

```json
{
  "error": "Invalid credentials"
}
```

```json
{
  "error": "Session token not found or invalid"
}
```

### Authorization Errors

```json
{
  "error": "You do not have permission to access this resource"
}
```

### Resource Not Found

```json
{
  "error": "Recipe not found"
}
```

---

## Common Request Examples

### Create Recipe

```bash
curl -X POST http://localhost:5001/api/recipes \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Chocolate Chip Cookies",
    "cookbook_id": 5
  }'
```

### Update Recipe Ingredients

```bash
curl -X PUT http://localhost:5001/api/recipes/123/ingredients \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredients": [
      {
        "name": "All-purpose flour",
        "quantity": "2",
        "unit": "cups",
        "category": "Dry Ingredients"
      },
      {
        "name": "Butter",
        "quantity": "1",
        "unit": "cup",
        "preparation": "softened"
      }
    ]
  }'
```

### Upload Recipe Image

```bash
curl -X POST http://localhost:5001/api/recipes/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@recipe.jpg" \
  -F "cookbook_id=5" \
  -F "page_number=10"
```

### Search Public Recipes

```bash
curl -X GET "http://localhost:5001/api/recipes/discover?search=pasta&difficulty=easy&page=1&per_page=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## CORS Configuration

The API supports Cross-Origin Resource Sharing (CORS) for browser-based applications.

**Allowed Origins:** Configured via `CORS_ORIGINS` environment variable

**Allowed Methods:** GET, POST, PUT, DELETE, OPTIONS

**Allowed Headers:** Content-Type, Authorization

---

## Testing the API

### Using cURL

```bash
# Test authentication
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "user", "password": "pass"}'

# Test authenticated endpoint
curl -X GET http://localhost:5001/api/recipes \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Using HTTPie

```bash
# More readable than cURL
http POST localhost:5001/api/auth/login login=user password=pass
http GET localhost:5001/api/recipes Authorization:"Bearer YOUR_TOKEN"
```

### Using Postman

1. Import the API collection (if available)
2. Set environment variables for base URL and token
3. Use Collection Runner for automated testing

---

## API Endpoints

Detailed documentation for each endpoint category:

- **[Authentication](authentication-endpoints.md)** - Register, login, sessions, password management
- **[Recipes](recipes-endpoints.md)** - Recipe CRUD, upload, OCR processing, images
- **[Cookbooks](cookbooks-endpoints.md)** - Cookbook management, Google Books integration
- **[Payments](payments-endpoints.md)** - Subscriptions, purchases, Stripe integration
- **[Print Orders](print-orders-endpoints.md)** - Print-on-demand via Lulu
- **[Public Endpoints](public-endpoints.md)** - Unauthenticated access to public content

---

## Webhooks

The API receives webhooks from external services:

### Stripe Webhooks

**Endpoint:** `POST /api/payments/webhook`

**Events:**
- `payment_intent.succeeded` - Payment completed
- `customer.subscription.created` - Subscription created
- `customer.subscription.updated` - Subscription changed
- `customer.subscription.deleted` - Subscription cancelled

### Lulu Webhooks

**Endpoint:** `POST /api/print-webhooks/lulu-status`

**Events:**
- `validation_completed` - PDF validation complete
- `printing_started` - Order sent to printer
- `shipped` - Order shipped to customer
- `delivered` - Order delivered
- `cancelled` - Order cancelled
- `failed` - Order failed

---

## SDK & Client Libraries

Currently, no official SDKs are available. The API follows REST principles and can be accessed from any HTTP client.

**Recommended libraries:**
- **JavaScript/TypeScript:** `axios`, `fetch`
- **Python:** `requests`, `httpx`
- **Ruby:** `httparty`, `faraday`
- **PHP:** `Guzzle`

---

## Versioning

The API is currently **unversioned**. Breaking changes will be communicated in advance.

**Future:** API versioning via URL path (`/api/v1/`, `/api/v2/`) or header-based versioning.

---

## Support

For API support and questions:

- **Documentation:** [docs/README.md](../README.md)
- **Issues:** GitHub Issues
- **Email:** support@cookbook-creator.com (if applicable)

---

## See Also

- [Authentication Endpoints](authentication-endpoints.md)
- [Recipes Endpoints](recipes-endpoints.md)
- [Cookbooks Endpoints](cookbooks-endpoints.md)
- [Payments Endpoints](payments-endpoints.md)
- [Getting Started Guide](../getting-started/installation.md)

---

[← Back to API Reference](README.md) | [Back to Documentation Home](../README.md)

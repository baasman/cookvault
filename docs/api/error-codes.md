# API Error Codes Reference

**Tags:** `api`, `errors`, `troubleshooting`, `reference`
**Last updated:** 2026-02-13

Complete reference for all API error codes, HTTP status codes, and error messages.

---

## HTTP Status Codes

### Success Codes

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request succeeded. Used for GET, PUT, DELETE operations |
| 201 | Created | Resource created successfully. Used for POST operations |
| 204 | No Content | Request succeeded with no response body |

### Client Error Codes

| Code | Name | Description | Common Causes |
|------|------|-------------|---------------|
| 400 | Bad Request | Invalid request data | Missing required fields, validation errors, malformed JSON |
| 401 | Unauthorized | Authentication required | Missing token, invalid token, expired token |
| 403 | Forbidden | Authenticated but not authorized | Insufficient permissions, inactive account, wrong owner |
| 404 | Not Found | Resource doesn't exist | Invalid ID, deleted resource, wrong endpoint |
| 409 | Conflict | Resource conflict | Duplicate username, email, or unique field |
| 422 | Unprocessable Entity | Semantic validation error | Business logic validation failed |
| 423 | Locked | Account locked | Too many failed login attempts |
| 429 | Too Many Requests | Rate limit exceeded | Exceeded API rate limits |

### Server Error Codes

| Code | Name | Description |
|------|------|-------------|
| 500 | Internal Server Error | Unexpected server error |
| 502 | Bad Gateway | Upstream service error (Cloudinary, Stripe, etc.) |
| 503 | Service Unavailable | Service temporarily unavailable |

---

## Error Response Format

All API errors return a consistent JSON format:

```json
{
  "error": "Human-readable error message"
}
```

Some validation errors include additional details:

```json
{
  "error": "Validation failed",
  "details": {
    "email": ["Invalid email format"],
    "password": ["Password must be at least 8 characters"]
  }
}
```

---

## Authentication Errors

### 401 Unauthorized

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Authentication required` | No authentication token provided | Include `Authorization: Bearer <token>` header |
| `Invalid credentials` | Wrong username/email or password | Verify login credentials |
| `Session token not found or invalid` | Session expired or invalid | Login again to get new token |
| `Invalid token` | JWT token malformed or tampered | Get new token via login |
| `Token has expired` | JWT token past expiration | Login again to get new token |

### 403 Forbidden

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Account is not active` | Account deactivated | Contact support |
| `Account is pending verification` | Email/phone not verified | Complete verification |
| `Account is pending deletion` | Deletion requested | Cancel deletion or wait |
| `Permission denied` | Not owner of resource | Use own resources or request access |
| `Admin access required` | Admin-only endpoint | Use admin account |

### 423 Locked

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Account is locked` | Too many failed login attempts | Wait 30 minutes or contact support |
| `Account locked due to too many failed attempts` | 5+ failed logins | Wait for lockout period to expire |

---

## Validation Errors (400 Bad Request)

### User Registration

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Username is required` | Missing username field | Provide username |
| `Email is required` | Missing email field | Provide email |
| `Password is required` | Missing password field | Provide password |
| `Invalid email format` | Email doesn't match pattern | Use valid email format |
| `Password must be at least 8 characters` | Password too short | Use 8+ character password |
| `Username must be 3-80 characters` | Username length invalid | Adjust username length |
| `Username can only contain letters, numbers, underscores, and hyphens` | Invalid characters | Remove special characters |

### Recipe Operations

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Title is required` | Missing recipe title | Provide title field |
| `No data provided` | Empty request body | Include JSON data |
| `Invalid difficulty. Must be easy, medium, or hard` | Invalid difficulty value | Use: easy, medium, or hard |
| `Prep time must be a positive number` | Negative prep time | Use positive number |
| `Cook time must be a positive number` | Negative cook time | Use positive number |
| `Servings must be a positive number` | Invalid servings | Use positive number |

### File Upload

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `No image file provided` | Missing file in request | Include file in multipart form |
| `File size exceeds 8MB limit` | File too large | Compress or resize image |
| `Invalid file type` | Unsupported format | Use: PNG, JPG, JPEG, GIF, BMP, TIFF, WebP |
| `File is empty` | Zero-byte file | Upload valid file |

### Cookbook Operations

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Cookbook title is required` | Missing title | Provide cookbook title |
| `Invalid price. Must be a positive number` | Negative price | Use positive price value |

---

## Conflict Errors (409 Conflict)

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Username already exists` | Username taken | Choose different username |
| `Email already exists` | Email already registered | Use different email or login |
| `Phone number already exists` | Phone registered | Use different phone number |
| `Recipe group name already exists` | Duplicate group name | Choose different name |

---

## Not Found Errors (404 Not Found)

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Recipe not found` | Invalid recipe ID | Verify recipe exists |
| `Cookbook not found` | Invalid cookbook ID | Verify cookbook exists |
| `User not found` | Invalid user ID | Verify user exists |
| `Session not found` | Invalid session ID | List sessions first |
| `Processing job not found` | Invalid job ID | Use job ID from upload response |
| `Recipe group not found` | Invalid group ID | Verify group exists |
| `Ingredient not found` | Invalid ingredient ID | Verify ingredient exists |
| `Instruction not found` | Invalid instruction ID | Verify instruction exists |
| `Image not found` | Invalid image ID | Verify image exists |

---

## Rate Limit Errors (429 Too Many Requests)

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Rate limit exceeded` | Too many requests | Wait and retry |
| `Upload limit exceeded` | Too many uploads | Wait for limit reset or upgrade |
| `Please wait before requesting another verification` | SMS/email spam protection | Wait 2 minutes between requests |

### Rate Limit Response Headers

When rate limited, check these headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

---

## Business Logic Errors

### Password Operations

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Current password is incorrect` | Wrong current password | Verify current password |
| `Password is incorrect` | Wrong password for action | Verify password |
| `New password must be different from current` | Same password | Choose new password |
| `Invalid or expired reset token` | Token expired/invalid | Request new reset email |

### Verification

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Invalid verification code` | Wrong code entered | Check code and retry |
| `Verification code has expired` | Code expired (10 min) | Request new code |
| `Account already verified` | Already verified | Proceed to login |
| `Invalid verification token` | Bad email token | Request new verification email |

### Account Operations

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `No pending deletion request` | Cancel without delete | No action needed |
| `Account deletion already pending` | Duplicate request | Wait for deletion or cancel |

### Payment Operations

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Payment processing failed` | Stripe error | Check payment details |
| `Cookbook not available for purchase` | Not purchasable | Contact cookbook owner |
| `Already purchased` | Duplicate purchase | Access existing purchase |
| `Invalid payment amount` | Price mismatch | Refresh and retry |

### Print Orders

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Print order not found` | Invalid order ID | Verify order ID |
| `Cannot modify submitted order` | Order already submitted | Contact support |
| `Invalid print specifications` | Bad print config | Check valid specifications |

---

## External Service Errors

### Cloudinary (Image Storage)

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Image upload failed` | Cloudinary error | Retry upload |
| `Image processing failed` | Transform error | Try different image |

### Stripe (Payments)

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Payment method declined` | Card declined | Try different payment method |
| `Subscription creation failed` | Stripe API error | Retry or contact support |

### Google Books API

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Google Books search failed` | API error | Retry search |
| `Book not found in Google Books` | ISBN not found | Verify ISBN |

### OCR/AI Processing

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Could not extract text from image` | OCR failed | Use clearer image |
| `Recipe parsing failed` | AI couldn't parse | Try cleaner recipe format |
| `Image quality too low` | Poor image | Use higher resolution |

---

## Error Handling Best Practices

### Client-Side Handling

```javascript
try {
  const response = await fetch('/api/recipes', {
    headers: { 'Authorization': `Bearer ${token}` }
  });

  if (!response.ok) {
    const error = await response.json();

    switch (response.status) {
      case 401:
        // Redirect to login
        redirectToLogin();
        break;
      case 403:
        // Show permission error
        showError('You don\'t have permission to access this resource');
        break;
      case 404:
        // Show not found
        showError('Resource not found');
        break;
      case 429:
        // Rate limited - implement backoff
        const retryAfter = response.headers.get('Retry-After');
        setTimeout(() => retry(), retryAfter * 1000);
        break;
      default:
        showError(error.error || 'An error occurred');
    }
  }
} catch (networkError) {
  showError('Network error. Please check your connection.');
}
```

### Retry Strategy

For transient errors (500, 502, 503, 429), implement exponential backoff:

```javascript
async function fetchWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fetch(url, options);

    if (response.ok) return response;

    if ([500, 502, 503, 429].includes(response.status)) {
      const delay = Math.pow(2, i) * 1000; // 1s, 2s, 4s
      await new Promise(r => setTimeout(r, delay));
      continue;
    }

    throw new Error(`HTTP ${response.status}`);
  }
  throw new Error('Max retries exceeded');
}
```

---

## Debugging Tips

### Check Request Format

1. **Headers**: Ensure `Content-Type: application/json` for JSON bodies
2. **Authorization**: Format must be `Bearer <token>` (note the space)
3. **Body**: Must be valid JSON for JSON endpoints

### Common Mistakes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 401 on all requests | Token not included | Add Authorization header |
| 401 after working | Token expired | Re-authenticate |
| 400 with valid data | Wrong Content-Type | Set `Content-Type: application/json` |
| 404 on known resource | Wrong ID type | Use integer IDs, not strings |
| CORS errors | Missing origin | Configure CORS_ORIGINS |

### Debug Endpoints (Development Only)

```bash
# Test API connectivity
GET /api/auth/test

# Check auth state
GET /api/auth/debug

# Verify JWT token
GET /api/auth/jwt-debug
```

---

## See Also

- [API Overview](overview.md) - Authentication and general patterns
- [Authentication Endpoints](authentication-endpoints.md) - Auth-specific errors
- [Rate Limiting](#rate-limit-errors-429-too-many-requests) - Rate limit details

---

[Back to API Reference](README.md) | [Back to Documentation Home](../README.md)

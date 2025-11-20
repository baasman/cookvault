# Authentication Endpoints

**Tags:** `api`, `authentication`, `jwt`, `session`, `security`
**Last updated:** 2025-11-14

Complete reference for authentication, session management, and password operations.

---

## Table of Contents

- [Register](#register)
- [Login](#login)
- [Logout](#logout)
- [Get Current User](#get-current-user)
- [Session Management](#session-management)
- [Password Management](#password-management)
- [Debug Endpoints](#debug-endpoints)

---

## Register

Create a new user account.

**Endpoint:** `POST /api/auth/register`

**Authentication:** None required

**Rate Limit:** 10 requests / minute

### Request Body

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "first_name": "John",      // Optional
  "last_name": "Doe"          // Optional
}
```

### Validation Rules

- **username**: 3-80 characters, alphanumeric + underscore/hyphen
- **email**: Valid email format
- **password**: Minimum 8 characters
- **first_name/last_name**: Optional, max 100 characters each

### Success Response

**Status:** 201 Created

```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "role": "USER",
    "first_name": "John",
    "last_name": "Doe",
    "created_at": "2025-11-14T12:00:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "session_token": "abc123..."
}
```

### Error Responses

**409 Conflict** - Username or email already exists
```json
{
  "error": "Username already exists"
}
```

**400 Bad Request** - Validation failed
```json
{
  "error": "Invalid email format"
}
```

### Example

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

---

## Login

Authenticate a user and receive access token.

**Endpoint:** `POST /api/auth/login`

**Authentication:** None required

**Rate Limit:** 10 requests / minute

### Request Body

```json
{
  "login": "johndoe",           // Username or email
  "password": "SecurePass123!"
}
```

### Success Response

**Status:** 200 OK

```json
{
  "message": "Login successful",
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

### Error Responses

**401 Unauthorized** - Invalid credentials
```json
{
  "error": "Invalid credentials"
}
```

**429 Too Many Requests** - Account locked
```json
{
  "error": "Account locked due to too many failed attempts. Try again in 30 minutes."
}
```

### Security Features

- **Account Lockout**: 5 failed attempts locks account for 30 minutes
- **Session Invalidation**: Old sessions are invalidated on new login
- **IP Tracking**: Failed attempts tracked by IP address

### Example

```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "johndoe",
    "password": "SecurePass123!"
  }'
```

---

## Logout

Logout current user and invalidate session.

**Endpoint:** `POST /api/auth/logout`

**Authentication:** Required

### Success Response

**Status:** 200 OK

```json
{
  "message": "Logout successful"
}
```

### Example

```bash
curl -X POST http://localhost:5001/api/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Get Current User

Retrieve authenticated user information.

**Endpoint:** `GET /api/auth/me`

**Authentication:** Required

### Success Response

**Status:** 200 OK

```json
{
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "bio": "Home chef and recipe enthusiast",
    "avatar": "https://cloudinary.com/.../avatar.jpg",
    "role": "USER",
    "is_active": true,
    "created_at": "2025-01-01T00:00:00Z",
    "subscription_tier": "free",
    "uploads_this_month": 3,
    "upload_limit": 10
  }
}
```

### Example

```bash
curl -X GET http://localhost:5001/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Session Management

### List Active Sessions

Get all active sessions for the current user.

**Endpoint:** `GET /api/auth/sessions`

**Authentication:** Required

#### Success Response

**Status:** 200 OK

```json
{
  "sessions": [
    {
      "id": 1,
      "session_token": "abc123...",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2025-11-14T10:00:00Z",
      "last_accessed": "2025-11-14T12:00:00Z",
      "is_current": true
    },
    {
      "id": 2,
      "session_token": "def456...",
      "ip_address": "192.168.1.5",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2025-11-13T09:00:00Z",
      "last_accessed": "2025-11-13T22:00:00Z",
      "is_current": false
    }
  ]
}
```

#### Example

```bash
curl -X GET http://localhost:5001/api/auth/sessions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Revoke Session

Revoke a specific session (logout from a device).

**Endpoint:** `DELETE /api/auth/sessions/<session_id>`

**Authentication:** Required

#### Success Response

**Status:** 200 OK

```json
{
  "message": "Session revoked successfully"
}
```

#### Error Responses

**404 Not Found** - Session doesn't exist or doesn't belong to user
```json
{
  "error": "Session not found"
}
```

#### Example

```bash
curl -X DELETE http://localhost:5001/api/auth/sessions/2 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Password Management

### Change Password

Change the current user's password.

**Endpoint:** `POST /api/auth/change-password`

**Authentication:** Required

#### Request Body

```json
{
  "current_password": "OldPass123!",
  "new_password": "NewSecurePass456!"
}
```

#### Validation Rules

- **new_password**: Minimum 8 characters
- **current_password**: Must match existing password

#### Success Response

**Status:** 200 OK

```json
{
  "message": "Password changed successfully"
}
```

**Note:** All other sessions (except current) are invalidated for security.

#### Error Responses

**400 Bad Request** - Current password incorrect
```json
{
  "error": "Current password is incorrect"
}
```

**400 Bad Request** - New password too short
```json
{
  "error": "Password must be at least 8 characters long"
}
```

#### Example

```bash
curl -X POST http://localhost:5001/api/auth/change-password \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "OldPass123!",
    "new_password": "NewSecurePass456!"
  }'
```

---

## Debug Endpoints

**Note:** These endpoints are for development/debugging only and should be disabled in production.

### Test Endpoint

**Endpoint:** `GET /api/auth/test`

Simple test endpoint to verify API is reachable.

### Debug Auth State

**Endpoint:** `GET /api/auth/debug`

Returns current authentication state information.

### Auth Status

**Endpoint:** `GET /api/auth/status`

**Authentication:** None required

Returns whether a valid session exists.

### JWT Debug

**Endpoint:** `GET /api/auth/jwt-debug`

Returns JWT token details for debugging.

### Environment Check

**Endpoint:** `GET /api/auth/env-check`

Checks environment configuration (SECRET_KEY, SESSION_COOKIE_SECURE, etc.).

---

## Security Best Practices

### Token Storage

**✅ Recommended:**
- Store JWT in memory or secure httpOnly cookie
- Use short-lived access tokens (1 hour)
- Implement token refresh mechanism

**❌ Not Recommended:**
- localStorage (vulnerable to XSS)
- sessionStorage (vulnerable to XSS)
- Unencrypted storage

### Password Requirements

- Minimum 8 characters
- Consider complexity requirements (uppercase, lowercase, numbers, symbols)
- Use bcrypt hashing (automatic)
- Never log or display passwords

### Session Security

- Sessions automatically expire after inactivity
- Monitor active sessions regularly
- Revoke suspicious sessions immediately
- Use HTTPS in production (SESSION_COOKIE_SECURE=true)

---

## Error Reference

| Status | Error | Cause |
|--------|-------|-------|
| 400 | Invalid email format | Email doesn't match pattern |
| 400 | Password too short | Password < 8 characters |
| 401 | Invalid credentials | Wrong username/email or password |
| 409 | Username already exists | Username taken |
| 409 | Email already exists | Email already registered |
| 429 | Account locked | Too many failed login attempts |
| 429 | Rate limit exceeded | Too many requests |

---

## See Also

- [API Overview](overview.md) - Authentication methods, rate limits
- [User Profile Endpoints](user-endpoints.md) - Profile management
- [Security Guide](../operations/security.md) - Production security configuration

---

[← Back to API Reference](README.md) | [Back to Documentation Home](../README.md)

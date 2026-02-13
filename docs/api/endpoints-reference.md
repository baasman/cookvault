# API Endpoints Quick Reference

**Tags:** `api`, `endpoints`, `reference`, `quick-reference`
**Last updated:** 2026-02-13

Quick reference for all API endpoints with authentication requirements and rate limits.

---

## Authentication Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| POST | `/auth/register` | None | 20/hour | Register new account |
| POST | `/auth/verify-email` | None | 20/hour | Verify email with token |
| POST | `/auth/verify-phone` | None | 20/hour | Verify phone with code |
| POST | `/auth/resend-verification` | None | 20/hour | Resend verification |
| POST | `/auth/login` | None | 20/hour | Authenticate user |
| POST | `/auth/logout` | Required | - | Logout and invalidate session |
| GET | `/auth/me` | Required | 1000/hour | Get current user info |
| GET | `/auth/status` | None | 1000/hour | Check auth status |
| POST | `/auth/forgot-password` | None | 20/hour | Request password reset |
| POST | `/auth/validate-reset-token` | None | 20/hour | Validate reset token |
| POST | `/auth/reset-password` | None | 20/hour | Reset password |
| POST | `/auth/change-password` | Required | 20/hour | Change password |
| GET | `/auth/sessions` | Required | 1000/hour | List active sessions |
| DELETE | `/auth/sessions/<id>` | Required | 100/hour | Revoke session |
| DELETE | `/auth/account` | Required | 100/hour | Request account deletion |
| POST | `/auth/account/cancel-deletion` | Required | 100/hour | Cancel deletion |
| GET | `/auth/account/deletion-status` | Required | 1000/hour | Get deletion status |
| GET | `/auth/export` | Required | 100/hour | Export user data (ZIP) |

---

## User Profile Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | `/user/profile` | Required | 1000/hour | Get current user profile |
| PUT | `/user/profile` | Required | 100/hour | Update profile |
| GET | `/users/<id>` | Optional | 1000/hour | Get public user profile |
| GET | `/users/by-username/<username>` | Optional | 1000/hour | Get user by username |

---

## Recipe Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | `/recipes` | Required | 1000/hour | List recipes with filters |
| POST | `/recipes` | Required | 100/hour | Create empty recipe |
| GET | `/recipes/<id>` | Required | 1000/hour | Get recipe details |
| PUT | `/recipes/<id>` | Required | 100/hour | Update recipe metadata |
| DELETE | `/recipes/<id>` | Required | 100/hour | Delete recipe |
| POST | `/recipes/upload` | Required | 50/hour | Upload image for OCR |
| POST | `/recipes/upload-text` | Required | 50/hour | Upload text for parsing |
| POST | `/recipes/batch-upload` | Required | 50/hour | Multi-image upload |
| GET | `/recipes/job-status/<id>` | Required | 5000/hour | Get processing status |
| GET | `/recipes/multi-job-status/<id>` | Required | 5000/hour | Multi-job status |
| PUT | `/recipes/<id>/ingredients` | Required | 100/hour | Update ingredients |
| PUT | `/recipes/<id>/instructions` | Required | 100/hour | Update instructions |
| PUT | `/recipes/<id>/tags` | Required | 100/hour | Update tags |
| POST | `/recipes/<id>/images` | Required | 50/hour | Add recipe image |
| GET | `/recipes/<id>/images` | Required | 1000/hour | List recipe images |
| DELETE | `/recipes/<id>/images/<img_id>` | Required | 100/hour | Delete image |
| POST | `/recipes/<id>/publish` | Required | 100/hour | Publish recipe |
| POST | `/recipes/<id>/unpublish` | Required | 100/hour | Unpublish recipe |
| POST | `/recipes/<id>/notes` | Required | 100/hour | Add/update note |
| GET | `/recipes/<id>/notes` | Required | 1000/hour | Get user's note |
| DELETE | `/recipes/<id>/notes` | Required | 100/hour | Delete note |
| GET | `/recipes/<id>/comments` | Optional | 1000/hour | List comments |
| POST | `/recipes/<id>/comments` | Required | 100/hour | Add comment |
| DELETE | `/recipes/<id>/comments/<c_id>` | Required | 100/hour | Delete comment |
| GET | `/recipes/search` | Required | 1000/hour | Search all recipes |
| GET | `/recipes/discover` | Required | 1000/hour | Browse public recipes |

---

## Cookbook Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | `/cookbooks` | Required | 1000/hour | List user's cookbooks |
| POST | `/cookbooks` | Required | 100/hour | Create cookbook |
| GET | `/cookbooks/<id>` | Required | 1000/hour | Get cookbook details |
| PUT | `/cookbooks/<id>` | Required | 100/hour | Update cookbook |
| DELETE | `/cookbooks/<id>` | Required | 100/hour | Delete cookbook |
| GET | `/cookbooks/<id>/recipes` | Required | 1000/hour | List cookbook recipes |
| POST | `/cookbooks/<id>/images` | Required | 50/hour | Upload cover image |
| GET | `/cookbooks/search` | Required | 1000/hour | Search cookbooks |
| GET | `/cookbooks/stats` | Required | 1000/hour | Get cookbook stats |
| GET | `/cookbooks/search/google-books` | Required | 1000/hour | Search Google Books |
| POST | `/cookbooks/from-google-books` | Required | 100/hour | Create from Google Books |
| GET | `/cookbooks/search/google-books/isbn/<isbn>` | Required | 1000/hour | Search by ISBN |

---

## Recipe Group Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | `/recipe-groups` | Required | 1000/hour | List all groups |
| POST | `/recipe-groups` | Required | 100/hour | Create group |
| GET | `/recipe-groups/<id>` | Required | 1000/hour | Get group details |
| PUT | `/recipe-groups/<id>` | Required | 100/hour | Update group |
| DELETE | `/recipe-groups/<id>` | Required | 100/hour | Delete group |
| POST | `/recipe-groups/<id>/recipes/<r_id>` | Required | 100/hour | Add recipe to group |
| DELETE | `/recipe-groups/<id>/recipes/<r_id>` | Required | 100/hour | Remove from group |
| POST | `/recipe-groups/system/<type>/recipes/<r_id>/toggle` | Required | 100/hour | Toggle system group |
| GET | `/recipe-groups/system/status/<r_id>` | Required | 1000/hour | Get system group status |

**System Groups:**
- `have_made` - Recipes user has cooked
- `want_to_make` - Recipes user wants to try

---

## Public Endpoints (No Auth Required)

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | `/public/recipes` | None | 1000/hour | Browse public recipes |
| GET | `/public/recipes/<id>` | None | 1000/hour | Get public recipe |
| GET | `/public/recipes/featured` | None | 1000/hour | Get featured recipes |
| GET | `/public/users/<id>/recipes` | None | 1000/hour | User's public recipes |
| GET | `/public/cookbooks` | None | 1000/hour | Browse public cookbooks |
| GET | `/public/cookbooks/<id>` | None | 1000/hour | Get public cookbook |
| GET | `/public/cookbooks/<id>/recipes` | None | 1000/hour | Cookbook's recipes |
| GET | `/public/stats` | None | 1000/hour | Platform statistics |

---

## Export Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | `/recipes/<id>/export/pdf` | Required | 100/hour | Export recipe as PDF |
| GET | `/cookbooks/<id>/export/pdf` | Required | 100/hour | Export cookbook as PDF |
| POST | `/cookbooks/<id>/export/print` | Required | 100/hour | Export for printing |

---

## Payment Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| POST | `/payments/subscription/upgrade` | Required | 100/hour | Create subscription |
| POST | `/payments/cookbook/<id>/purchase` | Required | 100/hour | Purchase cookbook |
| POST | `/payments/webhook` | None* | - | Stripe webhook |

*Stripe webhooks are verified via signature

---

## Print Order Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | `/print-orders/specifications` | Required | 1000/hour | Get print specs |
| POST | `/print-orders` | Required | 100/hour | Create print order |
| GET | `/print-orders/<id>` | Required | 1000/hour | Get order details |
| PUT | `/print-orders/<id>` | Required | 100/hour | Update order |
| DELETE | `/print-orders/<id>` | Required | 100/hour | Cancel order |
| GET | `/print-orders/<id>/status` | Required | 5000/hour | Get order status |
| POST | `/print-webhooks/lulu` | None* | - | Lulu webhook |

*Lulu webhooks are verified via signature

---

## System Endpoints (Admin Only)

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | `/system/metrics` | Admin | 1000/hour | System metrics (CPU, memory) |

---

## Health Check

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | `/health` | None | - | Health check endpoint |

---

## Query Parameters Reference

### Pagination (Most list endpoints)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `per_page` | integer | 10 | Items per page (max: 100) |

### Recipe Filtering

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search title/description |
| `cookbook_id` | integer | Filter by cookbook |
| `filter` | string | `mine`, `collection`, `discover` |
| `difficulty` | string | `easy`, `medium`, `hard` |
| `sort_by` | string | `title`, `created_at`, `updated_at` |
| `include_images` | boolean | Include image data |
| `include_notes` | boolean | Include user notes |

### Cookbook Filtering

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search title/author |
| `sort_by` | string | `title`, `recipe_count`, `created_at` |

---

## See Also

- [API Overview](overview.md) - Authentication and patterns
- [Error Codes Reference](error-codes.md) - Error handling
- [Authentication Endpoints](authentication-endpoints.md) - Auth details
- [Recipe Endpoints](recipes-endpoints.md) - Recipe operations

---

[Back to API Reference](README.md) | [Back to Documentation Home](../README.md)

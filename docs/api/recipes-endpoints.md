# Recipe Endpoints

**Tags:** `api`, `recipes`, `crud`, `ocr`, `upload`, `images`
**Last updated:** 2025-11-14

Complete reference for recipe management, OCR processing, and image handling.

---

## Table of Contents

- [List Recipes](#list-recipes)
- [Get Recipe](#get-recipe)
- [Create Recipe](#create-recipe)
- [Update Recipe](#update-recipe)
- [Delete Recipe](#delete-recipe)
- [Upload for OCR Processing](#upload-for-ocr-processing)
- [Check Processing Status](#check-processing-status)
- [Recipe Components](#recipe-components)
  - [Update Ingredients](#update-ingredients)
  - [Update Instructions](#update-instructions)
  - [Update Tags](#update-tags)
- [Recipe Images](#recipe-images)
- [Recipe Privacy](#recipe-privacy)
- [Recipe Collections](#recipe-collections)

---

## List Recipes

Get a paginated list of recipes with filtering options.

**Endpoint:** `GET /api/recipes`

**Authentication:** Required

### Query Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `page` | integer | Page number | 1 |
| `per_page` | integer | Items per page (max 100) | 10 |
| `search` | string | Search by title/description | - |
| `cookbook_id` | integer | Filter by cookbook | - |
| `filter` | string | `mine`, `collection`, or `discover` | `mine` |

### Filter Options

- **`mine`**: Only recipes owned by current user
- **`collection`**: Recipes saved to user's collection
- **`discover`**: Browse public recipes from all users

### Success Response

**Status:** 200 OK

```json
{
  "recipes": [
    {
      "id": 1,
      "title": "Chocolate Chip Cookies",
      "description": "Classic chocolate chip cookies",
      "prep_time": 15,
      "cook_time": 12,
      "servings": 24,
      "difficulty": "easy",
      "is_public": true,
      "published_at": "2025-11-01T10:00:00Z",
      "user_id": 1,
      "cookbook_id": 5,
      "page_number": 42,
      "images": [
        {
          "id": 10,
          "url": "https://cloudinary.com/.../recipe.jpg",
          "is_primary": true
        }
      ],
      "tags": ["dessert", "cookies", "chocolate"],
      "created_at": "2025-11-01T09:00:00Z",
      "updated_at": "2025-11-01T10:00:00Z"
    }
  ],
  "total": 150,
  "pages": 15,
  "current_page": 1,
  "per_page": 10,
  "has_next": true,
  "has_prev": false
}
```

### Example

```bash
# Get my recipes
curl -X GET "http://localhost:5001/api/recipes?filter=mine&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search for chocolate recipes
curl -X GET "http://localhost:5001/api/recipes?search=chocolate" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get recipes in a specific cookbook
curl -X GET "http://localhost:5001/api/recipes?cookbook_id=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Get Recipe

Retrieve a specific recipe with all details.

**Endpoint:** `GET /api/recipes/<recipe_id>`

**Authentication:** Required

### Success Response

**Status:** 200 OK

```json
{
  "id": 1,
  "title": "Chocolate Chip Cookies",
  "description": "Classic chocolate chip cookies with a crispy edge and chewy center",
  "prep_time": 15,
  "cook_time": 12,
  "servings": 24,
  "difficulty": "easy",
  "is_public": true,
  "published_at": "2025-11-01T10:00:00Z",
  "user_id": 1,
  "cookbook_id": 5,
  "page_number": 42,
  "ingredients": [
    {
      "id": 1,
      "name": "All-purpose flour",
      "quantity": "2",
      "unit": "cups",
      "preparation": "sifted",
      "category": "Dry Ingredients",
      "optional": false,
      "position": 0
    },
    {
      "id": 2,
      "name": "Butter",
      "quantity": "1",
      "unit": "cup",
      "preparation": "softened",
      "category": "Wet Ingredients",
      "optional": false,
      "position": 1
    }
  ],
  "instructions": [
    {
      "id": 1,
      "step_number": 1,
      "instruction": "Preheat oven to 375°F (190°C)",
      "image_url": null
    },
    {
      "id": 2,
      "step_number": 2,
      "instruction": "Mix flour and baking soda in a bowl",
      "image_url": "https://cloudinary.com/.../step2.jpg"
    }
  ],
  "images": [
    {
      "id": 10,
      "url": "https://cloudinary.com/.../recipe.jpg",
      "is_primary": true,
      "created_at": "2025-11-01T09:30:00Z"
    }
  ],
  "tags": ["dessert", "cookies", "chocolate"],
  "created_at": "2025-11-01T09:00:00Z",
  "updated_at": "2025-11-01T10:00:00Z"
}
```

### Error Responses

**404 Not Found**
```json
{
  "error": "Recipe not found"
}
```

**403 Forbidden** - Private recipe, not owned by user
```json
{
  "error": "You do not have permission to access this resource"
}
```

### Example

```bash
curl -X GET http://localhost:5001/api/recipes/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Create Recipe

Create a new empty recipe.

**Endpoint:** `POST /api/recipes`

**Authentication:** Required

**Upload Limit:** Free tier limited to 10 recipes/month

### Request Body

```json
{
  "title": "New Recipe",
  "cookbook_id": 5    // Optional
}
```

### Success Response

**Status:** 201 Created

```json
{
  "message": "Recipe created successfully",
  "recipe": {
    "id": 123,
    "title": "New Recipe",
    "user_id": 1,
    "cookbook_id": 5,
    "is_public": false,
    "created_at": "2025-11-14T12:00:00Z"
  }
}
```

### Error Responses

**429 Too Many Requests** - Upload limit exceeded (free tier)
```json
{
  "error": "Upload limit exceeded. You have used 10 out of 10 uploads this month."
}
```

### Example

```bash
curl -X POST http://localhost:5001/api/recipes \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "New Recipe",
    "cookbook_id": 5
  }'
```

---

## Update Recipe

Update recipe metadata.

**Endpoint:** `PUT /api/recipes/<recipe_id>`

**Authentication:** Required (owner or admin)

### Request Body

```json
{
  "title": "Updated Recipe Title",
  "description": "New description",
  "prep_time": 20,
  "cook_time": 30,
  "servings": 4,
  "difficulty": "medium"
}
```

**Note:** All fields are optional. Only provided fields will be updated.

### Difficulty Options

- `easy`
- `medium`
- `hard`

### Success Response

**Status:** 200 OK

```json
{
  "message": "Recipe updated successfully",
  "recipe": {
    "id": 1,
    "title": "Updated Recipe Title",
    "description": "New description",
    "prep_time": 20,
    "cook_time": 30,
    "servings": 4,
    "difficulty": "medium",
    "updated_at": "2025-11-14T12:00:00Z"
  }
}
```

### Example

```bash
curl -X PUT http://localhost:5001/api/recipes/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Recipe",
    "difficulty": "medium",
    "servings": 6
  }'
```

---

## Delete Recipe

Delete a recipe and all associated data.

**Endpoint:** `DELETE /api/recipes/<recipe_id>`

**Authentication:** Required (owner or admin)

**Warning:** This action is irreversible. All images, ingredients, and instructions will be deleted.

### Success Response

**Status:** 200 OK

```json
{
  "message": "Recipe deleted successfully"
}
```

### Example

```bash
curl -X DELETE http://localhost:5001/api/recipes/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Upload for OCR Processing

Upload a recipe image for OCR text extraction and AI parsing.

**Endpoint:** `POST /api/recipes/upload`

**Authentication:** Required

**Rate Limit:** 10 uploads / hour

**Max File Size:** 8 MB

**Supported Formats:** PNG, JPG, JPEG, GIF, BMP, TIFF, WebP

### Request (Multipart Form Data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | Yes | Recipe image file |
| `cookbook_id` | integer | No | Cookbook to add recipe to |
| `page_number` | integer | No | Page number in cookbook |
| `create_new_cookbook` | boolean | No | Create new cookbook |
| `new_cookbook_title` | string | Conditional | Required if `create_new_cookbook=true` |

### Success Response

**Status:** 201 Created

```json
{
  "message": "Image uploaded successfully. Processing started.",
  "job_id": "abc123-def456",
  "image_id": 789,
  "image": {
    "id": 789,
    "url": "https://cloudinary.com/.../recipe.jpg",
    "thumbnail_url": "https://cloudinary.com/.../thumb.jpg"
  },
  "cookbook": {
    "id": 5,
    "title": "My Cookbook"
  },
  "status": "processing",
  "processing_info": {
    "stage": "ocr",
    "message": "Extracting text from image..."
  },
  "status_url": "/api/recipes/job-status/abc123-def456"
}
```

### Processing Stages

1. **upload** - Image uploaded to Cloudinary
2. **ocr** - Text extraction from image
3. **parsing** - AI parsing of recipe text
4. **completed** - Recipe created with parsed data

### Error Responses

**400 Bad Request** - File too large
```json
{
  "error": "File size exceeds 8MB limit"
}
```

**400 Bad Request** - Invalid file type
```json
{
  "error": "Invalid file type. Allowed: PNG, JPG, JPEG, GIF, BMP, TIFF, WebP"
}
```

**429 Too Many Requests** - Upload limit exceeded
```json
{
  "error": "Upload limit exceeded"
}
```

### Example

```bash
curl -X POST http://localhost:5001/api/recipes/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@/path/to/recipe.jpg" \
  -F "cookbook_id=5" \
  -F "page_number=42"
```

### Upload Text Instead of Image

**Endpoint:** `POST /api/recipes/upload-text`

For pasting recipe text directly instead of uploading an image.

```bash
curl -X POST http://localhost:5001/api/recipes/upload-text \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Chocolate Chip Cookies\n\nIngredients:\n2 cups flour\n...",
    "cookbook_id": 5
  }'
```

---

## Check Processing Status

Check the status of an OCR processing job.

**Endpoint:** `GET /api/recipes/job-status/<job_id>`

**Authentication:** Required

**Rate Limit:** 60 requests / minute

### Success Response

**Status:** 200 OK

**While Processing:**
```json
{
  "job": {
    "job_id": "abc123-def456",
    "status": "processing",
    "stage": "parsing",
    "progress": 75,
    "message": "Parsing recipe ingredients and instructions...",
    "created_at": "2025-11-14T12:00:00Z"
  },
  "recipe": null
}
```

**When Completed:**
```json
{
  "job": {
    "job_id": "abc123-def456",
    "status": "completed",
    "progress": 100,
    "message": "Recipe created successfully",
    "completed_at": "2025-11-14T12:05:00Z"
  },
  "recipe": {
    "id": 123,
    "title": "Chocolate Chip Cookies",
    "ingredients": [...],
    "instructions": [...]
  }
}
```

**If Failed:**
```json
{
  "job": {
    "job_id": "abc123-def456",
    "status": "failed",
    "error_message": "Could not extract text from image",
    "failed_at": "2025-11-14T12:03:00Z"
  },
  "recipe": null
}
```

### Job Statuses

- **pending**: Job queued, not started yet
- **processing**: Currently processing
- **completed**: Successfully completed
- **failed**: Processing failed

### Example

```bash
curl -X GET http://localhost:5001/api/recipes/job-status/abc123-def456 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Recipe Components

### Update Ingredients

Replace all ingredients for a recipe.

**Endpoint:** `PUT /api/recipes/<recipe_id>/ingredients`

**Authentication:** Required (owner or admin)

#### Request Body

```json
{
  "ingredients": [
    {
      "name": "All-purpose flour",
      "quantity": "2",
      "unit": "cups",
      "preparation": "sifted",
      "category": "Dry Ingredients",
      "optional": false
    },
    {
      "name": "Chocolate chips",
      "quantity": "2",
      "unit": "cups",
      "category": "Mix-ins",
      "optional": true
    }
  ]
}
```

#### Ingredient Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Ingredient name |
| `quantity` | string | No | Amount (e.g., "2", "1/2") |
| `unit` | string | No | Unit (cups, tbsp, etc.) |
| `preparation` | string | No | Prep note (chopped, diced) |
| `category` | string | No | Group (Dry, Wet, etc.) |
| `optional` | boolean | No | Is ingredient optional |

#### Success Response

**Status:** 200 OK

```json
{
  "message": "Ingredients updated successfully",
  "recipe": {
    "id": 1,
    "ingredients": [...]
  }
}
```

#### Example

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

### Update Instructions

Replace all instructions for a recipe.

**Endpoint:** `PUT /api/recipes/<recipe_id>/instructions`

**Authentication:** Required (owner or admin)

#### Request Body

```json
{
  "instructions": [
    "Preheat oven to 375°F (190°C)",
    "Mix dry ingredients in a large bowl",
    "Cream butter and sugar until fluffy",
    "Combine wet and dry ingredients",
    "Drop spoonfuls onto baking sheet",
    "Bake for 10-12 minutes"
  ]
}
```

**Note:** Array order determines step numbers. Existing instruction images are preserved.

#### Success Response

**Status:** 200 OK

```json
{
  "message": "Instructions updated successfully",
  "recipe": {
    "id": 1,
    "instructions": [
      {
        "id": 1,
        "step_number": 1,
        "instruction": "Preheat oven to 375°F (190°C)",
        "image_url": null
      }
    ]
  }
}
```

#### Example

```bash
curl -X PUT http://localhost:5001/api/recipes/1/instructions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": [
      "Step 1",
      "Step 2",
      "Step 3"
    ]
  }'
```

### Update Tags

Replace all tags for a recipe.

**Endpoint:** `PUT /api/recipes/<recipe_id>/tags`

**Authentication:** Required (owner or admin)

#### Request Body

```json
{
  "tags": ["dessert", "cookies", "chocolate", "baking"]
}
```

#### Success Response

**Status:** 200 OK

```json
{
  "message": "Tags updated successfully",
  "recipe": {
    "id": 1,
    "tags": ["dessert", "cookies", "chocolate", "baking"]
  }
}
```

---

## Recipe Images

### Add Image to Recipe

Upload an additional image to a recipe.

**Endpoint:** `POST /api/recipes/<recipe_id>/images`

**Authentication:** Required (owner or admin)

#### Request (Multipart Form Data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | Yes | Image file |
| `is_primary` | boolean | No | Set as primary image |

#### Success Response

**Status:** 201 Created

```json
{
  "message": "Image uploaded successfully",
  "image": {
    "id": 456,
    "url": "https://cloudinary.com/.../image.jpg",
    "thumbnail_url": "https://cloudinary.com/.../thumb.jpg",
    "is_primary": false
  }
}
```

#### Example

```bash
curl -X POST http://localhost:5001/api/recipes/1/images \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@/path/to/image.jpg" \
  -F "is_primary=true"
```

### Add Image to Instruction Step

Add an image to a specific instruction step.

**Endpoint:** `POST /api/recipes/<recipe_id>/instructions/<instruction_id>/image`

**Authentication:** Required (owner or admin)

#### Request (Multipart Form Data)

```
image: (file)
```

#### Success Response

```json
{
  "message": "Image added to instruction",
  "instruction": {
    "id": 2,
    "step_number": 2,
    "instruction": "Mix ingredients",
    "image_url": "https://cloudinary.com/.../step.jpg"
  }
}
```

---

## Recipe Privacy

### Update Privacy Setting

Change recipe visibility.

**Endpoint:** `PUT /api/recipes/<recipe_id>/privacy`

**Authentication:** Required (owner or admin)

#### Request Body

```json
{
  "is_public": true
}
```

#### Success Response

```json
{
  "message": "Recipe privacy updated",
  "recipe": {
    "id": 1,
    "is_public": true
  }
}
```

### Publish Recipe

Publish a recipe publicly (sets is_public=true and records published_at).

**Endpoint:** `POST /api/recipes/<recipe_id>/publish`

**Authentication:** Required (owner or admin)

### Unpublish Recipe

Make a recipe private again.

**Endpoint:** `POST /api/recipes/<recipe_id>/unpublish`

**Authentication:** Required (owner or admin)

---

## Recipe Collections

### Add to Collection

Save another user's public recipe to your collection.

**Endpoint:** `POST /api/recipes/<recipe_id>/add-to-collection`

**Authentication:** Required

#### Success Response

```json
{
  "message": "Recipe added to your collection"
}
```

### Remove from Collection

Remove a recipe from your collection.

**Endpoint:** `DELETE /api/recipes/<recipe_id>/remove-from-collection`

**Authentication:** Required

---

## See Also

- [API Overview](overview.md)
- [Cookbooks Endpoints](cookbooks-endpoints.md)
- [Cloudinary Integration](../integrations/cloudinary.md)
- [Anthropic Claude Integration](../integrations/anthropic-claude.md)

---

[← Back to API Reference](README.md) | [Back to Documentation Home](../README.md)

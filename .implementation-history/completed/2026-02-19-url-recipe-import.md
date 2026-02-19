# URL Recipe Import Feature

**Task ID:** 2026-02-14-1200
**Status:** Completed

## Original Plan

### Overview
Allow users to import recipes from blog posts by pasting a URL. System extracts recipe data using schema.org JSON-LD (preferred) or Claude AI fallback.

---

### Files to Create/Modify

| File | Action |
|------|--------|
| `backend/app/services/url_recipe_service.py` | **Create** - URL fetching and recipe extraction |
| `backend/app/api/recipes.py` | **Modify** - Add `POST /recipes/upload-url` endpoint |
| `frontend/src/components/forms/UploadForm.tsx` | **Modify** - Add URL mode tab |
| `frontend/src/services/recipesApi.ts` | **Modify** - Add `uploadRecipeUrl()` method |
| `frontend/src/pages/UploadPage.tsx` | **Modify** - Handle URL mode submission |
| `pyproject.toml` | **Modify** - Add `beautifulsoup4` dependency |

---

### Step 1: Add Dependency

Add to `pyproject.toml` dependencies:
```
beautifulsoup4>=4.12.0
```

---

### Step 2: Create URL Recipe Service

**File:** `backend/app/services/url_recipe_service.py`

```python
class UrlRecipeService:
    def import_from_url(self, url: str) -> Dict:
        """Main entry - fetch URL and extract recipe"""

    def _validate_url(self, url: str) -> str:
        """Validate URL format, block private IPs (SSRF prevention)"""

    def _fetch_page(self, url: str) -> str:
        """Fetch with browser User-Agent, 15s timeout, 5MB limit"""

    def _extract_json_ld_recipe(self, html: str) -> Optional[Dict]:
        """Parse <script type="application/ld+json"> for @type: Recipe"""

    def _extract_recipe_with_claude(self, html: str, url: str) -> Dict:
        """Fallback: Clean HTML and use RecipeParser.parse_recipe_text()"""

    def _parse_iso_duration(self, duration: str) -> Optional[int]:
        """Convert PT30M to 30 minutes"""
```

**Key extraction logic:**
1. Fetch URL with requests
2. Parse HTML with BeautifulSoup
3. Look for JSON-LD with `@type: Recipe`
4. Map schema.org fields:
   - `name` → `title`
   - `recipeIngredient[]` → `ingredients`
   - `recipeInstructions` → `instructions` (handle HowToStep objects)
   - `prepTime/cookTime` (ISO 8601) → minutes
   - `recipeYield` → `servings`
5. If no JSON-LD: strip nav/ads, extract main content, send to Claude

**Redis caching:** Cache by URL hash, 24h TTL

---

### Step 3: Add API Endpoint

**File:** `backend/app/api/recipes.py`

Add endpoint `POST /recipes/upload-url`:

```python
@bp.route("/recipes/upload-url", methods=["POST"])
@require_auth
def upload_recipe_url(current_user):
    """Import recipe from URL."""
```

**Request:**
```json
{
  "url": "https://example.com/chocolate-chip-cookies",
  "cookbook_id": 123,
  "create_new_cookbook": false,
  "translate_to_english": false
}
```

**Response:**
```json
{
  "recipe": { ... },
  "message": "Recipe imported successfully",
  "extraction_method": "json_ld" | "claude",
  "source_url": "https://..."
}
```

**Implementation:**
1. Validate JSON payload
2. Check upload limit (free tier)
3. Handle cookbook creation/linking (reuse existing pattern)
4. Call `UrlRecipeService.import_from_url(url)`
5. Create Recipe with `is_original_recipe=False`, `source=url`
6. Create Ingredients, Instructions, Tags
7. Return recipe response

---

### Step 4: Frontend - API Service

**File:** `frontend/src/services/recipesApi.ts`

Add method:
```typescript
async uploadRecipeUrl(url: string, formData: UploadFormData): Promise<any> {
  const payload = {
    url,
    cookbook_id: formData.cookbook_id,
    create_new_cookbook: formData.create_new_cookbook,
    new_cookbook_title: formData.new_cookbook_title,
    translate_to_english: formData.translate_to_english,
  };

  const response = await apiFetch(`${this.baseUrl}/recipes/upload-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return response.json();
}
```

---

### Step 5: Frontend - Upload Form

**File:** `frontend/src/components/forms/UploadForm.tsx`

1. Add URL mode to upload type selector (alongside Image/Text)
2. Add URL input field when URL mode selected:
   - Placeholder: "https://example.com/recipe-page"
   - URL validation
3. Auto-set `is_original_recipe: false` for URL imports
4. Show info: "Recipes from URLs are for personal use only"

**File:** `frontend/src/pages/UploadPage.tsx`

Handle URL mode in `handleUpload`:
```typescript
if (formData.isUrlMode && formData.recipeUrl) {
  const result = await recipesApi.uploadRecipeUrl(formData.recipeUrl, formData);
  // handle success/error
}
```

---

### Error Handling

| Scenario | Error | User Message |
|----------|-------|--------------|
| Invalid URL | `UrlValidationError` | "Please enter a valid URL" |
| 403/blocked | `BotProtectionError` | "This site blocked our request. Try copying the recipe text instead." |
| 404 | `UrlFetchError` | "Page not found. Please check the URL." |
| Timeout | `UrlFetchError` | "Request timed out. The site may be slow." |
| No recipe found | `RecipeNotFoundError` | "No recipe found on this page. Try the text input instead." |

---

### Security

1. **SSRF Prevention:** Block private IPs (10.x, 192.168.x, 127.x, etc.)
2. **Rate Limiting:** Add to existing rate limiter
3. **Content Limits:** Max 5MB response, 15s timeout
4. **Sanitization:** Don't store raw HTML

---

### Verification

1. **Unit tests:** Test JSON-LD extraction with sample HTML
2. **Integration test:** Import from popular recipe sites:
   - AllRecipes.com (has JSON-LD)
   - SeriousEats.com (has JSON-LD)
   - Random WordPress recipe blog
3. **Manual test:**
   - Run `make dev`
   - Go to Upload page
   - Select URL mode
   - Paste recipe URL
   - Verify recipe created with correct ingredients/instructions
   - Verify `source` field shows original URL
   - Verify `is_original_recipe` is false

## Timeline
- Started: 2026-02-14T12:00:00Z
- Completed: 2026-02-19T12:00:00Z

## Deviations
- 2026-02-14T12:30:00Z: Added front page advertising for URL import feature (updated HomePage.tsx feature cards, Import & Create section, and OnboardingModal.tsx) - user requested
- 2026-02-14T12:45:00Z: Added "Import from URL" option to Header.tsx dropdown menu (desktop and mobile) - user requested
- 2026-02-14T12:50:00Z: Added `?mode=url` query parameter support to UploadPage.tsx and `initialMode` prop to UploadForm.tsx to allow deep linking directly to URL mode

## Results Summary
Successfully implemented URL recipe import feature allowing users to paste recipe URLs and have them automatically extracted and saved.

**Files Created:**
- `backend/app/services/url_recipe_service.py` - URL fetching, JSON-LD extraction, Claude AI fallback

**Files Modified:**
- `backend/app/api/recipes.py` - Added `POST /recipes/upload-url` endpoint
- `frontend/src/services/recipesApi.ts` - Added `uploadRecipeUrl()` method
- `frontend/src/components/forms/UploadForm.tsx` - Added URL mode tab with input field
- `frontend/src/pages/UploadPage.tsx` - Handle URL mode submission and `?mode=url` query param
- `frontend/src/types/index.ts` - Added `isUrlMode` and `recipeUrl` to UploadFormData
- `frontend/src/components/layout/Header.tsx` - Added "Import from URL" to dropdown menus
- `frontend/src/pages/HomePage.tsx` - Updated marketing copy for URL import
- `frontend/src/components/onboarding/OnboardingModal.tsx` - Updated onboarding text
- `pyproject.toml` - Added `beautifulsoup4` dependency

**Key Features:**
- Schema.org JSON-LD extraction (preferred method)
- Claude AI fallback for pages without structured data
- SSRF prevention (blocks private IPs)
- Redis caching (24h TTL)
- Deep linking via `?mode=url` query parameter
- Auto-sets `is_original_recipe: false` for copyright compliance

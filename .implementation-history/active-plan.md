# Add Food Photo as Primary Image Feature

**Task ID:** 2026-02-06-1430
**Status:** In Progress

## Original Plan

### Overview
Allow recipe owners to easily add a food photo (actual dish photo) that becomes the primary display image, pushing the original recipe scans to secondary positions.

**Existing Infrastructure:**
- `RecipeImage` model has `image_order` field (lower = primary)
- `RecipeImageCarousel` sorts by `image_order`
- `cameraService.ts` handles Capacitor Camera on mobile
- `isNativePlatform()` utility for platform detection
- `canEdit` flag already computed in RecipeDetailPage

---

### Backend Changes

#### File: `backend/app/api/recipes.py`

Add new endpoint after line ~1222 (after existing upload endpoint):

**POST `/recipes/:id/images/primary`**
- Shifts all existing images' `image_order` up by 1
- Uploads new image with `image_order = 0` (becomes primary)
- Returns updated recipe with all images

```python
@bp.route("/recipes/<int:recipe_id>/images/primary", methods=["POST"])
@require_auth
def upload_primary_recipe_image(current_user, recipe_id: int):
    # 1. Verify recipe exists and user owns it
    # 2. Validate file upload
    # 3. Shift all existing images: image_order += 1
    # 4. Process and save new image with image_order = 0
    # 5. Return recipe with updated images
```

---

### Frontend Changes

#### 1. API Method

**File**: `frontend/src/services/recipesApi.ts`

Add after `uploadRecipeImage()`:
```typescript
async uploadPrimaryRecipeImage(recipeId: number, imageFile: File): Promise<{message: string; image: any; recipe: Recipe}>
```

#### 2. New Component

**File**: `frontend/src/components/recipe/AddFoodPhotoButton.tsx` (CREATE)

- Camera icon button with "Add Food Photo" text
- On mobile: uses `captureRecipePhoto()` from cameraService
- On web: opens file picker
- Shows spinner during upload
- Validates file type and size (5MB max)
- Invalidates recipe cache on success

#### 3. Integrate into Carousel

**File**: `frontend/src/components/recipe/RecipeImageCarousel.tsx`

- Add `canEdit` prop to interface
- Import and render `AddFoodPhotoButton` below thumbnails when `canEdit` is true

#### 4. Pass canEdit Prop

**File**: `frontend/src/pages/RecipeDetailPage.tsx`

- Add `canEdit={canEdit}` to RecipeImageCarousel (line ~359)

---

### File Summary

| File | Action |
|------|--------|
| `backend/app/api/recipes.py` | Add primary image upload endpoint |
| `frontend/src/services/recipesApi.ts` | Add API method |
| `frontend/src/components/recipe/AddFoodPhotoButton.tsx` | Create component |
| `frontend/src/components/recipe/RecipeImageCarousel.tsx` | Add button + canEdit prop |
| `frontend/src/pages/RecipeDetailPage.tsx` | Pass canEdit prop |

---

### Verification

1. **Web upload**: View own recipe → Click "Add Food Photo" → Select file → Verify it appears first
2. **Mobile camera**: On iOS/Android → Click button → Camera/picker opens → Take/select photo → Verify upload
3. **Order check**: Original recipe images should now be in positions 2, 3, etc.
4. **Recipe cards**: Navigate to recipes list → Verify new photo shows on card
5. **Non-owner**: View someone else's recipe → Button should NOT appear
6. **Error handling**: Try uploading invalid file type → Should show error

## Timeline
- Started: 2026-02-06T14:30:00Z
- Completed:

## Deviations
- 2026-02-06T14:35:00Z: Added `traceback` import to recipes.py for better error logging with full stack traces (not explicitly in plan but follows CLAUDE.md requirement for exception logging)
- 2026-02-06T14:45:00Z: Changed button styling from `bg-accent` class to inline style `backgroundColor: '#f15f1c'` to match project's Button component pattern - the accent class wasn't rendering correctly
- 2026-02-06T14:50:00Z: Added `db.session.flush()` after shifting existing image orders and `db.session.expire(recipe, ['images'])` after commit to ensure proper ordering when returning updated recipe data
- 2026-02-06T17:10:00Z: Fixed JavaScript falsy bug in RecipeImageCarousel sorting - changed `||` to `??` (nullish coalescing) so `image_order=0` is handled correctly instead of falling back to `id`

## Results Summary
[To be added on completion]

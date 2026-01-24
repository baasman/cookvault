# Recipe Privacy & Copyright Protection

**Task ID:** 2026-01-22-1845
**Status:** Completed

## Original Plan

### Overview
Protect against copyright issues by restricting which recipes can be made public:
- Recipes from Google Books cookbooks → **Never publishable** (only viewable by uploader)
- Recipes from user-created cookbooks → **Publishable**
- Standalone recipes → **Depends on source** (ask user at upload if it's their own recipe)

Replace the confusing 4-checkbox copyright consent at upload with a simple source question.

### Implementation

1. **Database Migration** - Add `is_original_recipe` field to Recipe, ProcessingJob, and MultiRecipeJob models
2. **Backend Model Changes** - Add `can_be_published()` method to Recipe model
3. **Backend API Changes** - Update upload endpoints and privacy toggle to check publishability
4. **Frontend Upload Form** - Replace 4 copyright checkboxes with recipe source radio buttons
5. **Frontend Publish Flow** - Update MakePublicButton to check publishability
6. **Frontend Recipe Display** - Show publish restriction indicators

## Timeline
- Started: 2026-01-22T18:45:00Z
- Completed: 2026-01-22T19:15:00Z

## Deviations
- 2026-01-22T19:10:00Z: Added requirement that if user selects "from a cookbook", they must actually link it to a cookbook. This prevents users from selecting "from a cookbook" while using "No cookbook" option to avoid the requirement.

## Results Summary

Successfully implemented recipe privacy and copyright protection system.

### Files Created
- `backend/migrations/versions/c1d2e3f4g5h6_add_is_original_recipe.py` - Database migration

### Files Modified

**Backend:**
- `backend/app/models/recipe.py` - Added `is_original_recipe` field and `can_be_published()` method
- `backend/app/api/recipes.py` - Updated upload endpoints and privacy toggle

**Frontend:**
- `frontend/src/types/index.ts` - Added new type fields
- `frontend/src/components/forms/UploadForm.tsx` - Replaced copyright checkboxes with recipe source selection
- `frontend/src/components/recipe/MakePublicButton.tsx` - Added publishability check
- `frontend/src/pages/RecipeDetailPage.tsx` - Added publish restriction notice
- `frontend/src/pages/UploadPage.tsx` - Updated to pass is_original_recipe
- `frontend/src/services/recipesApi.ts` - Updated upload methods

### Key Behaviors Implemented
1. Recipes from Google Books cookbooks automatically cannot be made public
2. Users select whether their recipe is original or from a source at upload time
3. "From a cookbook" selection requires linking to an actual cookbook
4. Non-publishable recipes show "Personal Only" button instead of "Make Public"
5. Recipe detail page shows a notice explaining publish restrictions
6. Existing recipes default to publishable for backwards compatibility

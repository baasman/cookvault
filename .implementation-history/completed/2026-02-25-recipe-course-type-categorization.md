# Recipe Course Type Categorization

**Task ID:** 2026-02-25-1200
**Status:** In Progress

## Original Plan

### Overview
Add a `course_type` field to recipes (Appetizer, Main Course, Dessert, etc.) that is:
- Automatically inferred by Claude during recipe parsing
- Filterable in the recipes page UI
- Optional/nullable (existing recipes remain unaffected)

### Course Types
```
Appetizer, Soup, Salad, Main Course, Side Dish, Bread, Dessert, Beverage, Sauce/Condiment, Snack
```

---

### Files to Modify

| File | Change |
|------|--------|
| `backend/migrations/versions/` | New migration for `course_type` column |
| `backend/app/models/recipe.py` | Add `course_type` field + update `to_dict()` |
| `backend/app/services/recipe_parser.py` | Update 3 LLM prompts to extract course_type |
| `backend/app/services/url_recipe_service.py` | Map JSON-LD `recipeCategory` to course_type |
| `backend/app/api/recipes.py` | Add to recipe creation (3 places) + filtering |
| `frontend/src/types/index.ts` | Add `course_type` to Recipe interface |
| `frontend/src/services/recipesApi.ts` | Add `courseType` param to fetch functions |
| `frontend/src/pages/RecipesPage.tsx` | Add course type filter dropdown |

---

### Implementation Steps

1. Database Migration - Create `course_type` column with index
2. Recipe Model - Add field and update `to_dict()`
3. LLM Prompts - Update all 3 prompt builders to extract course_type
4. URL Recipe Service - Map JSON-LD `recipeCategory` to course_type
5. Recipe Creation - Add `course_type` to all recipe creation endpoints
6. Backend Filtering - Add course_type filtering to get_recipes
7. Frontend Types - Add `course_type` to Recipe interface and COURSE_TYPES constant
8. Frontend API - Add `courseType` param to fetch functions
9. Frontend Filter UI - Add course type filter dropdown

---

## Timeline
- Started: 2026-02-25T12:00:00Z
- Completed: 2026-02-25T15:38:00Z

## Deviations
None.

## Results Summary
Successfully implemented recipe course type categorization:

**Database:**
- Created migration `i7j8k9l0m1n2_add_course_type.py` adding `course_type` column with index

**Backend:**
- Added `course_type` field to Recipe model in `backend/app/models/recipe.py`
- Updated `to_dict()` to include `course_type`
- Updated 3 LLM prompts in `recipe_parser.py` to extract course_type
- Added JSON-LD `recipeCategory` mapping in `url_recipe_service.py`
- Added `course_type` to recipe creation in `_create_recipe_from_parsed_data`, `upload_recipe_text`, and `upload_recipe_url`
- Added `course_type` filtering in `get_recipes` and `discover_recipes` endpoints

**Frontend:**
- Added `COURSE_TYPES` constant and `CourseType` type in `frontend/src/types/index.ts`
- Added `course_type` to `Recipe` interface
- Added `courseType` param to `FetchRecipesParams` and both fetch functions in `recipesApi.ts`
- Added course type dropdown filter to `RecipesPage.tsx`

**Migration verified:** Successfully ran `flask db upgrade`

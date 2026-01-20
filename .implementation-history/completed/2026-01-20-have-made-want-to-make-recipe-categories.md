# Add "Have Made" and "Want to Make" Recipe Categories

**Task ID:** 2026-01-20-0830
**Status:** Completed

## Original Plan

Add two default system recipe groups for all users with quick-toggle buttons on the recipe detail page.

### Approach
Extend the existing recipe groups system with special "system" groups that:
- Are auto-created for each user (lazily, on first access)
- Cannot be deleted or renamed
- Have dedicated quick-toggle buttons

### Implementation Steps
1. Database Changes - Add `is_system` and `system_type` fields to RecipeGroup model
2. Backend API Changes - Add helper function, new endpoints, update existing endpoints
3. Frontend Changes - Update types, add API methods, create button components
4. UI Consolidation - Simplify action buttons with dropdown menu

## Timeline
- Started: 2026-01-20T08:30:00Z
- Completed: 2026-01-20T09:45:00Z

## Deviations
- 2026-01-20T09:30:00Z: Added UI consolidation phase after initial implementation. The recipe detail page had too many buttons (10+), so created a RecipeActionsDropdown component to consolidate secondary actions into a "More" menu.

## Results Summary

Successfully implemented "Have Made" and "Want to Make" system recipe groups with a streamlined UI.

### Backend Changes
- `backend/app/models/recipe.py` - Added `is_system` and `system_type` fields to RecipeGroup, updated Recipe.to_dict() to include `have_made`/`want_to_make` booleans
- `backend/app/api/recipe_groups.py` - Added `ensure_system_groups_exist()` helper, new toggle/status endpoints, protection for system groups
- `backend/migrations/versions/b4c5d6e7f8a9_add_system_group_fields.py` - Database migration
- `backend/scripts/create_system_groups.py` - Data migration script for existing users

### Frontend Changes
- `frontend/src/types/index.ts` - Added system group fields to types
- `frontend/src/services/recipeGroupsApi.ts` - Added `toggleSystemGroup()` and `getSystemGroupStatus()` methods
- `frontend/src/components/recipe/HaveMadeButton.tsx` - New component with icon-only mode
- `frontend/src/components/recipe/WantToMakeButton.tsx` - New component with icon-only mode
- `frontend/src/components/recipe/RecipeActionsDropdown.tsx` - New consolidated actions dropdown
- `frontend/src/components/recipe/RecipeGroupDetail.tsx` - Hide edit/delete for system groups, added "System" badge
- `frontend/src/pages/RecipeDetailPage.tsx` - Updated to use new simplified layout

### Key Outcomes
- System groups are lazily created on first API access
- Desktop toolbar reduced from 10+ buttons to 3 compact controls (Have Made icon, Want to Make icon, More dropdown)
- System groups cannot be modified or deleted (protected by backend)
- Mobile menu unchanged (already worked well as list format)

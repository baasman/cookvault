# Organization & Management Features

**Task ID:** 2026-04-06-1200
**Status:** In Progress

## Original Plan

Cookbook Creator has solid recipe CRUD, groups, and collections — but lacks power-user tools for managing larger libraries. Users with 50+ recipes need bulk actions, backup/portability, and dynamic organization. These three features fill that gap without requiring complex AI or major architectural changes.

### Scope

Three features, implemented in order:
1. **Bulk Operations** — multi-select + batch actions (no DB changes)
2. **Import/Export** — JSON export/import for backup & portability (no DB changes)
3. **Smart Folders** — auto-populating groups from filter rules (1 new table)

### Phase 1: Bulk Operations

**Backend** — `backend/app/api/recipes/bulk.py` (new file)

Endpoints (all POST, auth required, max 50 IDs):
- `POST /api/recipes/bulk/delete` — verify ownership, delete with image cleanup
- `POST /api/recipes/bulk/add-to-group` — verify group ownership + recipe access
- `POST /api/recipes/bulk/remove-from-group` — remove recipes from group
- `POST /api/recipes/bulk/privacy` — toggle privacy (private→public only)
- `POST /api/recipes/bulk/tags` — add/remove/set tags

All use partial-success pattern: `{ "updated": [...], "errors": [...] }`

**Frontend:**
- `useRecipeSelection.ts` hook for selection state
- RecipeCard: add selectable checkbox overlay
- BulkActionToolbar: sticky bottom bar with actions
- BulkDeleteModal, BulkTagModal: confirmation/input modals
- RecipesPage: selection mode toggle, toolbar integration

### Phase 2: Import/Export (JSON)

**Backend** — modify `backend/app/api/exports.py`:
- `GET /api/exports/recipes/<id>/json` — single recipe JSON
- `POST /api/exports/recipes/json` — multi-recipe JSON (max 200)
- `POST /api/imports/recipes/json` — upload + validate + create

New: `backend/app/services/recipe_import_service.py`

**Frontend:**
- ExportButton: add JSON format option
- ImportRecipesModal: file upload + preview + import
- RecipesPage: import button

### Phase 3: Smart Folders

**Backend:**
- SmartFolder model in `backend/app/models/recipe.py`
- `backend/app/services/smart_folder_service.py` — rule → SQLAlchemy filter translation
- `backend/app/api/smart_folders.py` — CRUD + recipe listing + preview

**Frontend:**
- `smartFoldersApi.ts` service
- SmartFolderCard, SmartFolderRuleBuilder, CreateSmartFolderModal components
- SmartFolderDetailPage
- Integration into RecipesPage groups tab

### New Files (13)
- `backend/app/api/recipes/bulk.py`
- `frontend/src/hooks/useRecipeSelection.ts`
- `frontend/src/components/recipe/BulkActionToolbar.tsx`
- `frontend/src/components/recipe/BulkDeleteModal.tsx`
- `frontend/src/components/recipe/BulkTagModal.tsx`
- `backend/app/services/recipe_import_service.py`
- `frontend/src/components/import/ImportRecipesModal.tsx`
- `backend/app/services/smart_folder_service.py`
- `backend/app/api/smart_folders.py`
- `frontend/src/services/smartFoldersApi.ts`
- `frontend/src/components/recipe/SmartFolderCard.tsx`
- `frontend/src/components/recipe/SmartFolderRuleBuilder.tsx`
- `frontend/src/pages/SmartFolderDetailPage.tsx`

### Modified Files (7)
- `backend/app/api/recipes/__init__.py`
- `backend/app/api/exports.py`
- `backend/app/api/__init__.py`
- `backend/app/models/recipe.py`
- `frontend/src/pages/RecipesPage.tsx`
- `frontend/src/components/recipe/RecipeCard.tsx`
- `frontend/src/components/export/ExportButton.tsx`
- `frontend/src/services/recipesApi.ts`
- `frontend/src/App.tsx`

## Timeline
- Started: 2026-04-06T12:00:00Z
- Completed:

## Deviations
None yet.

## Results Summary
[To be added on completion]

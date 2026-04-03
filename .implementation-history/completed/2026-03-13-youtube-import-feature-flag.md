# YouTube Import Feature Flag

**Branch:** `main`
**Started:** 2026-03-13
**Completed:** 2026-03-13

## Status: Complete

## Steps
1. [x] Add YOUTUBE_IMPORT_ENABLED to backend config (backend/app/config.py)
2. [x] Guard upload-youtube API endpoint with feature flag check (backend/app/api/recipes.py)
3. [x] Add /features API endpoint to expose feature flags (backend/app/api/recipes.py)
4. [x] Add getFeatures method to recipesApi (frontend/src/services/recipesApi.ts)
5. [x] Conditionally render YouTube option in UploadForm (frontend/src/components/forms/UploadForm.tsx)

## Verification
- TypeScript: compiles cleanly
- Ruff lint: all checks passed

## Key Design Decisions
- Feature flag defaults to `false` (YouTube import disabled)
- Backend returns 503 when YouTube import is attempted with feature disabled
- Frontend fetches features on mount and hides YouTube toggle when disabled
- Graceful fallback: if features endpoint fails, YouTube import defaults to disabled

## Environment Variable
- **Name:** `YOUTUBE_IMPORT_ENABLED`
- **Default:** `false` (disabled)
- **To enable:** Set to `true` in Render environment variables

## Files Modified
- `backend/app/config.py` — Added YOUTUBE_IMPORT_ENABLED feature flag
- `backend/app/api/recipes.py` — Added /features endpoint + guard on upload-youtube endpoint
- `frontend/src/services/recipesApi.ts` — Added getFeatures method
- `frontend/src/components/forms/UploadForm.tsx` — Conditionally render YouTube option based on feature flag

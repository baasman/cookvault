# YouTube Recipe Import (Hybrid Approach C)

**Branch:** `feature/youtube-recipe-import`
**Started:** 2026-03-05
**Completed:** 2026-03-05

## Status: Complete

## Steps
1. [x] Create branch + add yt-dlp dependency
2. [x] Extend model + enum (VideoProcessingStatus, VideoProcessingJob)
3. [x] Write backend service tests (test_youtube_service.py) — 35 tests
4. [x] Write API endpoint tests (test_youtube_api.py) — 10 tests
5. [x] Implement YouTubeRecipeService
6. [x] Implement Celery task (process_youtube_recipe_task)
7. [x] Implement API endpoint (POST /recipes/upload-youtube)
8. [x] Update frontend types
9. [x] Add frontend API method
10. [x] Update VideoProcessingProgress
11. [x] Update UploadForm — YouTube link toggle
12. [x] Update UploadPage submission

## Verification
- 45/45 tests passing
- Ruff lint: all checks passed
- TypeScript: compiles cleanly

## Key Design Decisions
- Extend VideoProcessingJob model (not a new model)
- 3 new status enum values: FETCHING_METADATA, EXTRACTING_CAPTIONS, DOWNLOADING_AUDIO
- Separate endpoint: POST /recipes/upload-youtube (JSON, not multipart)
- Always async via Celery
- Max duration: 20 minutes
- Two-tier: captions first, audio fallback

## Files Created/Modified
- `pyproject.toml` — added yt-dlp dependency
- `backend/app/models/video_job.py` — 3 new enum values + 3 nullable columns
- `backend/app/services/youtube_recipe_service.py` — NEW: core service
- `backend/app/tasks/recipe_tasks.py` — added process_youtube_recipe_task
- `backend/app/api/recipes.py` — added POST /recipes/upload-youtube
- `backend/tests/test_youtube_service.py` — NEW: 35 service tests
- `backend/tests/test_youtube_api.py` — NEW: 10 API tests
- `frontend/src/types/index.ts` — new status values + fields
- `frontend/src/services/recipesApi.ts` — uploadRecipeYouTube method
- `frontend/src/components/upload/VideoProcessingProgress.tsx` — 3 new status labels
- `frontend/src/components/forms/UploadForm.tsx` — YouTube link toggle in video tab
- `frontend/src/pages/UploadPage.tsx` — YouTube URL submission handling

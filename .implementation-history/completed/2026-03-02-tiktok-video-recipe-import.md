# TikTok/Video Recipe Import Feature

**Task ID:** 2026-02-27-1200
**Status:** Completed

## Original Plan

### Overview

Add the ability to import recipes from cooking videos (TikTok, Instagram Reels saved to camera roll, etc.). Users upload a video file, and the system extracts the recipe using audio transcription + visual analysis.

### User Flow

```
1. User saves TikTok/Reel to camera roll (native app feature)
2. User opens Cookle → Upload → selects "Video" tab
3. User selects video file (MP4/MOV, max 100MB, max 3 min)
4. Upload starts → async processing begins
5. Progress shown: "Extracting audio..." → "Transcribing..." → "Analyzing frames..."
6. ~30-60 seconds later: Recipe ready for review
7. User edits/confirms extracted recipe
8. Save to collection
```

### Technical Architecture

```
┌─────────────┐     ┌─────────────────────────────────────────────────────┐
│   Video     │     │                Backend Processing                    │
│   Upload    │────▶│                                                      │
│  (Frontend) │     │  ┌──────────┐   ┌──────────┐   ┌─────────────────┐  │
└─────────────┘     │  │  FFmpeg  │──▶│ Whisper  │──▶│     Claude      │  │
                    │  │          │   │  (OpenAI)│   │  (combine all)  │  │
                    │  │ Extract: │   │          │   │                 │  │
                    │  │ • Audio  │   │Transcribe│   │ Parse into      │  │
                    │  │ • Frames │   │ speech   │   │ structured      │  │
                    │  └──────────┘   └──────────┘   │ recipe JSON     │  │
                    │       │                        └────────┬────────┘  │
                    │       │                                 │           │
                    │       ▼                                 ▼           │
                    │  ┌──────────┐                    ┌───────────┐      │
                    │  │  Claude  │                    │  Recipe   │      │
                    │  │  Vision  │                    │  Created  │      │
                    │  │ (frames) │                    └───────────┘      │
                    │  └──────────┘                                       │
                    └─────────────────────────────────────────────────────┘
```

### Cost Per Video

| Component | Cost | Notes |
|-----------|------|-------|
| Whisper API | ~$0.006/min | 30-60 sec typical |
| Claude Vision (6 frames) | ~$0.024 | Frame analysis |
| Claude parsing | ~$0.01 | Final structuring |
| **Total** | **~$0.04** | Per video |

---

### Files to Create

1. `backend/app/services/video_processor.py` (NEW)
2. `backend/app/models/video_job.py` (NEW)

### Files to Modify

3. `backend/app/api/recipes.py`
4. `backend/app/tasks/recipe_tasks.py`
5. `backend/requirements.txt` (or pyproject.toml)
6. `frontend/src/components/forms/UploadForm.tsx`
7. `frontend/src/services/recipesApi.ts`
8. `frontend/src/pages/UploadPage.tsx`

### Implementation Order

0. Create feature branch - `git checkout -b feature/video-recipe-import`
1. Backend Model - Create VideoProcessingJob model + migration
2. Backend Service - Create VideoRecipeProcessor with FFmpeg + Whisper + Claude
3. Backend API - Add upload-video and status endpoints
4. Backend Task - Add Celery task for async processing
5. Frontend API - Add recipesApi methods
6. Frontend Form - Add video tab to UploadForm
7. Frontend Page - Handle video upload flow in UploadPage

## Timeline
- Started: 2026-02-27T12:00:00Z
- Completed: 2026-03-02T10:30:00Z

## Deviations
- Added `VideoProcessingProgress.tsx` component (not in original plan) for detailed stage-by-stage progress display
- Added video option to Header dropdown menu for easy access
- Added comprehensive help/guidance section in upload form with TikTok download instructions
- Added FFmpeg to worker Dockerfile for production deployment

## Results Summary

Successfully implemented video recipe import feature. Users can now upload cooking videos (TikTok, Instagram Reels, etc.) and have recipes automatically extracted.

**Files Created:**
- `backend/app/models/video_job.py` - VideoProcessingJob model with granular status tracking
- `backend/app/services/video_processor.py` - Full processing pipeline (FFmpeg + Whisper + Claude Vision)
- `backend/migrations/versions/4c4302aa4669_add_videoprocessingjob_model_for_video_.py` - Database migration
- `frontend/src/components/upload/VideoProcessingProgress.tsx` - Progress UI with stage indicators

**Files Modified:**
- `backend/app/api/recipes.py` - Added upload-video and video-job-status endpoints
- `backend/app/tasks/recipe_tasks.py` - Added process_video_recipe_task Celery task
- `backend/Dockerfile.worker` - Added FFmpeg installation
- `frontend/src/components/forms/UploadForm.tsx` - Added Video tab with drag-drop and help section
- `frontend/src/components/layout/Header.tsx` - Added "Import from Video" to dropdown
- `frontend/src/pages/UploadPage.tsx` - Added video upload flow handling
- `frontend/src/services/recipesApi.ts` - Added video API methods
- `frontend/src/types/index.ts` - Added video-related types
- `pyproject.toml` & `requirements.txt` - Added openai dependency

**Key Features:**
- Video upload with drag-drop support (MP4, MOV, WebM, AVI)
- Async processing via Celery with detailed progress tracking
- Audio transcription via OpenAI Whisper API
- Visual analysis via Claude Vision (6 frames)
- Recipe structuring via Claude
- Constraints: max 100MB, max 3 minutes

**PR:** Merged to main via PR #12

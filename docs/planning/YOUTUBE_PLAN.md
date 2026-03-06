# YouTube Recipe Import (Hybrid Approach C)

**Status:** Implemented
**Branch:** `feature/youtube-recipe-import`
**Completed:** 2026-03-06

## Context

Users can already import recipes from blog URLs (instant, via JSON-LD) and uploaded TikTok videos (30-90s, via Whisper + Claude Vision). YouTube cooking videos are a natural next target. Instead of requiring users to download and re-upload YouTube videos, we use `yt-dlp` server-side. A hybrid two-tier strategy keeps things fast: extract captions when available (most YouTube videos have them), fall back to audio download + Whisper only when needed.

## Design Decisions

1. **Extend VideoProcessingJob model** (not a new model) — add 3 nullable columns: `youtube_url`, `youtube_video_id`, `extraction_method`. Use synthetic values for existing NOT NULL video file columns (e.g., `video_filename="youtube_{id}"`, `video_path="youtube"`) to avoid altering constraints.
2. **Add 3 new status enum values** to `VideoProcessingStatus`: `FETCHING_METADATA`, `EXTRACTING_CAPTIONS`, `DOWNLOADING_AUDIO`. Existing statuses (`TRANSCRIBING`, `PARSING_RECIPE`) are reused.
3. **Separate endpoint**: `POST /recipes/upload-youtube` (accepts JSON, not multipart form-data like video upload).
4. **Always async via Celery** — even the fast caption path goes through Celery for consistent UX and error handling. Reuse `VideoProcessingProgress.tsx` for polling.
5. **Max duration**: 20 minutes (YouTube cooking videos are longer than TikTok's 3 min).

## Architecture

```
User pastes YouTube URL in Video tab
    |
POST /recipes/upload-youtube { url, cookbook_id?, translate_to_english? }
    |
Create VideoProcessingJob (youtube_url + youtube_video_id set)
    |
Queue Celery task: process_youtube_recipe_task
    |
YouTubeRecipeService.process_youtube_url()
    |
    +-> Check Redis cache (key: yt_recipe:{video_id}) -> hit? skip to recipe creation
    |
    +-> FETCHING_METADATA (10%): yt-dlp --dump-json (title, duration, thumbnails, captions info)
    |   Validate: duration <= 1200s, not live, not private
    |
    +-> EXTRACTING_CAPTIONS (30%): yt-dlp --write-sub --skip-download
    |   Try manual captions -> auto-generated captions (prefer English)
    |   IMPORTANT: Use exact lang_code from metadata + glob pattern (en.*)
    |
    +-> Captions found? (TIER 1 - fast, ~5-10s)
    |   YES -> Download thumbnail -> PARSING_RECIPE (70%): transcript + thumbnail -> Claude -> recipe
    |   NO  -> TIER 2 fallback:
    |           DOWNLOADING_AUDIO (40%): yt-dlp -x --audio-format mp3
    |           TRANSCRIBING (60%): Whisper API
    |           Download thumbnail -> PARSING_RECIPE (70%): transcript + thumbnail -> Claude -> recipe
    |
    +-> Cache result in Redis (24h TTL)
    +-> Create Recipe + ingredients/instructions/tags in DB
    +-> COMPLETED (100%)
```

## Files Modified/Created

| File | Action |
|------|--------|
| `pyproject.toml` (root, NOT backend/) | Modify — add `yt-dlp>=2024.1.0` |
| `backend/app/models/video_job.py` | Modify — add 3 enum values + 3 nullable columns |
| `backend/app/services/youtube_recipe_service.py` | **Create** — core service (~940 lines) |
| `backend/app/tasks/recipe_tasks.py` | Modify — add `process_youtube_recipe_task` |
| `backend/app/api/recipes.py` | Modify — add `POST /recipes/upload-youtube` |
| `backend/tests/test_youtube_service.py` | **Create** — 35 service unit tests |
| `backend/tests/test_youtube_api.py` | **Create** — 10 API endpoint tests |
| `frontend/src/types/index.ts` | Modify — add status values + fields |
| `frontend/src/services/recipesApi.ts` | Modify — add `uploadRecipeYouTube` method |
| `frontend/src/components/upload/VideoProcessingProgress.tsx` | Modify — add 3 status labels |
| `frontend/src/components/forms/UploadForm.tsx` | Modify — YouTube link toggle in video tab |
| `frontend/src/pages/UploadPage.tsx` | Modify — handle YouTube URL submission |

## Test Results

- **45 tests passing** (35 service + 10 API) in ~8s
- Ruff lint: all checks passed
- TypeScript: compiles cleanly

## Bugs Found and Fixed During Testing

### 1. pyproject.toml location

**Problem:** Plan said `backend/pyproject.toml` but the project uses a single root-level `pyproject.toml`.
**Fix:** Added `yt-dlp` dependency to the root `pyproject.toml`.

### 2. `uv sync` drops dev dependencies

**Problem:** Running `uv sync` (without `--extra dev`) to install yt-dlp removed dev dependencies like `honcho`, causing `make dev` to fail with `.venv/bin/honcho: No such file or directory`.
**Fix:** Run `uv sync --extra dev` to include dev dependencies.
**Lesson:** Always use `uv sync --extra dev` when adding new dependencies, not bare `uv sync`.

### 3. SQLite table not found after model changes

**Problem:** After adding new columns to `VideoProcessingJob`, the dev SQLite database still had the old schema, causing `sqlite3.OperationalError: no such table: video_processing_job`.
**Fix:** Recreate the dev database:
```python
PYTHONPATH=backend .venv/bin/python -c "
from app import create_app, db
app = create_app('development')
with app.app_context():
    db.drop_all()
    db.create_all()
"
```
Then re-seed users. Dev uses SQLite without migrations, so schema changes require a full recreate.

### 4. YouTube subtitle language keys are non-standard

**Problem:** YouTube uses non-standard language keys for manual subtitles (e.g., `en-US-cvfXDfbeED0` instead of `en` or `en-US`). The initial code passed `--sub-lang en,en-US,en-GB` to yt-dlp, which didn't match these keys, so yt-dlp reported "There are no subtitles for the requested languages" even though the video clearly had English captions.
**Fix:**
- `_extract_captions` now accepts a `lang_code` parameter with the exact key from metadata
- Uses glob pattern `en.*` in addition to exact matches: `--sub-lang {exact_key},en.*,en,en-US,en-GB`
- The caller passes the actual language code from `_determine_caption_source`

**Lesson:** Never assume YouTube subtitle language keys follow standard ISO codes. Always pass the exact key from the metadata JSON and use yt-dlp's glob matching (`en.*`) as a safety net.

### 5. YouTube thumbnails are WebP, not JPEG

**Problem:** Thumbnail download saved the file as `thumbnail.jpg` and the Claude API call hardcoded `media_type: "image/jpeg"`. YouTube actually serves thumbnails as WebP, causing Claude to reject them with: `invalid_request_error: The image was specified using the image/jpeg media type, but the image appears to be a image/webp image`.
**Fix:** Detect actual image format from magic bytes before sending to Claude:
```python
if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
    media_type = "image/webp"
elif raw[:3] == b"\xff\xd8\xff":
    media_type = "image/jpeg"
elif raw[:8] == b"\x89PNG\r\n\x1a\n":
    media_type = "image/png"
elif raw[:4] in (b"GIF8",):
    media_type = "image/gif"
else:
    media_type = "image/jpeg"
```
**Lesson:** Never trust file extensions or assume image formats from URLs. Always detect from magic bytes, especially with third-party services that may change formats without notice.

### 6. Celery worker doesn't auto-reload

**Problem:** After fixing code bugs, the Flask backend picked up changes automatically (via `--debug`), but the Celery worker kept running old code. This caused confusing behavior where the API accepted requests correctly but the background processing still failed with old bugs.
**Fix:** Must restart `make dev` (which restarts all processes including Celery) after any backend code change.
**Lesson:** Celery workers do NOT auto-reload like Flask's debug mode. Always restart the full `make dev` after code changes, not just the Flask server.

### 7. Silent failures in recipe parsing

**Problem:** `_parse_youtube_recipe` caught all exceptions and returned `None`, which the caller turned into the vague error "No recipe found in this video". This made it impossible to distinguish between "Claude API error", "JSON parsing error", and "genuinely no recipe in the video".
**Fix:**
- Changed `_parse_youtube_recipe` to raise `YouTubeCaptionError` with specific error details instead of returning `None`
- Caller catches the exception and includes the real error message
- Task now saves `transcript` and `extraction_method` on the job even when processing fails, enabling post-mortem debugging

### 8. API test patch path

**Problem:** Tests used `@patch("app.api.recipes.process_youtube_recipe_task")` but the task is imported locally inside the endpoint function, so the patch path needed to target the module where the task is defined.
**Fix:** Changed to `@patch("app.tasks.recipe_tasks.process_youtube_recipe_task")`.

## Key Lessons Learned

1. **YouTube's subtitle system is quirky.** Language keys can be arbitrary strings like `en-US-cvfXDfbeED0`. Always use the exact key from yt-dlp's `--dump-json` metadata and pair it with glob patterns as fallback.

2. **yt-dlp's `--dump-json` is the source of truth.** It tells you exactly what subtitles/captions are available and their keys. Don't guess — fetch metadata first, then use the exact keys it reports.

3. **Never hardcode media types.** YouTube (and other services) serve images in varying formats. Detect from file content, not URLs or assumptions.

4. **Celery worker restart is mandatory after code changes.** Unlike Flask's debug auto-reload, Celery workers cache the code at startup. This is the #1 source of "it should work but doesn't" confusion during development.

5. **Save intermediate state on failure.** Persisting the transcript and extraction method even on failed jobs makes debugging vastly easier — you can see whether captions were extracted and what was sent to Claude.

6. **Make errors specific, not generic.** "No recipe found" could mean 5 different things. Propagating the actual exception message (Claude API error, JSON parse error, etc.) saves significant debugging time.

7. **The `pyproject.toml` is at the project root**, not in `backend/`. This is a CookVault-specific detail but easy to forget.

8. **Dev database changes require full recreation.** SQLite dev setup uses `db.create_all()` without Alembic migrations. Adding columns to models means dropping and recreating all tables, then re-seeding.

## Verification Checklist

1. Run tests: `uv run pytest backend/tests/test_youtube_service.py backend/tests/test_youtube_api.py -v`
2. Recreate dev DB (after model changes):
   ```bash
   PYTHONPATH=backend .venv/bin/python -c "
   from app import create_app, db
   app = create_app('development')
   with app.app_context():
       db.drop_all()
       db.create_all()
   "
   # Then re-seed:
   PYTHONPATH=backend .venv/bin/python -m cookbook_db_utils.cli --env development seed users-only
   ```
3. Start app: `make dev` (ensure `uv sync --extra dev` was run first)
4. Manual test — Tier 1: Paste a popular cooking video URL with captions — should complete in ~15-20s with `extraction_method: "captions"`
5. Manual test — Tier 2: Find a video without captions — falls back to audio + Whisper
6. Manual test — error cases: Playlist URL, private video, non-YouTube URL

# Codebase Cleanup Plan

## Executive Summary

Cookle is a well-architected Flask + React/Capacitor app with clear module boundaries and modern dependencies. The core infrastructure is solid: proper Flask factory pattern, SQLAlchemy ORM with typed models, React Query for data fetching, and Capacitor for iOS.

**Key strengths:** Good config management via env vars, proper CORS/security headers, rate limiting, Sentry integration, and a working CI pipeline.

**Key concerns:** Several files have grown far beyond maintainable size (routes.py at 3,878 lines, UploadForm at 1,620 lines), test coverage is low (~15-20% overall) with zero tests on payment/IAP paths, no route-level code splitting on the frontend, and duplicated utility logic (date formatting in 9+ files). No secrets are committed to git (only `.example` files tracked), but the backend config has an unsafe SECRET_KEY fallback.

The codebase is functional and shipping — the priorities below focus on reducing risk, improving maintainability, and preventing regressions as features grow.

---

## Phase 1 — Quick Wins (< 1 hour each, low risk)

### 1.1 Fix SECRET_KEY production fallback
- **File:** `backend/app/config.py:83`
- **Issue:** Falls back to `"dev-secret-key"` if env var missing — dangerous in production
- **Fix:** Raise `ValueError` in `ProductionConfig` if SECRET_KEY not set
- **Effort:** 10 min | **Risk:** None | **Benefit:** Prevents silent security misconfiguration

### 1.2 Remove unused axios dependency
- **File:** `frontend/package.json`
- **Issue:** `axios@^1.10.0` installed but only imported in one file (`publicApi.ts`) which can use the existing `apiFetch` wrapper
- **Fix:** Replace the one axios usage with `apiFetch`, remove axios from package.json
- **Effort:** 20 min | **Risk:** Low | **Benefit:** Smaller bundle, one less dependency to maintain

### 1.3 Extract date/time formatting utilities
- **Files affected:** 9+ files with duplicated `formatDate`/`formatTime` functions
  - `components/cookbook/CookbookCard.tsx:37`
  - `components/recipe/RecipeCard.tsx:118`
  - `components/recipe/CommentsSection.tsx:69`
  - `components/dashboard/RecentActivity.tsx:17`
  - `pages/RecipeDetailPage.tsx:126`
  - `pages/CookbookDetailPage.tsx:59`
  - `components/cookbook/CookbookSearch.tsx:45`
  - `components/recipe/RecipeGroupCard.tsx:26`
  - `components/user/ProfileHeader.tsx:11`
- **Fix:** Create `frontend/src/utils/formatters.ts` with shared `formatDate()` and `formatTime()`, replace all duplicates
- **Effort:** 30 min | **Risk:** Low | **Benefit:** Single source of truth, consistent formatting

### 1.4 Replace alert() with toast notifications
- **Files:** 8 files using native `alert()` for errors
  - `pages/RecipeDetailPage.tsx`, `pages/AccountSettingsPage.tsx`
  - `components/forms/UploadForm.tsx`, `components/payments/SubscriptionStatus.tsx`
  - `components/recipe/RecipeImageDisplay.tsx`, `components/recipe/FeatureToggleButton.tsx`
  - `components/cookbook/CookbookImageDisplay.tsx`, `components/export/ExportButton.tsx`
- **Fix:** Replace `alert()` with `toast.error()` from react-hot-toast (already installed)
- **Effort:** 30 min | **Risk:** None | **Benefit:** Consistent UX, non-blocking error messages

### 1.5 Create frontend constants file
- **Issue:** Magic numbers scattered across components — file size limits, color hex codes, time thresholds
- **Examples:**
  - `UploadForm.tsx:72` — `10 * 1024 * 1024` (10MB) repeated 3x
  - `UploadForm.tsx:224` — `100 * 1024 * 1024` (100MB video limit)
  - `RecipeDetailPage.tsx:136-140` — hardcoded difficulty colors
- **Fix:** Create `frontend/src/utils/constants.ts` with `LIMITS`, `COLORS` objects
- **Effort:** 30 min | **Risk:** None | **Benefit:** Single place to update limits/thresholds

### 1.6 Clean up duplicate iOS StoreKit plugin files
- **Issue:** StoreKit plugin exists in two locations:
  - `frontend/ios/App/App/StoreKitPlugin.swift` (compiled by Xcode)
  - `frontend/ios/App/App/Plugins/StoreKitPlugin/StoreKitPlugin.swift` (original)
  - Same for `StoreKitService.swift`
- **Fix:** Remove the `Plugins/StoreKitPlugin/` directory (Xcode uses the root copies)
- **Effort:** 5 min | **Risk:** Low | **Benefit:** No confusion about which file is authoritative

### 1.7 Standardize export patterns
- **Issue:** 10 components use `export default`, rest use named exports `export { Component }`
  - Default exports: `ErrorBoundary`, `OnboardingModal`, `OfflineBanner`, `SourceCard`, `SourceCardSkeleton`, `Skeleton`, `HomePage`, plus a few others
- **Fix:** Convert all to named exports (project convention)
- **Effort:** 30 min | **Risk:** Low | **Benefit:** Consistent imports, better tree-shaking, easier refactoring

---

## Phase 2 — Targeted Refactors (half-day to full-day each)

### 2.1 Add route-level code splitting
- **File:** `frontend/src/App.tsx` — 15 page imports loaded eagerly
- **Issue:** Entire app bundled as one chunk (~830KB). Users download all pages even if visiting only the homepage.
- **Fix:** Use `React.lazy()` + `Suspense` for all page components
- **Effort:** 3 hours | **Risk:** Low | **Benefit:** Faster initial load, smaller chunks per route

### 2.2 Split UploadForm.tsx (1,620 lines)
- **File:** `frontend/src/components/forms/UploadForm.tsx`
- **Issue:** Handles 4 upload modes (image, text, URL, video) in one component with complex branching
- **Fix:** Extract into:
  - `ImageUploadMode.tsx` — image file handling + preview
  - `TextUploadMode.tsx` — manual text input
  - `URLUploadMode.tsx` — URL scraping
  - `VideoUploadMode.tsx` — video upload
  - `CookbookSelector.tsx` — cookbook picker (reused across modes)
  - `UploadForm.tsx` — thin orchestrator that renders the active mode
- **Effort:** 4 hours | **Risk:** Medium | **Benefit:** Each mode testable independently, easier to maintain

### 2.3 Split RecipeDetailPage.tsx (1,012 lines)
- **File:** `frontend/src/pages/RecipeDetailPage.tsx`
- **Issue:** 8 useState hooks, manages editing, deletion, scaling, cooking mode, mobile menus, action sheets all in one component
- **Fix:** Extract into:
  - `RecipeHeader.tsx` — title, metadata, images
  - `RecipeActions.tsx` — edit/delete/share/collection buttons
  - `RecipeMobileMenu.tsx` — mobile action sheet logic
  - `RecipeInstructions.tsx` — instruction list with notes display
  - Keep `RecipeDetailPage.tsx` as the layout orchestrator
- **Effort:** 4 hours | **Risk:** Medium | **Benefit:** Smaller, focused components; easier to reason about state

### 2.4 Add payment & IAP test coverage
- **Issue:** Zero tests for Stripe payments, Apple IAP, and Lulu print ordering — all revenue-critical paths
- **Files to test:**
  - `backend/app/api/payments.py` (505 lines)
  - `backend/app/api/apple.py` (270 lines)
  - `backend/app/services/apple_iap_service.py`
  - `backend/app/services/stripe_service.py`
- **Fix:** Create `backend/tests/test_payments.py` and `backend/tests/test_apple_iap.py` with mocked external services
- **Effort:** 1 day | **Risk:** None | **Benefit:** Confidence in payment flows, catch regressions before they cost money

### 2.5 Split recipesApi.ts (1,392 lines)
- **File:** `frontend/src/services/recipesApi.ts`
- **Fix:** Split into:
  - `recipesApi.ts` — CRUD (create, read, update, delete)
  - `recipesUploadApi.ts` — image, text, URL, video upload endpoints
  - `recipesEngagementApi.ts` — ratings, notes, comments, collections
- **Effort:** 2 hours | **Risk:** Low | **Benefit:** Easier to find and modify API methods

### 2.6 Expand env var validation for production
- **File:** `backend/app/config.py:245-256`
- **Issue:** `validate_required_env_vars()` only checks SECRET_KEY. In production, missing STRIPE_SECRET_KEY or ANTHROPIC_API_KEY causes runtime errors instead of clear startup failure.
- **Fix:** Validate all required keys per config class (different requirements for dev vs prod)
- **Effort:** 1 hour | **Risk:** None | **Benefit:** Fail fast on misconfiguration

### 2.7 Consolidate error handling patterns (backend)
- **Issue:** Mix of bare `Exception` catches, inconsistent logging (some use `traceback.format_exc()`, some just `str(e)`), some use `current_app.logger`, others use module-level `logger`
- **Fix:** Standardize on module-level `logger` + always log traceback on 500 errors. Create decorator for common API error handling pattern.
- **Effort:** 3 hours | **Risk:** Low | **Benefit:** Consistent debugging experience, easier to trace production errors

---

## Phase 3 — Structural Improvements (multi-day, careful migration)

### 3.1 Continue splitting routes.py (3,878 lines)
- **File:** `backend/app/api/recipes/routes.py`
- **Context:** Previously reduced from 5,087 to 3,878 lines by extracting helpers, images, engagement, video modules. Still the largest file.
- **Fix:** Extract remaining modules:
  - `recipes/uploads.py` — `upload_recipe`, `upload_multi_recipe`, `upload_recipe_text`, `upload_recipe_url` + processing helpers
  - `recipes/crud.py` — basic GET/POST/PUT/DELETE recipe operations
  - Leave `routes.py` as thin registration of sub-blueprints
- **Effort:** 2-3 days | **Risk:** Medium (many route handlers, need careful testing) | **Benefit:** Each module under 500 lines, testable in isolation

### 3.2 Split auth.py (2,318 lines)
- **File:** `backend/app/api/auth.py`
- **Issue:** Registration (195-line function), login, sessions, password reset, account deletion, verification — all in one file
- **Fix:** Extract:
  - `auth/registration.py` — register, verify email/phone
  - `auth/sessions.py` — login, logout, session management
  - `auth/password.py` — forgot/reset/change password
  - `auth/account.py` — deletion, export, settings
- **Effort:** 2 days | **Risk:** Medium (auth is critical path) | **Benefit:** Maintainable auth modules

### 3.3 Extract service layer for recipe processing
- **Issue:** `_process_recipe_image()` in routes.py mixes DB queries, LLM API calls, image preprocessing, and recipe parsing. Uses manual `gc.collect()` indicating memory pressure.
- **Fix:** Create `backend/app/services/recipe_processing_service.py` that owns the OCR pipeline. Route handler calls service, service orchestrates steps.
- **Effort:** 2 days | **Risk:** Medium | **Benefit:** Testable processing pipeline, clearer separation of concerns

### 3.4 Increase frontend test coverage to 40%+
- **Current:** 5 test files covering auth context, login, register, button, upload form (~15% coverage)
- **Priority test targets (highest ROI):**
  1. `recipesApi.ts` — mock API responses, verify request shaping
  2. `RecipeDetailPage.tsx` — render recipe, cooking mode entry, edit mode toggle
  3. `UpgradePage.tsx` — platform detection, Apple IAP vs Stripe routing
  4. `CookingMode.tsx` — step navigation, timer detection
  5. `useWakeLock.ts` — mock navigator.wakeLock API
- **Effort:** 3-4 days | **Risk:** None | **Benefit:** Catch regressions in critical user flows

### 3.5 Add CI payment/IAP test coverage
- **File:** `.github/workflows/ci.yml:76`
- **Issue:** CI only runs 5 of 10 backend test files. Payment, Apple IAP, recipe groups, and YouTube tests are skipped.
- **Fix:** Run all `test_*.py` files. Make security audit job blocking (currently `exit 0` on failure).
- **Effort:** 1 hour for CI config, but requires tests from 2.4 to exist first
- **Risk:** Low | **Benefit:** No untested code reaches production

---

## Do Not Touch List

These areas are messy but stable — refactoring them has high risk and low payoff right now:

| Area | Why Leave It |
|------|-------------|
| `backend/app/services/pdf_service.py` (2,806 lines) | Complex PDF generation with ReportLab. Works reliably, rarely changes. Refactoring risks breaking page layout math. |
| `backend/app/services/lulu_service.py` (1,535 lines) | Print-on-demand integration with retry logic. Tightly coupled to Lulu's API quirks. Only touch if Lulu changes their API. |
| `backend/migrations/versions/` (34 files) | Migration history is append-only. Never edit old migrations. Squash only if starting fresh. |
| `frontend/ios/App/App.xcodeproj/project.pbxproj` | Auto-generated Xcode project file. Only Xcode should edit this. |
| `backend/app/services/recipe_parser.py` | LLM prompt engineering for recipe extraction. Works well, highly tuned. Changes risk degrading parsing quality. |
| `frontend/src/components/onboarding/OnboardingModal.tsx` | One-time flow users see once. Not worth optimizing. |

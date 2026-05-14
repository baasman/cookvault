# Phase 1: BookProject — Multi-Contributor Collection Flow + Basic PDF Export

**Task ID:** 2026-05-14-1016
**Status:** In Progress

## Original Plan

### Context

Cookle's recipe-management feature surface is in a crowded competitive space (Paprika, Mealie, etc.) and user growth has stalled. The strategic response — decided across the conversation that produced this plan — is to add **multi-contributor cookbook projects** ("BookProject") as a new core differentiating feature, while keeping the existing recipe-management product unchanged for existing users.

**The user-facing scenario (v1 marketing wedge: wedding gifts):** One person (the *organizer*) creates a BookProject as a gift — e.g. a sibling making a recipe book for an engaged couple. They generate a shareable link and send it to family + friends (*contributors*). Each contributor opens the link on their phone — **without creating an account** — and submits a recipe (photo of a handwritten card, URL, typed text). Submissions auto-land in the organizer's project. When ready, the organizer downloads a PDF of the assembled cookbook (free watermarked preview, paid clean version). Phase 2 (NOT in this plan) adds print-on-demand fulfillment via the existing Lulu integration and premium designer templates.

**Why this is differentiated:** Every recipe app does single-user collection. Nobody does the *non-technical multi-contributor-to-printable-book* flow well. Cookle's existing import infrastructure (URL, photo/OCR, multi-image, video, text, YouTube) is the unfair advantage that makes "Aunt Linda snaps her handwritten card on her phone" actually work end-to-end. The strategic emphasis (new dev, marketing) shifts to BookProject; existing recipe management stays first-class and supported.

**Strategic context preserved in memory** at `/Users/baasman/.claude/projects/-Users-baasman-projects-cookbook-creator/memory/pivot-wedding-cookbook-focus.md`.

### Architectural Decisions (locked in conversation)

| Decision | Choice |
|---|---|
| Entity model | New `BookProject` entity, generic fields (NOT wedding-hardcoded) |
| PDF tooling | **WeasyPrint** (new dependency). Existing ReportLab code stays for now but becomes legacy; Phase 2 extends WeasyPrint templates with print CSS for the Lulu pipeline. |
| Guest auth | No account required. Optional email for future magic-link claim. New `GuestContributor` model. |
| Submission landing | Auto-land in project (organizer edits/excludes after, no review queue gate) |
| Pricing gate | Free unlimited collection + free watermarked PDF; paid clean PDF export (one-time, ~$15–25, exact amount TBD, set on env config) |
| User-facing feature name | **TBD** — placeholder "Book Project" in copy. Confirm before frontend copy is written. |

### Out of Scope (Phase 2 or later)
- Print-on-demand fulfillment (Lulu integration exists but stays untouched in Phase 1)
- Premium designer templates (Phase 1 ships **one** generic-but-decent template)
- Magic-link / guest account claiming
- Multiple template choices in UI
- Marketing site / new landing page
- Removal of legacy ReportLab code (defer until WeasyPrint covers print-ready output in Phase 2)
- Replacing the existing iOS TabBar entries (Phase 1 adds Book Projects under the existing Cookbooks tab; full IA decision deferred)

---

### Backend Changes

#### New models — `backend/app/models/book_project.py` (new file)

```
BookProject
  id, owner_user_id (FK User)
  project_type (enum: wedding | anniversary | heirloom | memorial | holiday | general)
  status (enum: collecting | review | finalized | exported)
  title, subtitle, dedication (text)
  honorees (JSON / ARRAY of string — couples, individuals, deceased)
  occasion_date (date, nullable)
  submission_deadline (date, nullable)
  cover_image_url (nullable)
  metadata (JSONB — template-specific extras)
  created_at, updated_at

ProjectShareLink
  id, project_id (FK BookProject)
  token (string, indexed unique — 32+ char URL-safe random)
  expires_at (datetime, nullable)
  submission_cap (int, nullable)
  submission_count (int, default 0)
  revoked (bool, default False)
  created_at

GuestContributor
  id, project_id (FK BookProject)
  display_name (string)
  email (string, nullable — for future magic-link claim)
  share_link_id (FK ProjectShareLink — which link they came in through)
  created_at
  (No password, no auth credentials. Identified by project+id during a single submission session via a short-lived cookie.)

BookProjectExport
  id, project_id (FK BookProject)
  user_id (FK User — the purchaser)
  payment_id (FK Payment, nullable — null for free watermarked previews)
  pdf_file_path (string)
  is_watermarked (bool)
  created_at
```

#### Additions to `Recipe` — modify `backend/app/models/recipe.py`
- New nullable column: `book_project_id` (FK BookProject) — when set, this Recipe is a submission to a project
- New nullable column: `guest_contributor_id` (FK GuestContributor) — attribution for "From Aunt Linda"
- Update `Recipe.can_be_viewed_by(user_id, is_admin)` to include "viewer holds valid project share token" path (passed through request context)

#### Alembic migration
Single migration: `backend/migrations/versions/<auto>_book_projects.py`
- Creates four new tables above
- Adds `book_project_id` and `guest_contributor_id` columns to `recipes` with indexes and FKs
- No backfill required (all existing rows: null)

#### Auth — extend `backend/app/api/auth.py`
- Add new decorator `@require_share_token_or_auth` that:
  1. If JWT present → validate as usual (sets `g.current_user`)
  2. Else if `?share_token=...` query param present → look up `ProjectShareLink`, validate (not revoked, not expired, cap not exceeded), sets `g.share_link` and `g.book_project`
  3. Else → 401
- Existing `@require_auth` and `@optional_auth` decorators in this file are the reference pattern. Add the new decorator alongside them.

#### New API blueprint — `backend/app/api/book_projects.py` (new file)
Register in `backend/app/api/__init__.py` alongside existing blueprints.

Endpoints (URL prefix `/book-projects`):

**Organizer (auth required):**
- `POST /` — create project
- `GET /` — list current user's projects
- `GET /<id>` — get project detail + submission summary
- `PATCH /<id>` — update metadata (title, dedication, deadline, honorees, etc.)
- `DELETE /<id>` — soft delete (matches existing User soft-delete pattern)
- `POST /<id>/share-links` — generate new share link (returns full URL including token)
- `DELETE /<id>/share-links/<token>` — revoke
- `GET /<id>/submissions` — list submitted recipes with contributor attribution
- `PATCH /<id>/submissions/<recipe_id>` — edit recipe content (reuses existing recipe edit endpoint logic) or set `excluded` flag
- `POST /<id>/export/preview` — generate watermarked PDF (free, async via Celery — existing Celery is wired up per backend agent report)
- `POST /<id>/export/purchase` — Stripe Payment Intent for clean PDF (mirrors `payments.create_cookbook_purchase()` pattern)
- `POST /<id>/export/confirm` — confirm Stripe payment and generate clean PDF
- `GET /<id>/export/<export_id>/download` — download generated PDF

**Guest (share token required, no auth):**
- `GET /by-token/<token>` — validate token, return minimal project info (title, honorees, project_type — for landing page copy)
- `POST /by-token/<token>/submit-image` — submit recipe via image upload (multi-image supported). Reuses existing parsing pipeline from `backend/app/api/recipes/routes.py` — extract the parsing logic into `backend/app/services/recipe_parsing_service.py` if not already a service, then call from both organizer and guest endpoints.
- `POST /by-token/<token>/submit-text` — submit via raw text
- `POST /by-token/<token>/submit-url` — submit via URL
- All `submit-*` endpoints: accept optional `display_name` and `email` in body, create/match `GuestContributor`, create `Recipe` with `book_project_id`, `guest_contributor_id`, `user_id = project.owner_user_id`, increment `ProjectShareLink.submission_count`
- Rate-limit aggressively via Flask-Limiter (already in stack) — e.g. 10 submissions/IP/hour, 50/token/day

#### WeasyPrint PDF service — `backend/app/services/book_project_pdf_service.py` (new file)
- Add `weasyprint` to `pyproject.toml` (and its system deps: Pango, Cairo — `uv` should handle via wheels, but document in README)
- Service function: `generate_book_project_pdf(project_id, watermarked: bool) -> file_path`
- Renders HTML template via Jinja2 (Flask already has Jinja), passes through WeasyPrint
- Stores generated PDF in existing image/file storage location (mirror how recipe images are stored — `backend/app/utils/storage.py` or equivalent)
- Watermark: applied via CSS `position: fixed` with low-opacity "PREVIEW — cookle.food" repeated, when `watermarked=True`

#### WeasyPrint template — `backend/app/services/book_project_templates/wedding_basic/` (new directory)
- `template.html` (Jinja2) — cover page, dedication page, TOC, recipe pages (with contributor attribution: "From Aunt Linda"), back cover
- `template.css` — print-quality CSS (using `@page` rules, web fonts, no print CSS for crop/bleed in Phase 1)
- Driven by `project_type` for copy variations (wedding → "A gift from your guests" intro; generic → neutral intro). Single layout, copy switches.

#### Payment integration — modify `backend/app/models/payment.py`
- Extend `PaymentType` enum with `BOOK_PROJECT_EXPORT`
- New service method `StripeService.create_book_project_export_purchase(project_id, user_id)` mirroring existing `create_cookbook_purchase()` in `backend/app/services/stripe_service.py`
- Stripe webhook handler in `backend/app/api/print_webhooks.py` (or wherever webhooks live — verify in implementation) extended to mark `BookProjectExport.payment_id` and generate the clean PDF asynchronously upon `payment_intent.succeeded`

#### Reuse — recipe parsing pipeline
- Critical to reuse, NOT reimplement: existing endpoints in `backend/app/api/recipes/routes.py` do photo/OCR, URL, text, multi-image, video parsing
- Refactor the parsing into a service layer (`backend/app/services/recipe_parsing_service.py`) callable from both the existing authenticated routes AND new guest-submit endpoints
- This refactor is a prerequisite — do it as the first PR within Phase 1 (small, low-risk, no behavior change for existing flows)

---

### Frontend Changes

#### Stack reuse (no new dependencies for Phase 1)
React 19 + TypeScript + Vite + react-router-dom v7 + TanStack Query + Tailwind 4 + Capacitor 8. Reuse `apiFetch`, `AuthContext`, existing form-validation pattern (manual), `useMutation`/`useQuery`.

#### New routes — modify `frontend/src/App.tsx`
- `/projects` → ProjectsListPage (auth)
- `/projects/create` → CreateProjectPage (auth) — wizard with project_type chooser, then metadata form
- `/projects/:id` → ProjectDashboardPage (auth) — submissions, share-link management, export button
- `/projects/:id/edit` → EditProjectPage (auth)
- `/projects/:id/export-success` → ProjectExportSuccessPage (auth) — post-purchase landing
- `/contribute/:token` → ContributorLandingPage (**no auth, no Header — minimal layout**)

#### Public layout — new component `frontend/src/components/layout/ContributorLayout.tsx`
- Minimal: project title, organizer name, honorees + project type-specific copy
- No nav/header — different from existing pages which all use the standard `Layout`
- Mobile-first design (Tailwind responsive utilities)

#### New pages
- `frontend/src/pages/ProjectsListPage.tsx` — modeled on `CookbooksPage.tsx`
- `frontend/src/pages/CreateProjectPage.tsx` — modeled on `CreateCookbookPage.tsx` with project_type selector
- `frontend/src/pages/ProjectDashboardPage.tsx` — modeled on `CookbookDetailPage.tsx`, with new ShareLinkManager + SubmissionList sections
- `frontend/src/pages/EditProjectPage.tsx` — simple form
- `frontend/src/pages/ContributorLandingPage.tsx` — the public share-link entry; reuses `ImageUploadMode`, `URLUploadMode`, `TextUploadMode` from `frontend/src/components/forms/` but in unauthenticated context
- `frontend/src/pages/ProjectExportSuccessPage.tsx` — mirrors existing `CookbookPurchaseSuccessPage.tsx`

#### New components
- `frontend/src/components/book-projects/ProjectCard.tsx`
- `frontend/src/components/book-projects/ProjectTypeSelector.tsx`
- `frontend/src/components/book-projects/ShareLinkManager.tsx` (generate, copy, revoke, view submission count, see expiry)
- `frontend/src/components/book-projects/SubmissionList.tsx` (per-recipe edit/exclude actions, contributor attribution)
- `frontend/src/components/book-projects/ExportPaywallModal.tsx` (mirrors existing `PremiumUpgradeModal.tsx` Stripe Elements pattern)

#### Component reuse (KEY)
The contributor submission form is the **same component tree** as the authenticated UploadPage, just rendered inside `ContributorLandingPage` with:
- `apiFetch` calls pointed at `/book-projects/by-token/<token>/submit-*` endpoints (passed via prop or context)
- No Capacitor camera path on the contributor side (default to HTML5 file input with `capture="environment"` — most contributors are on mobile web, not the native app)
- The Capacitor camera path remains for the organizer's own future contributions to their projects
- Verify `ImageUploadMode.tsx`, `URLUploadMode.tsx`, `TextUploadMode.tsx` cleanly accept a `submitEndpoint` and `displayNameField` prop without coupling to AuthContext. Light refactor if needed.

#### Nav integration
- `frontend/src/components/layout/Header.tsx`: add "Book Projects" entry to `navItems` array (after "Cookbooks")
- `frontend/src/components/navigation/TabBar.tsx` (iOS): keep 5 tabs. Add Book Projects as a section *within* the existing Cookbooks tab (which becomes "Books" — listing both Cookbooks and Book Projects). Phase 1 doesn't add a 6th tab; full IA review deferred.
- `frontend/src/services/shareService.ts`: extend with `shareProjectLink(project, shareLink)` wrapping `shareUrl`

#### Wedge copy
- ContributorLandingPage reads `project.project_type` and renders copy variants:
  - `wedding`: "[Honorees] are getting married! Submit a favorite recipe — it'll become part of a cookbook gift from everyone they love."
  - `general`: "[Organizer] is putting together a cookbook. Submit a recipe to be included."
- Single layout, copy switches via a `projectTypeCopy[type]` map.

---

### Implementation Sequence (within Phase 1)

Build in order — each step is independently shippable behind a feature flag if desired:

1. **Recipe parsing service refactor** — extract parsing logic from `recipes/routes.py` into `services/recipe_parsing_service.py`. No behavior change. PR is small and low-risk. Foundation for guest submission.
2. **Database models + migration** — new tables, Recipe column additions. No UI yet, no endpoints.
3. **Backend endpoints (organizer side)** — project CRUD, share-link generation. Tests.
4. **Backend endpoints (guest side)** — share-token decorator, guest submission endpoints. Tests including the auth-bypass path.
5. **WeasyPrint integration + basic template** — service + one template + watermark variant. Smoke test rendering with a real project.
6. **Stripe export-purchase flow** — extend payment types, webhook handler, export download endpoint.
7. **Frontend: organizer surface** — list page, create wizard, dashboard, share-link manager, submission list.
8. **Frontend: contributor surface** — `/contribute/:token` page, minimal layout, mobile photo capture, submission confirmation.
9. **Frontend: paywall** — export modal, post-purchase landing.
10. **End-to-end manual QA + iteration** — see verification below.

---

### Verification (end-to-end manual test)

After implementation, the following loop should succeed end-to-end without code changes:

1. **Organizer flow (authenticated, web)**:
   - Log in as test user.
   - Create a project: project_type=wedding, honorees=["Sarah", "Maya"], occasion_date=2026-08-15, deadline=2026-07-15, title="Sarah & Maya's Recipe Book", dedication populated.
   - Generate a share link. Copy the URL.
2. **Contributor flow (unauthenticated, mobile-sized viewport)**:
   - Open the share-link URL in an incognito window resized to 375×812 (iPhone).
   - Verify the landing page renders project-type-appropriate copy ("Sarah & Maya are getting married!").
   - Submit via photo: upload a photo of a recipe card. Verify upload succeeds, OCR parsing completes, recipe lands in the project.
   - Submit via URL: paste an external recipe URL. Verify parsing.
   - Provide `display_name="Aunt Linda"` and `email="aunt@example.com"`. Verify `GuestContributor` row created.
3. **Organizer review**:
   - Return to organizer dashboard. Verify both submissions appear with "From Aunt Linda" attribution.
   - Edit one recipe (fix a parsing error). Exclude another.
4. **Free preview**:
   - Click "Preview PDF". Verify watermarked PDF downloads, opens in a viewer, renders cover + recipes + attribution legibly.
5. **Paid export**:
   - Click "Export Clean PDF". Stripe checkout opens (use Stripe test mode with card `4242 4242 4242 4242`).
   - On success, ProjectExportSuccessPage renders. Download link works. Clean PDF (no watermark) opens correctly.
6. **Security checks**:
   - Revoke the share link. Verify subsequent submissions return 403.
   - Manually expire a link in DB. Verify the same.
   - Try guest-submit endpoint with garbage token. Verify 404.
   - Verify rate limit triggers after configured threshold.
7. **Run pytest backend suite** + frontend type check + lint. All green.
8. **Smoke-test existing flows**: ensure personal recipe collection (existing UploadPage, CookbooksPage, etc.) still works unchanged for the existing user base — no regressions from the parsing service refactor.

---

### Open Items (resolve before/during implementation)

- **User-facing feature name** — placeholder "Book Project" used throughout. Confirm name before frontend copy is finalized (impacts: nav label, route paths if changed from `/projects` to e.g. `/books`, share-link landing copy, email subject lines).
- **Export pricing** — exact $ amount for clean PDF (initial range: $15–25). Set via env var or DB-configurable.
- **Watermark visual** — text content + placement. Default: "PREVIEW — cookle.food" diagonal repeat at ~15% opacity.
- **Submission cap default** — for share links, what's a sensible default cap (e.g., 100 submissions per link)? Or no cap by default? Decide during implementation.
- **Display of contributor email to organizer** — show or hide? Privacy implication. Default: hidden, only used internally.
- **Recipe storage when contributor doesn't have an account** — recipes get `user_id = project.owner_user_id` so they live in the organizer's space. After Phase 2 magic-link claim, ownership could transfer back. Document this in code.
- **iOS native (Capacitor)** — when does the iOS app get BookProject support? Phase 1 ships web-first. Native iOS shows the new "Book Projects" section under the Books tab but might lag on the camera/native pieces of the create flow. Confirm scope with user before frontend work begins.

---

### Critical files to modify

**New files:**
- `backend/app/models/book_project.py`
- `backend/app/api/book_projects.py`
- `backend/app/services/book_project_pdf_service.py`
- `backend/app/services/recipe_parsing_service.py` (refactor target)
- `backend/app/services/book_project_templates/wedding_basic/template.html`
- `backend/app/services/book_project_templates/wedding_basic/template.css`
- `backend/migrations/versions/<auto>_book_projects.py`
- `frontend/src/pages/ProjectsListPage.tsx`
- `frontend/src/pages/CreateProjectPage.tsx`
- `frontend/src/pages/ProjectDashboardPage.tsx`
- `frontend/src/pages/EditProjectPage.tsx`
- `frontend/src/pages/ContributorLandingPage.tsx`
- `frontend/src/pages/ProjectExportSuccessPage.tsx`
- `frontend/src/components/layout/ContributorLayout.tsx`
- `frontend/src/components/book-projects/*.tsx` (5 components listed above)

**Modified files:**
- `backend/app/models/recipe.py` (Recipe column additions, `can_be_viewed_by` extension)
- `backend/app/models/payment.py` (PaymentType enum extension)
- `backend/app/api/__init__.py` (register new blueprint)
- `backend/app/api/auth.py` (add `@require_share_token_or_auth` decorator)
- `backend/app/api/recipes/routes.py` (refactor parsing into shared service — behavior preserved)
- `backend/app/services/stripe_service.py` (add `create_book_project_export_purchase`)
- `backend/app/api/print_webhooks.py` (extend webhook handler for new payment type — verify file location during impl)
- `pyproject.toml` (add `weasyprint` dependency)
- `frontend/src/App.tsx` (new routes)
- `frontend/src/components/layout/Header.tsx` (nav entry)
- `frontend/src/components/navigation/TabBar.tsx` (extend Cookbooks tab to include Book Projects)
- `frontend/src/components/forms/ImageUploadMode.tsx` and siblings (light prop refactor for contributor flow reuse — verify coupling)
- `frontend/src/services/shareService.ts` (`shareProjectLink` helper)

## Timeline
- Started: 2026-05-14T14:16:15Z
- Completed:

## Deviations
- 2026-05-14T14:30:00Z (Step 1): Scoped the recipe parsing service refactor more narrowly than the plan implied. Investigation revealed the existing upload endpoints (image, multi, text, URL) don't have monolithic parsing logic to extract — actual parsing is already split across existing services (`RecipeParser`, `UrlRecipeService`) and async Celery tasks. The only shared logic worth extracting was the recipe-record-construction helpers (`_create_ingredients`, `_create_instructions`, `_create_tags`, plus three sub-helpers). Moved these to new `backend/app/services/recipe_parsing_service.py` as public `create_recipe_ingredients/instructions/tags` (with private sub-helpers). HTTP-routing-specific concerns (auth, quota, cookbook handling, response shape) stay in routes.py. Existing endpoints reference the service via import. All 36 recipe tests pass. This still provides the foundation task 4 needs: guest submission endpoints can import the same `create_recipe_*` helpers to build Recipes inline without duplicating logic.
- 2026-05-14T14:45:00Z (Step 2 — type choices): Plan called for PostgreSQL-specific column types (`ARRAY` for honorees, `JSONB` for metadata). Local dev DB is SQLite (per current Flask config — `.env` declares Postgres but config falls back to SQLite for local). Switched `honorees` and `project_metadata` to `sa.JSON` (cross-dialect; renders as JSONB on PostgreSQL, JSON on SQLite). No functional change but loses PG-specific JSONB indexing in dev — production behavior unchanged.
- 2026-05-14T14:50:00Z (Step 2 — migration SQLite compatibility): Added `bind.dialect.name == "sqlite"` checks to skip `op.create_foreign_key` for new Recipe columns on SQLite (SQLite doesn't support `ALTER TABLE ADD CONSTRAINT`; FK enforcement disabled by default anyway). FK is still defined at the SQLAlchemy ORM level, so app-layer relationships work on both dialects. Matches the pattern already established in other migrations in the project. `Recipe.can_be_viewed_by()` extension for share-token access deferred to Task 4 — needs the share-token request context that the decorator establishes.
- 2026-05-14T14:55:00Z (Step 2 — deferred extension): `Recipe.can_be_viewed_by(user_id, is_admin)` was supposed to be extended to recognize the "viewer holds a valid project share token" case. Deferring to Task 4 where the share-token decorator is built — extension needs the request context (`g.share_link`, `g.book_project`) that doesn't yet exist.

## Results Summary
[To be added on completion]

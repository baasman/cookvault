# Phase 2: Verify Payments, Persist PDFs, Print via Lulu, Polish

**Task ID:** 2026-05-15-1742
**Status:** In Progress

## Original Plan

### Context

Phase 1 shipped a working BookProject feature on `feature/book-projects` — organizers create cookbook projects, contributors submit recipes via share links without accounts, organizers curate submissions, and a free watermarked PDF preview renders end-to-end. The paid clean export and Stripe webhook code is in place but unverified in a live payment flow, and the rendered PDF lands on ephemeral disk that Render wipes on each deploy.

The strategic goal of Phase 2 is to take this from "demo-quality on a feature branch" to "production-quality, printable book." That breaks into:

1. **Verify the existing Stripe paid-export flow works end-to-end** — the audit found the webhook plumbing is already in place (`/api/payments/webhook`, signature verification, BOOK_PROJECT_EXPORT routing in `handle_payment_succeeded`). What's missing is verification + local-dev tooling, not net-new code.
2. **Persist generated PDFs in Cloudinary** so paid customers don't lose access after a deploy.
3. **Integrate Lulu print-on-demand for BookProjects** — the existing Lulu integration (`LuluService`, `PrintOrder` model, webhook handlers) is structurally complete but cookbook-coupled and shelf-ware (sandbox mode default, no production activation). Bridge it to BookProjects, extend the WeasyPrint template with print CSS for bleed/crop marks (single template system across digital + print, per architecture decision).
4. **Phase 1.5 polish** — iOS TabBar, EditProjectPage, email notifications, user-facing feature name — once the headline print flow works.
5. **Premium templates** — gated on the designer friend's deliverables.

**Architecture decisions for Phase 2:**

| Decision | Choice |
|---|---|
| Print-ready PDF engine for BookProjects | **WeasyPrint with `@page` print CSS** — one template system for digital + print, designer friend authors HTML/CSS, ReportLab `print_pdf_builder.py` stays as legacy for the existing Cookbook print path |
| PDF storage | **Cloudinary `resource_type="raw"`** — extend the existing service that handles recipe images, proxy downloads through the auth'd endpoint (don't expose Cloudinary URLs to the frontend) |
| `PrintOrder` polymorphism | **Nullable `cookbook_id` + new nullable `book_project_id` + CHECK constraint** (exactly one set) — minimal model churn, generalizes existing endpoints with branching logic |
| Polish-item timing | **After Lulu** — keep focus on the headline feature first |

---

### Phase 2A: Verify Stripe paid-export flow (small — ~half day)

**Goal:** confirm the existing Stripe webhook path actually works for `BOOK_PROJECT_EXPORT`, both locally and in production. No code changes expected beyond docs + tests.

#### Verify in local dev
- Document `stripe listen` setup in the project README. Command: `stripe listen --forward-to localhost:5001/api/payments/webhook`. The webhook secret it prints goes into `.env` as `STRIPE_WEBHOOK_SECRET`.
- End-to-end manual test: dashboard → Buy clean PDF → Stripe Elements with test card `4242 4242 4242 4242` → confirm webhook arrives → confirm `_handle_book_project_export_payment_success` runs → confirm `BookProjectExport.pdf_file_path` is populated → confirm "Download clean PDF" button appears and the file downloads.

#### Verify in production
- Manually register the webhook in the Stripe dashboard pointing at `https://cookle-backend.onrender.com/api/payments/webhook`.
- Subscribe to events: `payment_intent.succeeded`, `payment_intent.payment_failed`, plus the existing subscription/invoice events the handler already listens to.
- Set `STRIPE_WEBHOOK_SECRET` in Render env vars.
- Test with a real Stripe test-mode card against the deployed app (or wait for a real first customer and watch Sentry).

#### Add a regression test
- New test in `backend/tests/test_payments.py` that simulates a `payment_intent.succeeded` webhook for a `BOOK_PROJECT_EXPORT` and asserts the export row is updated. The existing `TestWebhookHandler` test in `test_api_book_projects.py` covers the handler in isolation but doesn't exercise the HTTP webhook route + signature verification path.

#### Files
- **Read:** `backend/app/api/payments.py:461` (webhook endpoint), `backend/app/services/stripe_service.py:686-732` (event routing), `backend/app/services/stripe_service.py:562-621` (BookProject handler)
- **Modify:** `README.md` or `docs/development/*.md` (add stripe-listen instructions)
- **Add:** test in `backend/tests/test_payments.py` covering the HTTP webhook route for BOOK_PROJECT_EXPORT

#### Verification
- `stripe listen` running locally, manual end-to-end test as described above, clean PDF downloads after payment.
- Pytest new test passes.

---

### Phase 2B: Persistent PDF storage via Cloudinary (medium — ~1 day)

**Goal:** generated BookProject PDFs survive deploys and storage rotations. Today they live in `backend/uploads/book_project_exports/` which Render wipes.

#### Backend changes

1. **Extend `cloudinary_service.py`** with a `upload_pdf(pdf_bytes, original_filename, folder) -> dict` method that calls `cloudinary.uploader.upload` with `resource_type="raw"`. Mirror the existing `upload_image` shape (returns `public_id`, `url`, `bytes`).
   - File: `backend/app/services/cloudinary_service.py`

2. **Migration `book_projects_004`** adding `cloudinary_public_id: Optional[str]` and `cloudinary_url: Optional[str]` to `book_project_export`. Keep `pdf_file_path` for local-dev fallback when Cloudinary isn't enabled.
   - File: `backend/migrations/versions/book_projects_004_export_cloudinary_fields.py` (new)
   - Modify: `backend/app/models/book_project.py:234-267` (add fields)

3. **Update `book_project_pdf_service.render_book_project_pdf`** to return a structured result rather than just a path string. Two variants:
   - When Cloudinary enabled: render to bytes (use existing `render_book_project_pdf_to_bytes`), upload via `cloudinary_service.upload_pdf`, return `{"cloudinary_public_id": ..., "cloudinary_url": ..., "pdf_file_path": None}`.
   - When Cloudinary disabled: write to disk as today, return `{"cloudinary_public_id": None, "cloudinary_url": None, "pdf_file_path": str}`.
   - File: `backend/app/services/book_project_pdf_service.py`

4. **Update both export call sites** to write the returned fields onto the export row:
   - `book_projects.py:create_export_preview` (preview)
   - `stripe_service.py:_handle_book_project_export_payment_success` (paid clean)

5. **Update `download_export` endpoint** to handle both storage backends:
   - If `cloudinary_url` is set: backend-side fetch via `requests.get(cloudinary_url, stream=True)` and stream to the user with `Response(stream_with_context(...), mimetype="application/pdf")`. **Proxy strategy** — don't expose the Cloudinary URL to the frontend, since the URLs are publicly resolvable.
   - If `pdf_file_path` is set: existing `send_file` path.
   - If neither: existing 202 "pending" / 410 "gone" responses.
   - File: `backend/app/api/book_projects.py:1263-1307`

#### Tests
- Mock `cloudinary_service.upload_pdf` in the existing PDF service tests so they don't hit Cloudinary.
- New test: preview generation when Cloudinary is enabled writes the right fields; download endpoint proxies correctly.

#### Files
- **Read for pattern:** `backend/app/api/recipes/helpers.py:26-98` (existing image upload + local fallback)
- **Add:** migration `book_projects_004`
- **Modify:** `cloudinary_service.py`, `book_project.py` (model), `book_project_pdf_service.py`, `book_projects.py` (preview + download), `stripe_service.py` (handler)
- **Modify:** `backend/tests/test_book_project_pdf_service.py`, `backend/tests/test_api_book_projects.py`

#### Verification
- With `USE_CLOUDINARY=true` and creds set: generate a preview, confirm `pdf_file_path` is null and `cloudinary_url` is set on the row. Download via the dashboard, confirm the file streams correctly.
- With `USE_CLOUDINARY=false`: confirm local-disk fallback still works (existing tests pass).
- Run full test suite.

---

### Phase 2C: Lulu print fulfillment for BookProjects (large — ~1.5 weeks)

**Goal:** organizer can click "Order printed book" on the dashboard, configure size/binding/quantity/shipping, pay, and Lulu fulfills the actual print. End-to-end in Lulu sandbox first; production activation gated on a sandbox test order.

The Lulu code is structurally complete — `LuluService`, `PrintOrder` model, `print_orders.py` endpoints, `print_webhooks.py` for status updates, `print_pdf_builder.py` for print-ready PDFs (ReportLab), `cover_generation_service.py`. The work is mostly **generalization** + **bridging the WeasyPrint template to produce print-ready output**.

#### C1. PrintOrder polymorphism
- Migration `book_projects_005`: make `cookbook_id` nullable on `print_orders`, add nullable `book_project_id: ForeignKey(book_project.id)`, add a CHECK constraint requiring exactly one to be set (`cookbook_id IS NULL` ≠ `book_project_id IS NULL`). SQLite-aware (CHECK constraints need different syntax than PG; follow the dialect-aware pattern from `book_projects_001`).
- Update `PrintOrder` model: relationship to `BookProject` alongside `Cookbook`, helper property `content` that returns whichever is set, helper property `content_type` returning `"cookbook" | "book_project"`.
- Files: `backend/migrations/versions/book_projects_005_print_order_polymorphic.py`, `backend/app/models/print_order.py`

#### C2. WeasyPrint print CSS for BookProject templates
The headline architectural decision: extend the WeasyPrint template to produce print-ready output (bleed, crop marks, page sizes matching Lulu trim sizes). Lulu accepts PDF/X-3 ideally, but standard PDFs with bleed + crop marks are usable.

- Add a `print` mode to `book_project_pdf_service.render_book_project_pdf`: accepts a `trim_size` parameter (one of the existing `TrimSize` enum values) and a `print_ready: bool`. When true, applies a print-mode CSS overlay alongside the existing `template.css`.
- New CSS file: `backend/app/services/book_project_templates/wedding_basic/print.css` — overrides `@page { size: <trim>; bleed: 3mm; marks: crop }`, removes the page-number footer (Lulu adds its own), fixes the front cover to a single page with bleed.
- Verify WeasyPrint output meets Lulu's interior PDF validation. Open issues to investigate during implementation: color space (WeasyPrint outputs RGB; Lulu accepts RGB but CMYK is preferred for cookbooks), embedded fonts (need to confirm all template fonts are embedded subset), PDF/X compliance (out of scope for v1; Lulu accepts standard PDFs).
- **Fallback if WeasyPrint print output won't validate at Lulu:** post-process with Ghostscript (`gs -dPDFX -sColorConversionStrategy=CMYK ...`) — adds a dependency but solves color + compliance in one pass. Investigate during implementation.
- A separate template can be added later for a dedicated print layout (e.g. `wedding_basic_print/`), but v1 reuses `wedding_basic` with overlay CSS.

Files: `backend/app/services/book_project_pdf_service.py`, `backend/app/services/book_project_templates/wedding_basic/print.css` (new)

#### C3. Cover generation for BookProjects
The existing `CoverGenerationService` accepts a `Dict[str, str]` of metadata (title, author, description) and is data-agnostic. Adapt it for BookProject:
- Map `BookProject.title` → cover title, `BookProject.honorees_joined` → cover author/subtitle, `BookProject.dedication` → back cover blurb.
- Confirm the existing 3 templates (Minimalist, Classic, Book) work; if not, add a wedding-flavored template. v1 picks one default.

Files: `backend/app/services/cover_generation_service.py` (light extension if needed), wire it into the print-order submit flow

#### C4. Print order endpoints accept BookProjects
Add branching logic — each existing endpoint either reads `cookbook_id` or `book_project_id` from the request and resolves accordingly:
- `POST /print-orders/specifications` — already cookbook-aware via `?cookbook_id=X`, add `?book_project_id=X`
- `POST /print-orders/quote` — accept either ID, fetch recipes from the right entity
- `POST /print-orders/` (create order) — accept either ID, validate ownership, set the appropriate FK on the PrintOrder row
- `POST /print-orders/<id>/submit` (the critical path) — branch the PDF generation: cookbook → `print_pdf_builder` (ReportLab); book_project → `book_project_pdf_service` (WeasyPrint print mode)
- Other endpoints (`/payment`, `/cancel`, `/refund`, etc.) are content-type-agnostic, no changes needed

Files: `backend/app/api/print_orders.py`

#### C5. Webhook handler (`print_webhooks.py`)
Already content-type-agnostic — it updates `PrintOrder` rows by `lulu_print_job_id` regardless of cookbook vs book_project. Audit confirms no changes needed beyond verifying behavior with a BookProject order.

#### C6. Frontend: order-printed-book flow on the BookProject dashboard

Reuse the existing `PrintOrderModal` (if it's content-type-agnostic) or adapt it. The existing `PrintOrderButton` requires `cookbookId`; generalize to accept either `cookbookId` or `bookProjectId`.

- Add "Order printed book" button to the Export section of `ProjectDashboardPage` (next to the existing Download Preview / Buy Clean PDF buttons).
- Wire it to open the print order configuration flow (trim size, binding, paper, quantity, shipping address) — reusing whatever cookbook UI exists.
- Show in-flight print orders on the dashboard (link to the existing `/orders` page).

Files: `frontend/src/components/print/PrintOrderButton.tsx`, `frontend/src/pages/ProjectDashboardPage.tsx`, possibly `frontend/src/components/print/PrintOrderModal.tsx`

#### C7. End-to-end verification in Lulu sandbox
- Set `LULU_SANDBOX_MODE=true` and real sandbox credentials in `.env`.
- Create a BookProject with a few recipes, configure a print order, submit. Verify:
  - Interior + cover PDFs upload to Lulu without validation errors.
  - Lulu returns a print job ID, stored on `PrintOrder.lulu_print_job_id`.
  - The validation webhook arrives and updates `interior_validation_status` / `cover_validation_status`.
  - The status webhooks (`print_job.printing`, etc.) progress the order through the state machine.
- If interior PDF fails Lulu validation: iterate on the print CSS, add Ghostscript post-processing if needed.

#### Files (Phase 2C summary)
**New:**
- `backend/migrations/versions/book_projects_005_print_order_polymorphic.py`
- `backend/app/services/book_project_templates/wedding_basic/print.css`

**Modified:**
- `backend/app/models/print_order.py` (polymorphism + properties)
- `backend/app/services/book_project_pdf_service.py` (print mode)
- `backend/app/services/cover_generation_service.py` (light extension)
- `backend/app/api/print_orders.py` (branching logic across multiple endpoints)
- `frontend/src/components/print/PrintOrderButton.tsx` (accept both IDs)
- `frontend/src/pages/ProjectDashboardPage.tsx` (Order Printed Book button)
- Possibly: `frontend/src/components/print/PrintOrderModal.tsx`

**Read but unchanged (existing infrastructure to leverage):**
- `backend/app/services/lulu_service.py` (fully reusable)
- `backend/app/api/print_webhooks.py` (content-type-agnostic)
- `backend/app/services/print_pdf_builder.py` (stays for Cookbook print path; legacy from BookProject perspective)

#### Verification
End-to-end Lulu sandbox order succeeds: print job created, validation passes, status updates flow, manual `print_job.delivered` webhook simulation results in `PrintOrder.status = DELIVERED`. Frontend correctly displays in-flight order on the project dashboard.

---

### Phase 2D: Phase 1.5 polish (variable — ~2-3 days, parallelizable)

Per the user-confirmed order, these come after Lulu. Listed in rough priority:

1. **User-facing feature name** — replace "Book Projects" placeholder throughout. Search: `/projects` route, nav labels, page titles, contributor landing copy ("Powered by Cookle"), share-link `/contribute/` URL. Decision required from user.
2. **EditProjectPage UI** — currently can only edit via PATCH API. New route `/projects/:id/edit`, mirrors `CreateProjectPage` with prefilled values. Backend already supports it.
3. **iOS TabBar entry** — extend the Cookbooks tab to a combined "Books" view that shows both Cookbooks and BookProjects in tabs/sections. Per Phase 1 plan.
4. **Email notifications** — investigate first whether an email service is configured (sendgrid/postmark/SES). If yes: organizer gets an email when a new submission arrives, when the deadline approaches, when their export is ready. If no: skip until email infra exists.
5. **Submission deadline UX** — currently stored as metadata, not enforced. At minimum, show a countdown on the contributor landing page; optionally auto-close share links past the deadline.

Each item is small (hours) but combined adds up to a few days. They can be parallelized or done as one-offs as time allows.

---

### Phase 2E: Premium designer templates (deferred — designer-gated)

Gated on the designer friend's deliverables. Each template = a new directory under `backend/app/services/book_project_templates/<template_name>/` with `template.html` + `template.css` (and `print.css` after C2). Plus a chooser UI in `CreateProjectPage` and `EditProjectPage`. Cheap to add per template; high quality bar.

---

### Critical files reference (Phase 2 entry points)

**Backend:**
- `backend/app/services/stripe_service.py:686-732` — webhook event routing
- `backend/app/services/stripe_service.py:562-621` — `_handle_book_project_export_payment_success`
- `backend/app/services/cloudinary_service.py` — image-only today; needs `upload_pdf` for raw resource type
- `backend/app/services/book_project_pdf_service.py` — WeasyPrint rendering; needs print-mode variant
- `backend/app/services/lulu_service.py` — fully reusable, no changes expected
- `backend/app/api/print_orders.py` — currently cookbook-coupled, needs branching
- `backend/app/api/payments.py:461` — Stripe webhook receiver
- `backend/app/api/print_webhooks.py` — Lulu status webhooks (content-type-agnostic)
- `backend/app/api/book_projects.py:1263-1307` — `download_export` endpoint (needs Cloudinary proxy support)
- `backend/app/models/print_order.py` — needs polymorphic FK
- `backend/app/models/book_project.py:234-267` — `BookProjectExport` (add Cloudinary fields)

**Frontend:**
- `frontend/src/pages/ProjectDashboardPage.tsx` — add Order Printed Book button
- `frontend/src/components/print/PrintOrderButton.tsx` — generalize from cookbook-only
- `frontend/src/components/print/PrintOrderModal.tsx` — likely needs adaptation
- `frontend/src/pages/OrdersPage.tsx` — existing print orders list; verify it handles BookProject-linked orders

---

### Overall verification gate

Phase 2 is considered done when:
- A user can buy a clean PDF via Stripe (test card → webhook → render → download), file lives in Cloudinary, persists across deploys.
- A user can place a Lulu print order from the BookProject dashboard, the order makes it through Lulu sandbox to a `DELIVERED` state, the PrintOrder rows in the DB correctly track status throughout.
- Production Stripe and Lulu sandbox webhooks are both verified live (not just unit-tested).
- All existing tests pass (current baseline: 235 passed, 0 skipped on `feature/book-projects`).
- The branch is up for review/merge — Phase 2 may merge separately from Phase 1 or as one big PR depending on user preference.

## Timeline
- Started: 2026-05-15T21:42:30Z
- Completed:

## Deviations
None yet.

## Results Summary
[To be added on completion]

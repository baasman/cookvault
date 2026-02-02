# App Store Readiness Roadmap

**Task ID:** 2026-01-31-1430
**Status:** In Progress

## Original Plan

### Overview
Comprehensive roadmap to prepare Cookle (cookbook/recipe app) for iOS App Store submission. Organized into 5 phases with clear dependencies and priorities.

### Decisions Made
- **Account Deletion:** 7-day soft delete with recovery option
- **Crash Reporting:** Yes, integrate Sentry (frontend + backend)
- **Scope:** All 5 phases (~50-70 hours over 5 weeks)

---

## Phase 1: Security & Critical Compliance (Week 1)
**Priority: BLOCKER - Must complete before any public release**

### 1.1 Rotate Exposed API Keys
- Rotate all keys in Stripe, Anthropic, SendGrid, Cloudinary, Twilio, Lulu
- Update `.env` locally and Render environment variables

### 1.2 Create Privacy Policy Page
- Create `frontend/src/pages/PrivacyPolicyPage.tsx`
- Add route and footer link

### 1.3 Implement Account Deletion (7-Day Soft Delete)
- Backend: Add `DELETE /api/auth/account` endpoint
- Add `deleted_at`, `deletion_scheduled_for` fields to User model
- Create Celery task to purge accounts after 7 days
- Frontend: Add deletion flow in AccountSettingsPage

### 1.4 Implement Data Export
- Backend: Add `GET /api/auth/export` endpoint (ZIP with profile, recipes, cookbooks, images, payments)
- Frontend: Add "Download My Data" button

---

## Phase 2: Error Handling & Stability (Week 2)

### 2.1 Add Crash Reporting (Sentry)
- Frontend: Install @sentry/react, initialize in main.tsx
- Backend: Install sentry-sdk[flask], initialize in __init__.py

### 2.2 Create Error Boundary Component
- Create `frontend/src/components/ErrorBoundary.tsx`
- Wrap app in ErrorBoundary

### 2.3 Create 404 and Error Pages
- Create NotFoundPage.tsx and ErrorPage.tsx
- Add catch-all route

### 2.4 Implement Offline Handling
- Create useNetworkStatus hook and OfflineBanner component
- Detect online/offline status using @capacitor/network

### 2.5 Fix Placeholder Emails
- Replace placeholder emails in TermsOfServicePage and CopyrightPolicyPage

---

## Phase 3: iOS-Specific Features (Week 3)

### 3.1 Configure Deep Linking
- Create apple-app-site-association file
- Configure iOS entitlements and Capacitor

### 3.2 Review Info.plist
- Verify camera, photo library usage descriptions

### 3.3 Verify App Icons & Splash
- Ensure all required sizes are present

### 3.4 App Store Metadata Preparation
- Prepare app name, subtitle, keywords, description, screenshots

---

## Phase 4: UX Polish (Week 4)

### 4.1 Create Onboarding Flow
- Create OnboardingModal and OnboardingStep components

### 4.2 Add Empty States
- Add empty states to RecipesPage, CookbooksPage

### 4.3 Add Loading Skeletons
- Create Skeleton, RecipeCardSkeleton, CookbookCardSkeleton components

### 4.4 Complete Settings Page
- Add notification preferences, display preferences, about section

---

## Phase 5: Final Polish & Testing (Week 5)

### 5.1 Remove Debug Code
- Remove/guard console.log, print statements

### 5.2 Performance Testing
- Test on real devices

### 5.3 End-to-End Testing
- Test all user flows

### 5.4 App Store Submission
- Archive, upload, submit for review

---

## Timeline
- Started: 2026-01-31T14:30:00Z
- Completed:

## Deviations
- 2026-01-31T15:00:00Z: Phase 2.5 (Fix Placeholder Emails) was completed early as part of Phase 1.2 since it was a quick win while working on the Footer component.
- 2026-02-01T00:00:00Z: Completed remaining Phase 2 items (2.2-2.4) - Error Boundary, 404/Error pages, and Offline handling.
- 2026-02-01T18:30:00Z: Skipped Phase 3.1 (Deep Linking) - user doesn't have App Store account yet; will add later.
- 2026-02-01T18:30:00Z: Phase 3.2-3.3 already complete (Info.plist, App Icons).
- 2026-02-01T18:30:00Z: Phase 4 completed - Onboarding modal, empty states already existed, added skeleton loading, enhanced settings page.

## Results Summary
[To be added on completion]

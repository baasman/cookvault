# Cooking Mode — Step-by-Step Kitchen Experience

**Task ID:** 2026-04-01-1330
**Status:** Abandoned

## Original Plan

Cookle users can store and browse recipes, but the experience of actually *cooking from* a recipe is the same as reading it — a long scrollable page. Cooking Mode transforms the recipe detail into a fullscreen, one-step-at-a-time interface optimized for kitchen use: large text, keep-screen-awake, swipe navigation, inline timers, and haptic feedback.

Frontend-only feature — no backend changes needed.

### Architecture
Fullscreen portal overlay launched from `RecipeDetailPage` (not a new route). Recipe data including `scaleFactor` already loaded.

### New Files (8)
- `frontend/src/components/cooking-mode/CookingMode.tsx` — Main orchestrator
- `frontend/src/components/cooking-mode/CookingModeStep.tsx` — Single instruction display
- `frontend/src/components/cooking-mode/CookingModeIngredients.tsx` — Ingredients (step 0)
- `frontend/src/components/cooking-mode/CookingModeProgress.tsx` — Progress bar + close
- `frontend/src/components/cooking-mode/CookingModeTimer.tsx` — Countdown timer
- `frontend/src/hooks/useCookingTimer.ts` — Multi-timer state
- `frontend/src/hooks/useWakeLock.ts` — Screen wake lock (Web API)
- `frontend/src/utils/timerDetection.ts` — Parse time mentions

### Modified Files (1)
- `frontend/src/pages/RecipeDetailPage.tsx` — Add "Start Cooking" button + overlay

### Implementation Phases
1. **Phase 1 — Core Shell:** CookingMode, Progress, Step, Ingredients components + swipe/button nav + entry point
2. **Phase 2 — Timers:** Timer detection, useCookingTimer, CookingModeTimer + audio/haptic completion
3. **Phase 3 — Polish:** Wake lock, status bar hiding, step animations, keyboard nav

## Timeline
- Started: 2026-04-01T13:30:00Z
- Completed:

## Deviations
None yet.

## Results Summary
Abandoned in favor of Organization & Management features plan. Cooking Mode components appear to have been partially or fully implemented based on git history (commit a315118 references Cooking Mode promotion).

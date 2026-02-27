# iOS Native UI Refactoring

**Task ID:** 2026-02-27-1030
**Status:** In Progress

## Original Plan

### Goal
Make the Cookle iPhone app feel native by implementing iOS-specific UI patterns. Changes apply **only on iOS** - web and Android keep current behavior.

### Key Changes

#### 1. Bottom Tab Bar Navigation (iOS only)
Replace hamburger menu with iOS-style bottom tab bar:
- **Tabs**: Home | Recipes | Add (+) | Cookbooks | Profile
- Centered "Add" button with accent color (common iOS pattern)
- Fixed to bottom with `env(safe-area-inset-bottom)` for home indicator
- Active tab indicator using accent color

#### 2. Action Sheets (iOS only)
Replace dropdown menus with iOS-style bottom action sheets:
- Slides up from bottom with drag-to-dismiss
- Used for: Add Recipe menu, Recipe actions, User menu
- Handle indicator at top, Cancel button at bottom

#### 3. Touch Interactions
- Replace `hover:` states with `active:` press states
- Add haptic feedback via `@capacitor/haptics`
- Subtle scale animation on press (`active:scale-[0.97]`)

#### 4. Layout Adjustments (iOS only)
- Hide header hamburger menu and footer on iOS
- Simplify header to logo + context actions only
- Add bottom padding for tab bar height + safe area

---

### Files to Create

| File | Purpose |
|------|---------|
| `src/components/navigation/TabBar.tsx` | iOS bottom tab bar component |
| `src/components/ui/ActionSheet.tsx` | iOS-style action sheet |
| `src/utils/haptics.ts` | Haptic feedback utilities |
| `src/hooks/useHapticFeedback.ts` | Hook for haptic feedback |

### Files to Modify

| File | Changes |
|------|---------|
| `src/components/layout/Layout.tsx` | Conditionally render TabBar, hide Footer on iOS, add bottom padding |
| `src/components/layout/Header.tsx` | Hide hamburger + nav on iOS, keep logo + user avatar |
| `src/components/ui/Button.tsx` | Add `active:` states, haptic feedback |
| `src/index.css` | Add safe area CSS variables, iOS utility classes |
| `package.json` | Add `@capacitor/haptics` dependency |

---

### Implementation Phases

#### Phase 1: Foundation
1. Install `@capacitor/haptics` and sync iOS
2. Create `src/utils/haptics.ts` with feedback utilities
3. Create `src/hooks/useHapticFeedback.ts`
4. Update `Button.tsx` with touch states

#### Phase 2: Action Sheet Component
1. Create `src/components/ui/ActionSheet.tsx`
   - Props: `isOpen`, `onClose`, `title?`, `options[]`, `cancelText?`
   - Slide-up animation, drag-to-dismiss, backdrop
   - Bottom safe area padding

#### Phase 3: Tab Bar Navigation
1. Create `src/components/navigation/TabBar.tsx`
   - 5 tabs with icons: Home, Recipes, Add, Cookbooks, Profile
   - Platform-gated (iOS only via `isIOS()`)
   - Handle auth state for Profile tab (show Login if not authenticated)
2. Update `Layout.tsx`:
   - Import and render TabBar on iOS
   - Hide Footer on iOS
   - Add padding-bottom for tab bar
3. Update `Header.tsx`:
   - Hide hamburger menu button on iOS
   - Hide desktop navigation items on iOS
   - Keep logo and user avatar
   - User avatar opens ActionSheet instead of dropdown on iOS

#### Phase 4: Replace Dropdowns with Action Sheets
1. Header "Add Recipe" menu → ActionSheet on iOS
2. Header user menu → ActionSheet on iOS
3. RecipeDetailPage mobile menu → ActionSheet on iOS

---

## Timeline
- Started: 2026-02-27T10:30:00Z
- Completed: 2026-02-27T10:50:00Z

## Deviations
None.

## Results Summary
Successfully implemented iOS Native UI Refactoring:

**New Files Created:**
- `frontend/src/utils/haptics.ts` - Haptic feedback utilities (light/medium/heavy impact, selection changed, notifications)
- `frontend/src/hooks/useHapticFeedback.ts` - React hook for haptic feedback
- `frontend/src/components/ui/ActionSheet.tsx` - iOS-style action sheet with slide-up animation and drag-to-dismiss
- `frontend/src/components/navigation/TabBar.tsx` - iOS bottom tab bar with 5 tabs and centered Add button

**Files Modified:**
- `frontend/package.json` - Added `@capacitor/haptics@8.0.1` dependency
- `frontend/src/components/ui/Button.tsx` - Added iOS touch states (active:scale-[0.97]) and haptic feedback on tap
- `frontend/src/index.css` - Added CSS variables for safe areas, tab bar styling, action sheet styling, touch feedback utilities
- `frontend/src/components/layout/Layout.tsx` - Conditionally renders TabBar on iOS, hides Footer, adds bottom padding
- `frontend/src/components/layout/Header.tsx` - Hides hamburger menu on iOS, shows user avatar that opens ActionSheet
- `frontend/src/pages/RecipeDetailPage.tsx` - Mobile menu uses ActionSheet on iOS instead of dropdown

**Key Implementation Details:**
- Platform detection via `isIOS() && isNativePlatform()` from existing platform utils
- TabBar shows 5 tabs: Home, Recipes, Add (centered with accent color), Books, Profile
- Add button opens ActionSheet with recipe creation options
- All changes are iOS-only - web and Android remain unchanged
- Build verified successful, iOS sync completed

# Fix Inconsistent Recipe Action Buttons on Web

**Task ID:** 2025-01-18-1615
**Status:** Completed

## Original Plan

### Problem
The recipe detail page action buttons have inconsistent styling on web:
- Different border radius (`rounded-md`, `rounded-lg` vs `rounded-full`)
- Different heights and padding
- Some use the shared `Button` component, others have custom styling

### Root Cause
Three button components implement their own button styling instead of using the shared `Button` component:
- `MakePublicButton` - uses `rounded-md`, custom size classes
- `FeatureToggleButton` - uses `rounded-lg`, hardcoded padding
- `ExportButton` - uses `rounded-md`, has `shadow-sm`, inline styles

### Solution
Refactor the three custom buttons to use the shared `Button` component.

### Files to Modify
1. `frontend/src/components/recipe/MakePublicButton.tsx`
2. `frontend/src/components/recipe/FeatureToggleButton.tsx`
3. `frontend/src/components/export/ExportButton.tsx`

## Timeline
- Started: 2025-01-18T16:15:00Z
- Completed: 2025-01-18T16:45:00Z

## Deviations
- 2025-01-18T16:35:00Z: Updated Button component size definitions to be more spacious (increased height and padding) for a more modern look. Final sizes: sm `h-10 px-6 gap-2`, md `h-12 px-8 gap-2`.

## Results Summary
Successfully fixed button consistency on the recipe detail page.

**Files modified:**
- `frontend/src/components/recipe/MakePublicButton.tsx` - Now uses shared Button component
- `frontend/src/components/recipe/FeatureToggleButton.tsx` - Now uses shared Button component, added size prop
- `frontend/src/components/export/ExportButton.tsx` - Now uses shared Button component, added size prop
- `frontend/src/components/ui/Button.tsx` - Increased button sizes for more spacious, modern look

**Result:**
All recipe action buttons now have consistent rounded-full styling, uniform heights, proper spacing, and a more modern appearance with generous padding.

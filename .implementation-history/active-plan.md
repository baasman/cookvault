# Fix Recipes Page: Default Tab & Back Navigation State

**Task ID:** 2026-04-23-0900
**Status:** In Progress

## Original Plan

The Recipes page defaults to the "Discover" tab, but authenticated users expect to see their own uploads first. Additionally, clicking a recipe and then navigating back always resets to the default tab instead of returning to whichever tab the user was on. Both issues stem from `activeFilter` being plain `useState('discover')` with no persistence.

### Approach: URL Search Params
Use `useSearchParams` to sync the active tab with `?tab=mine` in the URL. This fixes both issues at once:
- Default becomes `mine` (the "Uploads" tab) for authenticated users
- Back navigation restores the tab because the URL retains the query param

### Changes

**`frontend/src/pages/RecipesPage.tsx`**
- Import `useSearchParams` from `react-router-dom`
- Replace `useState<RecipeFilter>('discover')` with search-param-driven state
- Read initial tab from `searchParams.get('tab')`, defaulting to `'mine'` for authenticated users and `'discover'` for unauthenticated
- On tab change, call `setSearchParams({ tab: newTab }, { replace: true })`
- Remove the `useEffect` that forces `discover` for unauthenticated users

No other file changes needed.

## Timeline
- Started: 2026-04-23T09:00:00Z
- Completed:

## Deviations
None yet.

## Results Summary
[To be added on completion]

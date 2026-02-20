# Shared Ratings for URL-Imported Recipes

**Task ID:** 2026-02-20-1434
**Status:** Completed

## Original Plan

### Overview
Extend the rating aggregation system to share ratings across URL-imported recipes. When multiple users import the same URL, they'll see combined ratings from all copies, similar to how cookbook recipes aggregate by `normalized_title + cookbook_id`.

**Approach:** Each user keeps their own recipe copy, but ratings are aggregated by canonical source URL.

---

### Files Modified

| File | Changes |
|------|---------|
| `backend/app/models/recipe.py` | Added `canonical_source_url` field + event listener |
| `backend/app/services/rating_service.py` | Added `normalize_url()`, updated aggregation logic, added `backfill_canonical_source_urls()` |
| `backend/migrations/versions/h6i7j8k9l0m1_add_canonical_source_url.py` | New migration for `canonical_source_url` column |
| `frontend/src/types/index.ts` | Added `canonical_source_url` to `AggregateRating` interface |

---

### Implementation Details

#### Step 1: URL Normalization Utility
Added `normalize_url()` function to `rating_service.py`:
- Lowercases scheme and host
- Removes `www.` prefix
- Strips tracking params (utm_*, fbclid, gclid, etc.)
- Removes URL fragments
- Removes trailing slashes
- Sorts remaining query parameters

#### Step 2: Database Migration
Created migration `h6i7j8k9l0m1_add_canonical_source_url.py`:
- Added `canonical_source_url` column (String 500, nullable)
- Created index `ix_recipe_canonical_source_url`
- Backfilled existing recipes with source URLs

#### Step 3: Recipe Model Update
Added to `Recipe` model in `recipe.py`:
- `canonical_source_url` field
- Event listener `_recipe_source_set` that auto-populates `canonical_source_url` when `source` is set

#### Step 4: Rating Aggregation Update
Updated `get_aggregate_rating_for_recipe()` with three-tier strategy:
1. **Cookbook-based** (highest priority): aggregate by `normalized_title + cookbook_id`
2. **URL-based** (new): aggregate by `canonical_source_url` for URL-imported recipes
3. **Single recipe** (fallback): no cross-user matching

Also added `backfill_canonical_source_urls()` helper function.

#### Step 5: Frontend Type Update
Added `canonical_source_url: string | null` to `AggregateRating` interface.

---

## Timeline
- Started: 2026-02-20T14:34:00Z
- Completed: 2026-02-20T14:45:00Z

## Deviations
None.

## Results Summary
Successfully implemented shared ratings for URL-imported recipes:
- New recipes imported from URLs automatically have their `canonical_source_url` populated
- Rating aggregation now pools ratings across all recipes with matching canonical URLs
- Migration backfilled existing URL-imported recipes
- Frontend type updated for compatibility
- Event listener ensures automatic URL normalization on recipe creation/update

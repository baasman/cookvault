# Recipe Translation Feature

**Task ID:** 2026-02-08-1530
**Status:** Completed

## Original Plan

### Overview
Add automatic language detection and translation for recipes uploaded in foreign languages. When a user uploads a recipe image in a non-English language, the system will:
1. Detect the source language during OCR extraction
2. Translate the content to English during parsing
3. Store both original and translated versions for transparency

### Approach
Integrate translation into the existing `LLMOCRService` rather than adding a separate translation API. This:
- Minimizes API calls (translation happens during parsing, no extra call)
- Leverages Claude's multilingual capabilities already in use
- Reuses existing caching infrastructure

### Backend Changes

1. **Database Migration** - Add translation fields to models:
   - Recipe: `source_language`, `source_language_name`, `is_translated`, `original_title`, `original_description`
   - Instruction: `original_text`
   - ProcessingJob: `detected_language`, `detected_language_name`

2. **LLM OCR Service Updates** - Language detection and translation:
   - Update `_build_literal_extraction_prompt()` to detect language
   - Create `_parse_language_from_extraction()` helper
   - Update `_build_minimal_parsing_prompt()` for translation
   - Update `extract_and_parse_recipe()` to include language metadata

3. **Recipe Creation Updates** - Store translation data:
   - Update `_create_recipe_from_parsed_data()`
   - Update `_create_instructions()`

4. **API Response Updates** - Include translation fields

### Frontend Changes

1. **TypeScript Types** - Add translation fields to interfaces
2. **Recipe Detail Page** - Language indicator and original text toggle

### File Summary

| File | Action |
|------|--------|
| `backend/migrations/versions/xxx_add_translation_fields.py` | Create migration |
| `backend/app/models/recipe.py` | Add translation fields to models |
| `backend/app/services/llm_ocr_service.py` | Add language detection + translation |
| `backend/app/api/recipes.py` | Store translation data during creation |
| `frontend/src/types/index.ts` | Add TypeScript types |
| `frontend/src/pages/RecipeDetailPage.tsx` | Add UI for language indicator/toggle |

## Timeline
- Started: 2026-02-08T15:30:00Z
- Completed: 2026-02-09T10:55:00Z

## Deviations
- 2026-02-08T22:26:00Z: Updated migration down_revision from 'c1d2e3f4g5h6' to '22db193b35d3' to fix multiple heads issue. Another migration (add_account_deletion_fields) was created after the originally planned parent.

## Results Summary
Successfully implemented automatic language detection and translation for recipes:

**Backend Changes:**
- Created migration `d2e3f4g5h6i7_add_translation_fields.py` with SQLite batch mode support
- Added translation fields to Recipe, Instruction, and ProcessingJob models
- Updated `llm_ocr_service.py` with language detection in extraction prompt and translation in parsing prompt
- Updated `recipes.py` to store translation data during recipe creation

**Frontend Changes:**
- Added translation types to `types/index.ts`
- Updated `RecipeDetailPage.tsx` with "Translated from {language}" badge and toggle for viewing original text
- Fixed event propagation issue in `RecipeActionsDropdown.tsx` for Download button

**Key Files Modified:**
- `backend/migrations/versions/d2e3f4g5h6i7_add_translation_fields.py` (new)
- `backend/app/models/recipe.py`
- `backend/app/services/llm_ocr_service.py`
- `backend/app/api/recipes.py`
- `frontend/src/types/index.ts`
- `frontend/src/pages/RecipeDetailPage.tsx`
- `frontend/src/components/recipe/RecipeActionsDropdown.tsx`

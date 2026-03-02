import json
import re
import hashlib
from typing import Dict

import anthropic
import redis
from flask import current_app


class RecipeParser:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=current_app.config.get("ANTHROPIC_API_KEY")
        )
        self.redis_client = self._init_redis()
        self.cache_ttl = current_app.config.get(
            "RECIPE_CACHE_TTL", 86400
        )  # 24 hours default

    def _init_redis(self) -> redis.Redis:
        """Initialize Redis connection."""
        try:
            redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
            client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            client.ping()
            return client
        except Exception:
            # Fall back to None if Redis is unavailable
            return None

    def parse_recipe_text(
        self, ocr_text: str, use_cache: bool = True, translate_to_english: bool = False
    ) -> Dict:
        # Generate cache key from input text (include translate flag)
        translate_suffix = "_translated" if translate_to_english else ""
        cache_key = self._generate_cache_key(ocr_text) + translate_suffix

        # Check cache if enabled and Redis is available
        if use_cache and self.redis_client:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result

        prompt = self._build_parsing_prompt(
            ocr_text, translate_to_english=translate_to_english
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.0,
                system="You are a recipe parsing assistant.",
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            parsed_result = self._extract_json_from_response(content)

            # Cache the result if caching is enabled and Redis is available
            if use_cache and self.redis_client:
                self._set_in_cache(cache_key, parsed_result)

            return parsed_result

        except Exception as e:
            raise Exception(f"Recipe parsing failed: {str(e)}") from e

    def parse_multi_image_recipe(
        self,
        ocr_texts: list[str],
        use_cache: bool = True,
        quality_info: Dict = None,
        translate_to_english: bool = False,
    ) -> Dict:
        """Parse recipe from multiple OCR text blocks with enhanced text processing."""
        # Enhanced validation with better error messages
        if ocr_texts is None:
            raise ValueError("ocr_texts cannot be None")

        if not isinstance(ocr_texts, list):
            raise ValueError(f"ocr_texts must be a list, got {type(ocr_texts)}")

        if not ocr_texts:
            raise ValueError("At least one OCR text is required")

        # Filter out None/empty entries
        valid_texts = [
            text
            for text in ocr_texts
            if text and isinstance(text, str) and text.strip()
        ]

        if not valid_texts:
            raise ValueError(
                f"No valid text found in ocr_texts. Original count: {len(ocr_texts)}, valid count: 0"
            )

        if len(valid_texts) == 1:
            return self.parse_recipe_text(
                valid_texts[0], use_cache, translate_to_english
            )

        # Pre-process texts for better combination
        processed_texts = self._preprocess_multi_image_texts(valid_texts)

        # Combine texts for cache key generation (include translate flag)
        combined_text = "\n--- PAGE BREAK ---\n".join(processed_texts)
        translate_suffix = "_translated" if translate_to_english else ""
        cache_key = self._generate_cache_key(combined_text) + translate_suffix

        # Check cache if enabled and Redis is available
        if use_cache and self.redis_client:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result

        # Build enhanced prompt with quality information
        prompt = self._build_enhanced_multi_image_parsing_prompt(
            processed_texts, quality_info, translate_to_english
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,  # Increased for complex multi-page recipes
                temperature=0.0,
                system="You are an expert recipe parsing assistant specialized in combining multi-page recipes with advanced text processing capabilities.",
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            parsed_result = self._extract_json_from_response(content)

            # Post-process the result for multi-image specific improvements
            enhanced_result = self._enhance_multi_image_result(
                parsed_result, processed_texts
            )

            # Cache the result if caching is enabled and Redis is available
            if use_cache and self.redis_client:
                self._set_in_cache(cache_key, enhanced_result)

            return enhanced_result

        except Exception as e:
            current_app.logger.error(
                f"Multi-image recipe parsing failed: {str(e)}", exc_info=True
            )
            raise Exception(f"Multi-image recipe parsing failed: {str(e)}") from e

    def _preprocess_multi_image_texts(self, ocr_texts: list[str]) -> list[str]:
        """Pre-process OCR texts for better combination and parsing."""
        processed_texts = []

        for i, text in enumerate(ocr_texts):
            if not text.strip():
                processed_texts.append(f"[PAGE {i + 1}: NO TEXT EXTRACTED]")
                continue

            # Clean up common OCR artifacts
            cleaned_text = self._clean_ocr_text(text)

            # Add page context
            page_text = f"[PAGE {i + 1}]\n{cleaned_text}"
            processed_texts.append(page_text)

        return processed_texts

    def _clean_ocr_text(self, text: str) -> str:
        """Clean common OCR artifacts and improve text quality."""
        if not text:
            return text

        # Remove excessive whitespace and normalize line breaks
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        # Fix common OCR character misreadings
        ocr_fixes = {
            r"\b1\s*(?=[a-zA-Z])": "I ",  # 1 -> I at word boundaries
            r"\b0\s*(?=[a-zA-Z])": "O ",  # 0 -> O at word boundaries
            r"\b5\s*(?=[a-zA-Z])": "S ",  # 5 -> S at word boundaries
            r"\bcup5\b": "cups",
            r"\btbsp5\b": "tbsps",
            r"\btsp5\b": "tsps",
            r"\bteaspoon5\b": "teaspoons",
            r"\btablespoon5\b": "tablespoons",
        }

        for pattern, replacement in ocr_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Remove isolated single characters that are likely OCR noise
        text = re.sub(r"\n\s*[a-zA-Z]\s*\n", "\n", text)

        return text.strip()

    def _enhance_multi_image_result(
        self, parsed_result: Dict, processed_texts: list[str]
    ) -> Dict:
        """Enhance parsed result with multi-image specific improvements."""
        enhanced_result = parsed_result.copy()

        # Add metadata about multi-image processing
        enhanced_result["multi_image_metadata"] = {
            "total_pages": len(processed_texts),
            "processing_notes": [],
        }

        # Check for potential incomplete parsing
        if not enhanced_result.get("ingredients") or not enhanced_result.get(
            "instructions"
        ):
            enhanced_result["multi_image_metadata"]["processing_notes"].append(
                "Some recipe elements may be missing - manual review recommended"
            )

        # Validate ingredient and instruction counts seem reasonable
        ingredient_count = len(enhanced_result.get("ingredients", []))
        instruction_count = len(enhanced_result.get("instructions", []))

        if ingredient_count < 2:
            enhanced_result["multi_image_metadata"]["processing_notes"].append(
                f"Only {ingredient_count} ingredients found - may be incomplete"
            )

        if instruction_count < 2:
            enhanced_result["multi_image_metadata"]["processing_notes"].append(
                f"Only {instruction_count} instructions found - may be incomplete"
            )

        return enhanced_result

    def _build_enhanced_multi_image_parsing_prompt(
        self,
        processed_texts: list[str],
        quality_info: Dict = None,
        translate_to_english: bool = False,
    ) -> str:
        """Build enhanced prompt for multi-image parsing with quality context."""
        formatted_texts = "\n\n".join(processed_texts)

        # Add translation instructions if requested
        translation_instruction = ""
        if translate_to_english:
            translation_instruction = """
IMPORTANT - TRANSLATION REQUIRED:
The recipe text may be in a non-English language. You MUST:
1. Detect the source language
2. Translate ALL content (title, description, ingredients, instructions) to English
3. Keep the original title in the 'original_title' field
4. Keep the original description in the 'original_description' field
5. Store original instruction text in 'original_instructions' array
6. Add 'source_language' field with ISO 639-1 code (e.g., 'nl' for Dutch, 'fr' for French)
7. Add 'source_language_name' field with human-readable name (e.g., 'Dutch', 'French')
8. Set 'is_translated' to true

For ingredients: Translate ingredient names but preserve quantities and units.
For instructions: Translate the full instruction text to natural English.
"""

        quality_context = ""
        if quality_info:
            # Defensive check: ensure quality_info is a dictionary
            if not isinstance(quality_info, dict):
                current_app.logger.warning(
                    f"quality_info expected dict but got {type(quality_info)}: {quality_info}"
                )
                # Convert non-dict quality_info to safe format
                if isinstance(quality_info, (int, float)):
                    quality_info = {
                        "overall_quality": quality_info,
                        "completeness_score": {"score": "Unknown"},
                        "processing_summary": {"success_rate": "Unknown"},
                    }
                else:
                    quality_info = None

            if quality_info:
                # Extract values safely, handling both dict and direct values
                overall_quality = quality_info.get("overall_quality", "Unknown")

                completeness_data = quality_info.get("completeness_score", "Unknown")
                if isinstance(completeness_data, dict):
                    completeness_score = completeness_data.get("score", "Unknown")
                else:
                    completeness_score = completeness_data

                processing_data = quality_info.get("processing_summary", "Unknown")
                if isinstance(processing_data, dict):
                    success_rate = processing_data.get("success_rate", "Unknown")
                else:
                    success_rate = processing_data

                quality_context = f"""
QUALITY ASSESSMENT CONTEXT:
- Overall Quality: {overall_quality}/10
- Completeness Score: {completeness_score}/10
- Success Rate: {success_rate}%

Pay special attention to pages with lower quality scores and be more careful with text interpretation.
"""

        return f"""
Please parse this multi-page recipe and extract structured information in JSON format.
{translation_instruction}
{quality_context}

This recipe spans {len(processed_texts)} pages. Please combine all the information intelligently:

{formatted_texts}

ADVANCED PARSING INSTRUCTIONS:
1. **Text Combination**: Intelligently merge content from all pages, handling:
   - Split ingredients across pages (e.g., "2 cups" on page 1, "flour" on page 2)
   - Continuation of instruction steps across page breaks
   - Overlapping or duplicate content between pages
   - Missing or corrupted text due to OCR errors

2. **Content Detection**: Look for:
   - Recipe titles (often at the top of first page or standalone)
   - Ingredient lists (may use bullets, dashes, or numbers)
   - Instruction steps (numbered or paragraph format)
   - Cooking times, temperatures, and serving information
   - Yield/servings information

3. **Error Handling**: When encountering unclear text:
   - Make reasonable assumptions based on cooking context
   - Prefer complete words over fragments
   - Use surrounding context to interpret ambiguous characters
   - Flag uncertainty in your reasoning if needed

4. **Quality Assurance**: Ensure the final recipe:
   - Has logical ingredient quantities and units
   - Contains coherent step-by-step instructions
   - Maintains proper cooking terminology
   - Includes reasonable cooking times and temperatures

Return a JSON object with these fields:
- title: recipe name (combined from all pages) - IN ENGLISH if translation requested
- description: brief description (if any, from any page) - IN ENGLISH if translation requested
- ingredients: array of ingredient strings (intelligently combined from all pages) - IN ENGLISH if translation requested
- instructions: array of instruction steps (merged in logical order) - IN ENGLISH if translation requested
- prep_time: preparation time in minutes (if mentioned on any page)
- cook_time: cooking time in minutes (if mentioned on any page)
- servings: number of servings (if mentioned on any page)
- difficulty: easy/medium/hard (if mentioned or can be inferred)
- course_type: MUST be one of: "Appetizer", "Soup", "Salad", "Main Course", "Side Dish", "Bread", "Dessert", "Beverage", "Sauce/Condiment", "Snack". Infer from recipe name, ingredients, and context. Use null if uncertain.
- tags: array of relevant tags/categories (from all pages)
- parsing_confidence: your confidence level in the parsing (high/medium/low)
- parsing_notes: any concerns or observations about the text quality or parsing
- source_language: ISO 639-1 language code if translated (e.g., 'nl', 'fr', 'de')
- source_language_name: human-readable language name if translated (e.g., 'Dutch', 'French')
- is_translated: true if content was translated, false otherwise
- original_title: original title before translation (if translated)
- original_description: original description before translation (if translated)
- original_instructions: array of original instruction texts before translation (if translated)

If any information is not available or unclear, use null for that field.
"""

    def _generate_cache_key(self, ocr_text: str) -> str:
        """Generate a hash-based cache key from the OCR text."""
        normalized_text = ocr_text.strip().lower()
        hash_key = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        return f"recipe_parse:{hash_key}"

    def _get_from_cache(self, cache_key: str) -> Dict:
        """Get parsed recipe from Redis cache."""
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass
        return None

    def _set_in_cache(self, cache_key: str, parsed_result: Dict) -> None:
        """Store parsed recipe in Redis cache."""
        try:
            self.redis_client.setex(
                cache_key, self.cache_ttl, json.dumps(parsed_result)
            )
        except Exception:
            pass

    def clear_cache(self) -> None:
        """Clear all recipe parsing cache entries."""
        if self.redis_client:
            try:
                keys = self.redis_client.keys("recipe_parse:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception:
                pass

    def get_cache_size(self) -> int:
        """Get the current cache size."""
        if self.redis_client:
            try:
                return len(self.redis_client.keys("recipe_parse:*"))
            except Exception:
                pass
        return 0

    def _build_parsing_prompt(
        self, ocr_text: str, translate_to_english: bool = False
    ) -> str:
        if translate_to_english:
            return f"""
Please parse this recipe text and extract structured information.

ORIGINAL TEXT:
{ocr_text}

LANGUAGE AND TRANSLATION:
1. First, detect the language of the recipe text
2. If the recipe is NOT in English, translate all content to English
3. For translated recipes, preserve the original text in "original_*" fields

FIDELITY REQUIREMENTS:
1. Preserve meaning and measurements accurately
2. Keep quantities and measurements exactly as shown (1/2, not 0.5)
3. Use null for missing information - do not infer or add content

Return a JSON object with these fields:
- title: recipe name (translated to English if needed) or null
- original_title: original language title if translated, otherwise null
- description: description text (translated to English if needed) or null
- original_description: original language description if translated, otherwise null
- ingredients: array of ingredient strings (translated to English if needed)
- original_ingredients: array of original ingredient strings if translated, otherwise null
- instructions: array of instruction steps (translated to English if needed)
- original_instructions: array of original instruction steps if translated, otherwise null
- prep_time: time in minutes only if explicitly stated, otherwise null
- cook_time: time in minutes only if explicitly stated, otherwise null
- servings: exact servings text/number as written or null
- difficulty: only if explicitly stated, otherwise null
- course_type: MUST be one of: "Appetizer", "Soup", "Salad", "Main Course", "Side Dish", "Bread", "Dessert", "Beverage", "Sauce/Condiment", "Snack". Infer from recipe name, ingredients, and context. Use null if uncertain.
- tags: array of relevant tags (do not infer)
- source_language: ISO 639-1 code (e.g., 'fr', 'es', 'en') or null
- source_language_name: human-readable language name (e.g., 'French', 'Spanish', 'English') or null
- is_translated: true if the recipe was translated, false otherwise

Return ONLY valid JSON, no markdown, no additional text.
"""
        else:
            return f"""
Please parse this recipe text and extract structured information with EXACT text preservation.

ORIGINAL TEXT:
{ocr_text}

LANGUAGE DETECTION:
1. Detect the language of the recipe text
2. DO NOT translate - preserve the original language exactly

FIDELITY REQUIREMENTS:
1. Preserve ALL text exactly as written - do not rephrase or improve
2. Maintain original spelling, punctuation, and capitalization
3. Keep quantities and measurements exactly as shown (1/2, not 0.5)
4. Use ingredient text verbatim - do not standardize names
5. Copy instruction steps word-for-word
6. Use null for missing information - do not infer or add content

Return a JSON object with these fields:
- title: exact recipe name from text or null
- description: exact description text or null
- ingredients: array of exact ingredient strings as written
- instructions: array of exact instruction steps as written
- prep_time: time in minutes only if explicitly stated, otherwise null
- cook_time: time in minutes only if explicitly stated, otherwise null
- servings: exact servings text/number as written or null
- difficulty: only if explicitly stated, otherwise null
- course_type: MUST be one of: "Appetizer", "Soup", "Salad", "Main Course", "Side Dish", "Bread", "Dessert", "Beverage", "Sauce/Condiment", "Snack". Infer from recipe name, ingredients, and context. Use null if uncertain.
- tags: array of relevant tags from text (do not infer)
- source_language: ISO 639-1 code (e.g., 'fr', 'es', 'en') or null
- source_language_name: human-readable language name (e.g., 'French', 'Spanish', 'English') or null
- is_translated: false (since translation was not requested)

Return ONLY valid JSON, no markdown, no additional text.
"""

    def _build_multi_image_parsing_prompt(self, ocr_texts: list[str]) -> str:
        formatted_texts = []
        for i, text in enumerate(ocr_texts, 1):
            formatted_texts.append(f"=== PAGE {i} ===\n{text}")

        combined_text = "\n\n".join(formatted_texts)

        return f"""
Please parse this multi-page recipe and extract structured information in JSON format.

This recipe spans {len(ocr_texts)} pages. Please combine all the information intelligently:

{combined_text}

Instructions for multi-page parsing:
- Combine ingredients from all pages into a single list
- Merge instruction steps in logical order, maintaining the sequence across pages
- If ingredients or instructions are split across pages, merge them appropriately
- Use the title from the first page that has one, or combine if the title spans pages
- Combine any notes, tips, or additional information from all pages
- If cooking times appear on different pages, use the most complete information

Return a JSON object with these fields:
- title: recipe name (combined from all pages)
- description: brief description (if any, from any page)
- ingredients: array of ingredient strings (combined from all pages)
- instructions: array of instruction steps (merged in logical order)
- prep_time: preparation time in minutes (if mentioned on any page)
- cook_time: cooking time in minutes (if mentioned on any page)
- servings: number of servings (if mentioned on any page)
- difficulty: easy/medium/hard (if mentioned or can be inferred)
- course_type: MUST be one of: "Appetizer", "Soup", "Salad", "Main Course", "Side Dish", "Bread", "Dessert", "Beverage", "Sauce/Condiment", "Snack". Infer from recipe name, ingredients, and context. Use null if uncertain.
- tags: array of relevant tags/categories (from all pages)

If any information is not available or unclear, use null for that field.
"""

    def _extract_json_from_response(self, response: str) -> Dict:
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in response")

        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {str(e)}")

import base64
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Dict, Optional

import anthropic
import redis
from flask import current_app
from PIL import Image

from app.exceptions import OCRExtractionError


class LLMOCRService:
    """Service for LLM-based text extraction from images using Anthropic Claude."""

    def __init__(self):
        api_key = current_app.config.get("ANTHROPIC_API_KEY")
        if not api_key:
            current_app.logger.error("ANTHROPIC_API_KEY not configured!")
            raise ValueError("ANTHROPIC_API_KEY is required for LLM OCR service")

        current_app.logger.info(
            f"Initializing Anthropic client with API key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 10 else 'short'}"
        )

        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=90.0,  # 90 second timeout for API calls
        )
        self.redis_client = self._init_redis()
        self.cache_ttl = current_app.config.get(
            "OCR_QUALITY_CACHE_TTL", 3600
        )  # 1 hour default

        # Load model IDs from config for flexibility
        self.vision_model = current_app.config.get(
            "ANTHROPIC_VISION_MODEL", "claude-sonnet-4-5-20250929"
        )
        self.text_model = current_app.config.get(
            "ANTHROPIC_TEXT_MODEL", "claude-sonnet-4-20250514"
        )

        current_app.logger.info(
            f"LLM OCR Service initialized with vision_model={self.vision_model}, text_model={self.text_model}"
        )

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

    def _make_api_call_with_retry(
        self, api_call_func, max_retries: int = 3, base_delay: float = 1.0
    ):
        """
        Make an API call with exponential backoff retry logic.

        Args:
            api_call_func: Function that makes the API call
            max_retries: Maximum number of retries (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)

        Returns:
            API response

        Raises:
            OCRExtractionError: If all retries are exhausted
        """
        for attempt in range(max_retries + 1):
            try:
                return api_call_func()
            except Exception as e:
                # Check if it's a retryable error (overloaded, rate limit, timeout)
                is_retryable = False
                error_message = str(e).lower()

                if hasattr(e, "status_code"):
                    # HTTP status codes that should be retried
                    retryable_status_codes = {429, 500, 502, 503, 504, 529}
                    is_retryable = e.status_code in retryable_status_codes
                elif any(
                    keyword in error_message
                    for keyword in ["overloaded", "rate limit", "timeout", "connection"]
                ):
                    is_retryable = True

                # If this is the last attempt or error is not retryable, raise the exception
                if attempt == max_retries or not is_retryable:
                    current_app.logger.error(
                        f"API call failed after {attempt + 1} attempts: {str(e)}"
                    )
                    raise

                # Calculate delay with exponential backoff and jitter
                delay = base_delay * (2**attempt) + (time.time() % 1)  # Add jitter
                current_app.logger.warning(
                    f"API call failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay:.1f}s: {str(e)}"
                )
                time.sleep(delay)

    def _build_literal_extraction_prompt(self) -> str:
        """Build a prompt focused purely on literal text extraction with language detection."""
        return """
This is a page from a published cookbook. Your task is to transcribe the recipe text for a cookbook digitization application.

LANGUAGE DETECTION:
At the very beginning of your response, on a single line, indicate the detected language of the recipe:
[LANGUAGE: <iso_code>|<language_name>]
Example: [LANGUAGE: fr|French]
Example: [LANGUAGE: en|English]
Example: [LANGUAGE: es|Spanish]
Example: [LANGUAGE: zh|Chinese]
Example: [LANGUAGE: de|German]
Example: [LANGUAGE: it|Italian]
Example: [LANGUAGE: ja|Japanese]
Example: [LANGUAGE: ko|Korean]
Example: [LANGUAGE: pt|Portuguese]

Use the ISO 639-1 two-letter language code. If you cannot determine the language, use: [LANGUAGE: en|English]

EXTRACTION RULES:
1. Transcribe EVERY word exactly as written - preserve spelling, punctuation, capitalization
2. Maintain the visual layout and structure (line breaks, sections)
3. Do NOT interpret, correct, or modify any text
4. Do NOT add explanations, formatting, or structure
5. Include ALL text: titles, ingredients, cooking instructions, notes, times, etc.
6. Preserve numbers and fractions exactly (1/2, 2-3, etc.)

This is standard culinary content from a professionally published cookbook. After the language tag, return ONLY the raw extracted text, exactly as you see it in the image.
"""

    def _parse_language_from_extraction(self, extracted_text: str) -> tuple:
        """
        Parse the language tag from the extraction response.

        Args:
            extracted_text: The raw extraction response that may contain a language tag

        Returns:
            Tuple of (language_code, language_name, cleaned_text)
            Defaults to ('en', 'English', extracted_text) if no tag found
        """
        # Default values
        language_code = "en"
        language_name = "English"
        cleaned_text = extracted_text

        # Try to parse the language tag from the beginning of the response
        # Format: [LANGUAGE: <iso_code>|<language_name>]
        language_pattern = re.compile(
            r"^\s*\[LANGUAGE:\s*([a-z]{2,3})\|([^\]]+)\]\s*",
            re.IGNORECASE | re.MULTILINE,
        )
        match = language_pattern.match(extracted_text)

        if match:
            language_code = match.group(1).lower()
            language_name = match.group(2).strip()
            # Remove the language tag from the extracted text
            cleaned_text = extracted_text[match.end() :].strip()
            current_app.logger.info(
                f"Detected language: {language_code} ({language_name})"
            )
        else:
            current_app.logger.info(
                "No language tag found in extraction, defaulting to English"
            )

        return (language_code, language_name, cleaned_text)

    def _build_minimal_parsing_prompt(
        self,
        extracted_text: str,
        source_language: str = None,
        source_language_name: str = None,
    ) -> str:
        """Build a prompt for minimal parsing of already-extracted text, with optional translation."""
        # Determine if translation is needed
        needs_translation = source_language and source_language.lower() != "en"

        translation_instructions = ""
        if needs_translation:
            translation_instructions = f"""
TRANSLATION REQUIRED:
The original text is in {source_language_name} ({source_language}). You MUST:
1. Translate ALL content to English
2. For each translated field, also provide the original text in "original_*" fields
3. Translate ingredient names, quantities descriptions, and instructions
4. Keep measurements in their original units (do not convert)
5. Translate cooking terms appropriately (e.g., "cuillère à soupe" -> "tablespoon")

"""

        original_fields = ""
        if needs_translation:
            original_fields = """
    "original_title": "original title in source language or null",
    "original_description": "original description in source language or null",
    "original_ingredients": [
        "original ingredient line 1 in source language",
        "original ingredient line 2 in source language"
    ],
    "original_instructions": [
        "original instruction step 1 in source language",
        "original instruction step 2 in source language"
    ],"""

        return f"""
You have been given text that was literally extracted from a recipe image. Your job is to organize it into a structured format with MINIMAL changes.
{translation_instructions}
EXTRACTED TEXT:
{extracted_text}

STRUCTURING RULES:
1. {"Translate to English while preserving the meaning" if needs_translation else "Use the text EXACTLY as provided - do not rephrase or improve"}
2. Only add structure (JSON format) - {"translate but" if needs_translation else ""} preserve all original wording
3. Split into logical sections (title, ingredients, instructions) based on context
4. Maintain exact quantities, measurements, and ingredient names
5. {"Translate instruction text while preserving cooking steps" if needs_translation else "Keep instruction text word-for-word from the extraction"}
6. Use null for any missing information - do not infer or add content

Return a JSON object with this structure:
{{
    "title": "{"translated " if needs_translation else ""}title from text or null",
    "description": "{"translated " if needs_translation else ""}description from text or null",{original_fields}
    "prep_time": time_in_minutes_if_explicitly_stated_or_null,
    "cook_time": time_in_minutes_if_explicitly_stated_or_null,
    "total_time": time_in_minutes_if_explicitly_stated_or_null,
    "servings": "{"translated " if needs_translation else ""}servings_text_or_null",
    "difficulty": "only_if_explicitly_stated_or_null",
    "ingredients": [
        "{"translated " if needs_translation else ""}ingredient line 1",
        "{"translated " if needs_translation else ""}ingredient line 2"
    ],
    "instructions": [
        "{"translated " if needs_translation else ""}instruction step 1",
        "{"translated " if needs_translation else ""}instruction step 2"
    ],
    "tags": [],
    "source": "source_if_visible_or_null"
}}

Return ONLY valid JSON, no markdown, no additional text.
"""

    def _parse_minimal_response(self, response_text: str) -> dict:
        """Parse the minimal parsing LLM response into structured data."""

        try:
            # Clean up response text - sometimes LLM adds markdown formatting
            json_text = response_text.strip()
            if json_text.startswith("```json"):
                json_text = re.sub(r"^```json\s*", "", json_text)
            if json_text.endswith("```"):
                json_text = re.sub(r"\s*```$", "", json_text)

            # Parse JSON response
            recipe_data = json.loads(json_text)

            # Validate and clean up critical fields to prevent database constraint violations
            recipe_data = self._validate_and_clean_recipe_data(recipe_data)

            current_app.logger.info(
                f"Minimal parsing returned {len(recipe_data.get('ingredients', []))} ingredients and {len(recipe_data.get('instructions', []))} instructions"
            )

            return recipe_data

        except (json.JSONDecodeError, ValueError) as e:
            current_app.logger.error(f"Failed to parse minimal LLM response: {str(e)}")
            current_app.logger.error(f"Raw response: {response_text[:500]}...")

            # Fallback: return minimal but valid structure
            return self._get_fallback_recipe_structure(str(e))

    def _safe_int_conversion(self, value, field_name: str) -> Optional[int]:
        """Safely convert a value to integer, handling ranges and special cases."""
        if value is None:
            return None

        try:
            # If already an integer, return it
            if isinstance(value, int):
                return value

            # Convert to string and clean up
            value_str = str(value).strip()
            if not value_str:
                return None

            # Handle range values like "8-10", "4-6 servings", "2-3 hours", "2 to 4 servings"
            # Look for patterns like "8-10", "4-6", "2 to 4", etc.
            range_match = re.search(r"(\d+)\s*(?:[-–—]|to)\s*(\d+)", value_str)
            if range_match:
                start_val = int(range_match.group(1))
                end_val = int(range_match.group(2))
                # Take the average of the range, rounded down
                result = (start_val + end_val) // 2
                current_app.logger.info(
                    f"Converted range '{value_str}' to {result} for field '{field_name}'"
                )
                return result

            # Look for single numbers (ignoring text like "servings", "minutes", etc.)
            number_match = re.search(r"(\d+)", value_str)
            if number_match:
                result = int(number_match.group(1))
                current_app.logger.debug(
                    f"Extracted number {result} from '{value_str}' for field '{field_name}'"
                )
                return result

            # Try direct conversion as fallback
            return int(value_str)

        except (ValueError, TypeError, AttributeError) as e:
            current_app.logger.warning(
                f"Could not convert '{value}' to integer for field '{field_name}': {str(e)}"
            )
            return None

    def _validate_and_clean_recipe_data(self, recipe_data: dict) -> dict:
        """Validate and clean recipe data to prevent database constraint violations."""
        # Ensure title is never None or empty
        title = recipe_data.get("title")
        if not title or not str(title).strip():
            current_app.logger.warning(
                "LLM returned null/empty title, will be handled by fallback logic"
            )
            recipe_data["title"] = (
                None  # Let the calling code handle this with fallbacks
            )

        # Ensure ingredients is a list
        if "ingredients" in recipe_data and not isinstance(
            recipe_data["ingredients"], list
        ):
            current_app.logger.warning(
                "LLM returned ingredients in wrong format, converting to list"
            )
            recipe_data["ingredients"] = []

        # Ensure instructions is a list
        if "instructions" in recipe_data and not isinstance(
            recipe_data["instructions"], list
        ):
            current_app.logger.warning(
                "LLM returned instructions in wrong format, converting to list"
            )
            recipe_data["instructions"] = []

        # Clean up text fields to prevent issues
        text_fields = ["title", "description", "difficulty", "source"]
        for field in text_fields:
            if field in recipe_data and recipe_data[field] is not None:
                # Ensure it's a string and clean it up
                value = str(recipe_data[field]).strip()
                recipe_data[field] = value if value else None

        # Validate numeric fields with improved range handling
        numeric_fields = ["prep_time", "cook_time", "total_time", "servings"]
        for field in numeric_fields:
            if field in recipe_data and recipe_data[field] is not None:
                recipe_data[field] = self._safe_int_conversion(
                    recipe_data[field], field
                )

        # Ensure tags is a list
        if "tags" not in recipe_data or not isinstance(recipe_data["tags"], list):
            recipe_data["tags"] = []

        return recipe_data

    def _get_fallback_recipe_structure(self, error_msg: str = None) -> dict:
        """Return a minimal but valid recipe structure for fallback."""
        from datetime import datetime

        fallback_title = (
            f"Recipe extracted on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        return {
            "title": fallback_title,
            "description": "Recipe extracted from image"
            + (f" (Error: {error_msg})" if error_msg else ""),
            "ingredients": [],
            "instructions": [],
            "prep_time": None,
            "cook_time": None,
            "total_time": None,
            "servings": None,
            "difficulty": None,
            "tags": [],
            "source": None,
            "parsing_error": error_msg,
        }

    def extract_and_parse_recipe(
        self,
        image_data: bytes,
        source_info: str = "",
        use_cache: bool = True,
        translate_to_english: bool = False,
    ) -> dict:
        """
        Extract text from image using true two-step approach: literal extraction first, then minimal parsing.
        This ensures maximum fidelity to the source text.
        Includes language detection and optional translation for non-English recipes.

        Args:
            image_data: Image data as bytes
            source_info: Optional string for logging (path or URL)
            use_cache: Whether to use caching for the extraction
            translate_to_english: Whether to translate non-English recipes to English

        Returns:
            Dictionary containing extracted text, parsed recipe data, and language metadata
        """
        try:
            # Generate cache key from image content (v4 with translate flag)
            translate_suffix = "_translated" if translate_to_english else ""
            cache_key = f"recipe_extract_parse_v4_{self._generate_cache_key_from_data(image_data)}{translate_suffix}"

            # Check cache if enabled and Redis is available
            if use_cache and self.redis_client:
                cached_result = self._get_from_cache(cache_key)
                if cached_result and self._validate_cached_result(cached_result):
                    current_app.logger.info(
                        "Using cached two-step extract+parse result"
                    )
                    return cached_result
                elif cached_result:
                    current_app.logger.warning(
                        "Cached result failed validation, invalidating cache"
                    )
                    self._invalidate_cache(cache_key)

            # STEP 1: Pure literal text extraction with language detection
            current_app.logger.info(
                "Step 1: Starting literal text extraction with language detection"
            )
            raw_extracted_text = self._extract_literal_text(image_data, source_info)

            # Parse language from extraction response
            language_code, language_name, extracted_text = (
                self._parse_language_from_extraction(raw_extracted_text)
            )

            # Determine if translation is needed (only if user opted in AND language is not English)
            is_non_english = language_code.lower() != "en"
            is_translated = translate_to_english and is_non_english
            current_app.logger.info(
                f"Language: {language_code} ({language_name}), Non-English: {is_non_english}, Translate requested: {translate_to_english}, Will translate: {is_translated}"
            )

            # STEP 2: Minimal parsing of extracted text (with translation if needed)
            current_app.logger.info(
                "Step 2: Starting minimal parsing of extracted text"
            )
            parsed_recipe = self._parse_extracted_text(
                extracted_text,
                source_language=language_code if is_translated else None,
                source_language_name=language_name if is_translated else None,
            )

            # Add language metadata to parsed recipe
            parsed_recipe["source_language"] = language_code
            parsed_recipe["source_language_name"] = language_name
            parsed_recipe["is_translated"] = is_translated

            # Combine results
            result = {
                "text": extracted_text,  # Use cleaned text without language tag
                "parsed_recipe": parsed_recipe,
                "method": "two_step_literal",
                "quality_score": 10,
                "success": True,
                # Language metadata at top level for easy access
                "detected_language": language_code,
                "detected_language_name": language_name,
                "is_translated": is_translated,
            }

            # Cache the result if caching is enabled and Redis is available
            if use_cache and self.redis_client:
                self._set_in_cache(cache_key, result)

            current_app.logger.info(
                f"Two-step extract+parse completed successfully (language: {language_name})"
            )
            return result

        except Exception as e:
            current_app.logger.error(f"Two-step extract+parse failed: {str(e)}")
            raise OCRExtractionError(
                f"Two-step extract+parse failed: {str(e)}", e
            ) from e

    def _extract_literal_text(self, image_data: bytes, source_info: str = "") -> str:
        """Step 1: Extract literal text with no interpretation."""
        try:
            current_app.logger.info(
                f"Starting literal text extraction for: {source_info}"
            )

            # Prepare optimized image for LLM
            prepared_image = self._prepare_image_for_llm(image_data, source_info)

            # Literal extraction prompt
            prompt = self._build_literal_extraction_prompt()

            current_app.logger.info("Making LLM API call for literal text extraction")

            # System prompt for culinary context
            system_prompt = "You are a culinary text transcription specialist for a cookbook digitization service. You transcribe recipe text from published cookbook pages. This is standard culinary/cooking content. Extract every visible word exactly as written."

            # Message content (reusable for fallback)
            message_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": prepared_image["media_type"],
                        "data": prepared_image["data"],
                    },
                },
                {"type": "text", "text": prompt},
            ]

            # LLM call for pure text extraction with retry logic
            def make_api_call():
                return self.client.messages.create(
                    model=self.vision_model,
                    max_tokens=2000,
                    temperature=0.0,  # Maximum determinism
                    system=system_prompt,
                    messages=[{"role": "user", "content": message_content}],
                )

            # Fallback to haiku if content filtering triggers
            def make_api_call_fallback():
                current_app.logger.info(
                    "Trying fallback model claude-3-haiku-20240307 due to content filtering"
                )
                return self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=2000,
                    temperature=0.0,
                    system=system_prompt,
                    messages=[{"role": "user", "content": message_content}],
                )

            try:
                response = self._make_api_call_with_retry(make_api_call)
            except anthropic.BadRequestError as api_error:
                error_str = str(api_error).lower()
                current_app.logger.error(
                    f"Anthropic API BadRequestError: {str(api_error)}"
                )
                if hasattr(api_error, "status_code"):
                    current_app.logger.error(
                        f"API status code: {api_error.status_code}"
                    )
                if hasattr(api_error, "response"):
                    current_app.logger.error(f"API response: {api_error.response}")
                # Check for content filtering specifically - try fallback model
                if "content filtering" in error_str or "blocked" in error_str:
                    current_app.logger.warning(
                        f"Content filter triggered for image: {source_info}, trying fallback model"
                    )
                    try:
                        response = self._make_api_call_with_retry(
                            make_api_call_fallback
                        )
                        current_app.logger.info("Fallback model succeeded")
                    except anthropic.BadRequestError as fallback_error:
                        current_app.logger.error(
                            f"Fallback model also blocked: {str(fallback_error)}"
                        )
                        raise OCRExtractionError(
                            "This recipe image couldn't be processed due to content restrictions. Please try a different image.",
                            api_error,
                        )
                else:
                    raise
            except Exception as api_error:
                current_app.logger.error(
                    f"Anthropic API call failed after all retries: {str(api_error)}"
                )
                if hasattr(api_error, "status_code"):
                    current_app.logger.error(
                        f"API status code: {api_error.status_code}"
                    )
                if hasattr(api_error, "response"):
                    current_app.logger.error(f"API response: {api_error.response}")
                raise

            extracted_text = response.content[0].text.strip()
            current_app.logger.info(
                f"Literal extraction completed. Text length: {len(extracted_text)} characters"
            )
            current_app.logger.info(
                f"First 200 chars of extracted text: {extracted_text[:200]}..."
            )

            return extracted_text

        except Exception as e:
            current_app.logger.error(
                f"Literal text extraction failed: {str(e)}", exc_info=True
            )
            raise

    def _parse_extracted_text(
        self,
        extracted_text: str,
        source_language: str = None,
        source_language_name: str = None,
    ) -> dict:
        """Step 2: Minimally parse the already-extracted text, with optional translation."""
        # Minimal parsing prompt (includes translation instructions if source_language is non-English)
        prompt = self._build_minimal_parsing_prompt(
            extracted_text, source_language, source_language_name
        )

        # Adjust system prompt for translation
        if source_language and source_language.lower() != "en":
            system_prompt = f"You are a recipe structuring and translation assistant. Translate recipe content from {source_language_name} to English while organizing it into structured format. Preserve original text in original_* fields."
        else:
            system_prompt = "You are a recipe structuring assistant. Organize extracted text with minimal changes."

        # LLM call for minimal parsing with retry logic
        def make_api_call():
            return self.client.messages.create(
                model=self.text_model,
                max_tokens=4000,  # Increased for translation + original text
                temperature=0.0,  # Maximum determinism
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

        response = self._make_api_call_with_retry(make_api_call)
        response_text = response.content[0].text.strip()
        return self._parse_minimal_response(response_text)

    def extract_text_from_image(
        self, image_data: bytes, source_info: str = "", use_cache: bool = True
    ) -> str:
        """
        Extract text from image using Claude vision capabilities.

        Args:
            image_path: Path to the image file
            use_cache: Whether to use caching for the extraction

        Returns:
            Extracted text optimized for recipe parsing
        """
        try:
            # Generate cache key from image content
            cache_key = self._generate_cache_key_from_data(image_data)

            # Check cache if enabled and Redis is available
            if use_cache and self.redis_client:
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    return cached_result

            # Convert image to base64
            prepared_image = self._prepare_image_for_llm(image_data, source_info)

            prompt = self._build_extraction_prompt()

            # LLM call with retry logic
            def make_api_call():
                return self.client.messages.create(
                    model=self.vision_model,
                    max_tokens=2000,
                    temperature=0.0,
                    system="You are an expert at extracting text from recipe images with high accuracy and attention to detail.",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": prepared_image["media_type"],
                                        "data": prepared_image["data"],
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                )

            response = self._make_api_call_with_retry(make_api_call)

            extracted_text = response.content[0].text.strip()

            # Cache the result if caching is enabled and Redis is available
            if use_cache and self.redis_client:
                self._set_in_cache(cache_key, extracted_text)

            return extracted_text

        except Exception as e:
            current_app.logger.error(f"LLM OCR extraction failed: {str(e)}")
            raise OCRExtractionError(f"LLM OCR extraction failed: {str(e)}", e) from e

    def _prepare_image_for_llm(
        self, image_data: bytes, source_info: str = ""
    ) -> Dict[str, str]:
        """
        Prepare image for LLM processing with aggressive optimization to reduce memory usage.

        Args:
            image_data: Image data as bytes
            source_info: Optional string for logging (path or URL)

        Returns:
            Dictionary with base64 data and media type
        """
        import io
        import gc

        try:
            current_app.logger.info(f"Preparing image for LLM: {source_info}")

            # Get original file size for logging
            original_size_mb = len(image_data) / (1024 * 1024)
            current_app.logger.info(f"Original image size: {original_size_mb:.1f}MB")

            # Open and aggressively optimize image to reduce memory usage
            # Keep buffer open until all PIL operations complete (PIL lazy-loads)
            with Image.open(io.BytesIO(image_data)) as img:
                original_dimensions = img.size
                current_app.logger.info(
                    f"Original dimensions: {original_dimensions[0]}x{original_dimensions[1]}"
                )

                # Force full load of image data before any transformations
                img.load()

                # Convert to RGB if needed (more memory efficient than keeping alpha channels)
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")

                # Get max size from config (production may have different settings)
                max_size = current_app.config.get(
                    "MAX_IMAGE_DIMENSION", 1568
                )  # Keep higher default for better OCR
                current_app.logger.info(f"Using MAX_IMAGE_DIMENSION: {max_size}px")
                if img.width > max_size or img.height > max_size:
                    # Calculate new dimensions maintaining aspect ratio
                    ratio = min(max_size / img.width, max_size / img.height)
                    new_width = int(img.width * ratio)
                    new_height = int(img.height * ratio)

                    # Use LANCZOS for quality, but resize aggressively
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    current_app.logger.info(f"Resized to: {new_width}x{new_height}")

                # Compress as JPEG with configurable quality to reduce file size
                output_buffer = io.BytesIO()
                jpeg_quality = current_app.config.get(
                    "JPEG_QUALITY", 95
                )  # Use higher quality for better OCR
                current_app.logger.info(f"Using JPEG_QUALITY: {jpeg_quality}%")
                img.save(
                    output_buffer, format="JPEG", quality=jpeg_quality, optimize=True
                )

            # Image context manager closed - PIL resources freed
            gc.collect()

            # Get compressed size for logging
            compressed_size = output_buffer.tell()
            compressed_size_mb = compressed_size / (1024 * 1024)
            current_app.logger.info(
                f"Compressed image size: {compressed_size_mb:.1f}MB (reduction: {((original_size_mb - compressed_size_mb) / original_size_mb * 100):.1f}%)"
            )

            # Get the bytes and immediately close buffer
            output_buffer.seek(0)
            img_bytes = output_buffer.read()
            output_buffer.close()
            del output_buffer

            # Force garbage collection after image processing
            gc.collect()

            # Encode to base64 - must encode entire image at once for valid base64
            # (chunked encoding corrupts data because base64 works on 3-byte groups)
            base64_data = base64.b64encode(img_bytes).decode("utf-8")
            del img_bytes  # Free the original bytes data

            # Force garbage collection after encoding
            gc.collect()

            current_app.logger.info(
                "Base64 encoded image ready for LLM (final memory optimization complete)"
            )

            return {"data": base64_data, "media_type": "image/jpeg"}

        except Exception as e:
            # Force garbage collection even on error
            gc.collect()
            current_app.logger.error(f"Failed to prepare image for LLM: {str(e)}")
            raise OCRExtractionError(
                f"Failed to prepare image for LLM: {str(e)}", e
            ) from e

    def _generate_cache_key_from_data(self, image_data: bytes) -> str:
        """Generate a hash-based cache key from image data."""
        hash_key = hashlib.sha256(image_data).hexdigest()
        return f"llm_ocr:{hash_key}"

    def _generate_cache_key(self, image_path: Path) -> str:
        """Generate a hash-based cache key from the image file."""
        try:
            # Use file content hash for cache key
            with open(image_path, "rb") as f:
                image_content = f.read()

            return self._generate_cache_key_from_data(image_content)
        except Exception:
            # Fallback to path-based key if file reading fails
            hash_key = hashlib.sha256(str(image_path).encode("utf-8")).hexdigest()
            return f"llm_ocr:{hash_key}"

    def _get_from_cache(self, cache_key: str) -> str:
        """Get extracted text from Redis cache."""
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass
        return None

    def _set_in_cache(self, cache_key: str, extracted_text: str) -> None:
        """Store extracted text in Redis cache."""
        try:
            self.redis_client.setex(
                cache_key, self.cache_ttl, json.dumps(extracted_text)
            )
        except Exception:
            pass

    def _validate_cached_result(self, cached_result: dict) -> bool:
        """Validate cached result to ensure it won't cause database constraint violations."""
        try:
            # Check if it's a valid recipe result structure
            if not isinstance(cached_result, dict):
                current_app.logger.warning("Cached result is not a dictionary")
                return False

            # Check for required top-level keys
            required_keys = ["text", "parsed_recipe", "method", "success"]
            for key in required_keys:
                if key not in cached_result:
                    current_app.logger.warning(
                        f"Cached result missing required key: {key}"
                    )
                    return False

            # If parsing was successful, validate the parsed recipe
            if cached_result.get("success") and cached_result.get("parsed_recipe"):
                parsed_recipe = cached_result["parsed_recipe"]

                # Check if title would cause database constraint violation
                title = parsed_recipe.get("title")
                if title is None or (isinstance(title, str) and not title.strip()):
                    current_app.logger.warning(
                        "Cached result has null/empty title, would cause database constraint violation"
                    )
                    return False

                # Check that ingredients and instructions are lists (if present)
                ingredients = parsed_recipe.get("ingredients")
                if ingredients is not None and not isinstance(ingredients, list):
                    current_app.logger.warning(
                        "Cached result has invalid ingredients format"
                    )
                    return False

                instructions = parsed_recipe.get("instructions")
                if instructions is not None and not isinstance(instructions, list):
                    current_app.logger.warning(
                        "Cached result has invalid instructions format"
                    )
                    return False

            current_app.logger.debug("Cached result passed validation")
            return True

        except Exception as e:
            current_app.logger.error(f"Error validating cached result: {str(e)}")
            return False

    def _invalidate_cache(self, cache_key: str) -> None:
        """Remove invalid cached result."""
        try:
            if self.redis_client:
                self.redis_client.delete(cache_key)
                current_app.logger.info(
                    f"Invalidated cached result for key: {cache_key}"
                )
        except Exception as e:
            current_app.logger.error(
                f"Failed to invalidate cache key {cache_key}: {str(e)}"
            )

    def _build_extraction_prompt(self) -> str:
        """Build the prompt for LLM-based text extraction."""
        return """
Please extract ALL text from this recipe image with high accuracy. Focus on:

1. **Recipe Title** - Extract the complete recipe name
2. **Ingredients List** - Preserve exact measurements, units, and ingredient names
3. **Instructions** - Maintain step-by-step order and cooking details
4. **Additional Info** - Cooking times, serving sizes, temperatures, notes

EXTRACTION GUIDELINES:
- Preserve original spelling and capitalization
- Include ALL visible text, even if partially obscured
- Maintain the logical structure (ingredients before instructions)
- Use clear line breaks between different sections
- If text is unclear, make your best interpretation but stay faithful to what you see
- Include any cooking tips, notes, or additional information visible

OUTPUT FORMAT:
Return the extracted text in a clean, readable format that preserves the recipe's structure. Do not add explanations or modify the content - just extract what you see.
"""

    def clear_cache(self) -> None:
        """Clear all LLM OCR cache entries."""
        if self.redis_client:
            try:
                keys = self.redis_client.keys("llm_ocr:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception:
                pass

    def get_cache_size(self) -> int:
        """Get the current cache size for LLM OCR extractions."""
        if self.redis_client:
            try:
                return len(self.redis_client.keys("llm_ocr:*"))
            except Exception:
                pass
        return 0

    def get_extraction_cost_estimate(self) -> Dict[str, float]:
        """
        Get cost estimates for LLM OCR extraction.
        Based on Claude 3.5 Sonnet pricing as of 2024.
        """
        return {
            "cost_per_image_usd": 0.015,  # Approximate cost per typical recipe image
            "input_cost_per_1k_tokens": 0.003,
            "output_cost_per_1k_tokens": 0.015,
            "estimated_tokens_per_image": 1000,  # Rough estimate
        }

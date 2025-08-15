import base64
import hashlib
import json
import re
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
        
        current_app.logger.info(f"Initializing Anthropic client with API key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 10 else 'short'}")
        
        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=90.0  # 90 second timeout for API calls
        )
        self.redis_client = self._init_redis()
        self.cache_ttl = current_app.config.get("OCR_QUALITY_CACHE_TTL", 3600)  # 1 hour default

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
            
    def _build_literal_extraction_prompt(self) -> str:
        """Build a prompt focused purely on literal text extraction."""
        return """
You are a text transcription specialist. Your ONLY job is to extract every visible word from this recipe image with perfect accuracy.

EXTRACTION RULES:
1. Transcribe EVERY word exactly as written - preserve spelling, punctuation, capitalization
2. Maintain the visual layout and structure (line breaks, sections)
3. Do NOT interpret, correct, or modify any text
4. Do NOT add explanations, formatting, or structure
5. Include ALL text: titles, ingredients, instructions, notes, times, etc.
6. Preserve numbers and fractions exactly (1/2, 2-3, etc.)

Return ONLY the raw extracted text, exactly as you see it in the image. No JSON, no formatting, just the literal text.
"""

    def _build_minimal_parsing_prompt(self, extracted_text: str) -> str:
        """Build a prompt for minimal parsing of already-extracted text."""
        return f"""
You have been given text that was literally extracted from a recipe image. Your job is to organize it into a structured format with MINIMAL changes.

EXTRACTED TEXT:
{extracted_text}

STRUCTURING RULES:
1. Use the text EXACTLY as provided - do not rephrase or improve
2. Only add structure (JSON format) - preserve all original wording
3. Split into logical sections (title, ingredients, instructions) based on context
4. Maintain exact quantities, measurements, and ingredient names
5. Keep instruction text word-for-word from the extraction
6. Use null for any missing information - do not infer or add content

Return a JSON object with this structure:
{{
    "title": "exact title from text or null",
    "description": "exact description from text or null", 
    "prep_time": time_in_minutes_if_explicitly_stated_or_null,
    "cook_time": time_in_minutes_if_explicitly_stated_or_null,
    "total_time": time_in_minutes_if_explicitly_stated_or_null,
    "servings": "exact_servings_text_or_null",
    "difficulty": "only_if_explicitly_stated_or_null",
    "ingredients": [
        "exact ingredient line 1 as extracted",
        "exact ingredient line 2 as extracted"
    ],
    "instructions": [
        "exact instruction step 1 as extracted", 
        "exact instruction step 2 as extracted"
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
            if json_text.startswith('```json'):
                json_text = re.sub(r'^```json\s*', '', json_text)
            if json_text.endswith('```'):
                json_text = re.sub(r'\s*```$', '', json_text)
            
            # Parse JSON response
            recipe_data = json.loads(json_text)
            
            # Validate and clean up critical fields to prevent database constraint violations
            recipe_data = self._validate_and_clean_recipe_data(recipe_data)
                
            current_app.logger.info(f"Minimal parsing returned {len(recipe_data.get('ingredients', []))} ingredients and {len(recipe_data.get('instructions', []))} instructions")
                
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
            
            # Handle range values like "8-10", "4-6 servings", "2-3 hours"
            # Look for patterns like "8-10", "4-6", etc.
            range_match = re.search(r'(\d+)\s*[-–—]\s*(\d+)', value_str)
            if range_match:
                start_val = int(range_match.group(1))
                end_val = int(range_match.group(2))
                # Take the average of the range, rounded down
                result = (start_val + end_val) // 2
                current_app.logger.info(f"Converted range '{value_str}' to {result} for field '{field_name}'")
                return result
            
            # Look for single numbers (ignoring text like "servings", "minutes", etc.)
            number_match = re.search(r'(\d+)', value_str)
            if number_match:
                result = int(number_match.group(1))
                current_app.logger.debug(f"Extracted number {result} from '{value_str}' for field '{field_name}'")
                return result
            
            # Try direct conversion as fallback
            return int(value_str)
            
        except (ValueError, TypeError, AttributeError) as e:
            current_app.logger.warning(f"Could not convert '{value}' to integer for field '{field_name}': {str(e)}")
            return None
    
    def _validate_and_clean_recipe_data(self, recipe_data: dict) -> dict:
        """Validate and clean recipe data to prevent database constraint violations."""
        # Ensure title is never None or empty
        title = recipe_data.get("title")
        if not title or not str(title).strip():
            current_app.logger.warning("LLM returned null/empty title, will be handled by fallback logic")
            recipe_data["title"] = None  # Let the calling code handle this with fallbacks
        
        # Ensure ingredients is a list
        if "ingredients" in recipe_data and not isinstance(recipe_data["ingredients"], list):
            current_app.logger.warning("LLM returned ingredients in wrong format, converting to list")
            recipe_data["ingredients"] = []
        
        # Ensure instructions is a list  
        if "instructions" in recipe_data and not isinstance(recipe_data["instructions"], list):
            current_app.logger.warning("LLM returned instructions in wrong format, converting to list")
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
                recipe_data[field] = self._safe_int_conversion(recipe_data[field], field)
        
        # Ensure tags is a list
        if "tags" not in recipe_data or not isinstance(recipe_data["tags"], list):
            recipe_data["tags"] = []
        
        return recipe_data
    
    def _get_fallback_recipe_structure(self, error_msg: str = None) -> dict:
        """Return a minimal but valid recipe structure for fallback."""
        from datetime import datetime
        fallback_title = f"Recipe extracted on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return {
            "title": fallback_title,
            "description": "Recipe extracted from image" + (f" (Error: {error_msg})" if error_msg else ""),
            "ingredients": [],
            "instructions": [],
            "prep_time": None,
            "cook_time": None,
            "total_time": None,
            "servings": None,
            "difficulty": None,
            "tags": [],
            "source": None,
            "parsing_error": error_msg
        }

    def extract_and_parse_recipe(self, image_path: Path, use_cache: bool = True) -> dict:
        """
        Extract text from image using true two-step approach: literal extraction first, then minimal parsing.
        This ensures maximum fidelity to the source text.
        
        Args:
            image_path: Path to the image file
            use_cache: Whether to use caching for the extraction
            
        Returns:
            Dictionary containing both extracted text and parsed recipe data
        """
        try:
            # Generate cache key from image content
            cache_key = f"recipe_extract_parse_v2_{self._generate_cache_key(image_path)}"
            
            # Check cache if enabled and Redis is available
            if use_cache and self.redis_client:
                cached_result = self._get_from_cache(cache_key)
                if cached_result and self._validate_cached_result(cached_result):
                    current_app.logger.info("Using cached two-step extract+parse result")
                    return cached_result
                elif cached_result:
                    current_app.logger.warning("Cached result failed validation, invalidating cache")
                    self._invalidate_cache(cache_key)

            # STEP 1: Pure literal text extraction
            current_app.logger.info("Step 1: Starting literal text extraction")
            extracted_text = self._extract_literal_text(image_path)
            
            # STEP 2: Minimal parsing of extracted text
            current_app.logger.info("Step 2: Starting minimal parsing of extracted text")
            parsed_recipe = self._parse_extracted_text(extracted_text)
            
            # Combine results
            result = {
                "text": extracted_text,
                "parsed_recipe": parsed_recipe,
                "method": "two_step_literal",
                "quality_score": 10,
                "success": True
            }
            
            # Cache the result if caching is enabled and Redis is available
            if use_cache and self.redis_client:
                self._set_in_cache(cache_key, result)
                
            current_app.logger.info("Two-step extract+parse completed successfully")
            return result

        except Exception as e:
            current_app.logger.error(f"Two-step extract+parse failed: {str(e)}")
            raise OCRExtractionError(f"Two-step extract+parse failed: {str(e)}", e) from e
            
    def _extract_literal_text(self, image_path: Path) -> str:
        """Step 1: Extract literal text with no interpretation."""
        try:
            current_app.logger.info(f"Starting literal text extraction for: {image_path}")
            
            # Prepare optimized image for LLM
            image_data = self._prepare_image_for_llm(image_path)
            
            # Literal extraction prompt
            prompt = self._build_literal_extraction_prompt()

            current_app.logger.info("Making LLM API call for literal text extraction")
            
            # LLM call for pure text extraction
            try:
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",  # Best vision model
                    max_tokens=2000,
                    temperature=0.0,  # Maximum determinism
                    system="You are a text transcription specialist. Extract every visible word exactly as written.",
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_data["media_type"],
                                    "data": image_data["data"]
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }]
                )
            except Exception as api_error:
                current_app.logger.error(f"Anthropic API call failed: {str(api_error)}")
                if hasattr(api_error, 'status_code'):
                    current_app.logger.error(f"API status code: {api_error.status_code}")
                if hasattr(api_error, 'response'):
                    current_app.logger.error(f"API response: {api_error.response}")
                raise

            extracted_text = response.content[0].text.strip()
            current_app.logger.info(f"Literal extraction completed. Text length: {len(extracted_text)} characters")
            current_app.logger.info(f"First 200 chars of extracted text: {extracted_text[:200]}...")
            
            return extracted_text
            
        except Exception as e:
            current_app.logger.error(f"Literal text extraction failed: {str(e)}", exc_info=True)
            raise
        
    def _parse_extracted_text(self, extracted_text: str) -> dict:
        """Step 2: Minimally parse the already-extracted text."""
        # Minimal parsing prompt
        prompt = self._build_minimal_parsing_prompt(extracted_text)

        # LLM call for minimal parsing
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.0,  # Maximum determinism
            system="You are a recipe structuring assistant. Organize extracted text with minimal changes.",
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()
        return self._parse_minimal_response(response_text)

    def extract_text_from_image(self, image_path: Path, use_cache: bool = True) -> str:
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
            cache_key = self._generate_cache_key(image_path)

            # Check cache if enabled and Redis is available
            if use_cache and self.redis_client:
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    return cached_result

            # Convert image to base64
            image_data = self._prepare_image_for_llm(image_path)
            
            prompt = self._build_extraction_prompt()

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # High-quality vision model
                max_tokens=2000,
                temperature=0.0,
                system="You are an expert at extracting text from recipe images with high accuracy and attention to detail.",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_data["media_type"],
                                "data": image_data["data"]
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            extracted_text = response.content[0].text.strip()

            # Cache the result if caching is enabled and Redis is available
            if use_cache and self.redis_client:
                self._set_in_cache(cache_key, extracted_text)

            return extracted_text

        except Exception as e:
            current_app.logger.error(f"LLM OCR extraction failed: {str(e)}")
            raise OCRExtractionError(f"LLM OCR extraction failed: {str(e)}", e) from e

    def _prepare_image_for_llm(self, image_path: Path) -> Dict[str, str]:
        """
        Prepare image for LLM processing with aggressive optimization to reduce memory usage.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with base64 data and media type
        """
        import io
        import gc
        
        try:
            current_app.logger.info(f"Preparing image for LLM: {image_path}")
            
            # Get original file size for logging
            original_size_mb = image_path.stat().st_size / (1024 * 1024)
            current_app.logger.info(f"Original image size: {original_size_mb:.1f}MB")
            
            # Open and aggressively optimize image to reduce memory usage
            with Image.open(image_path) as img:
                original_dimensions = img.size
                current_app.logger.info(f"Original dimensions: {original_dimensions[0]}x{original_dimensions[1]}")
                
                # Convert to RGB if needed (more memory efficient than keeping alpha channels)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Get max size from config (production may have different settings)
                max_size = current_app.config.get('MAX_IMAGE_DIMENSION', 1568)  # Keep higher default for better OCR
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
                img_buffer = io.BytesIO()
                jpeg_quality = current_app.config.get('JPEG_QUALITY', 95)  # Use higher quality for better OCR
                current_app.logger.info(f"Using JPEG_QUALITY: {jpeg_quality}%")
                img.save(img_buffer, format='JPEG', quality=jpeg_quality, optimize=True)
                
                # Get compressed size for logging
                compressed_size = len(img_buffer.getvalue())
                compressed_size_mb = compressed_size / (1024 * 1024)
                current_app.logger.info(f"Compressed image size: {compressed_size_mb:.1f}MB (reduction: {((original_size_mb - compressed_size_mb) / original_size_mb * 100):.1f}%)")
                
                img_bytes = img_buffer.getvalue()
                img_buffer.close()  # Explicitly close buffer
                
            # Force garbage collection after image processing
            gc.collect()
            
            # Encode to base64 with streaming for memory efficiency
            # Use chunked encoding to reduce peak memory usage
            import math
            
            chunk_size = 1024 * 1024  # 1MB chunks
            base64_chunks = []
            
            for i in range(0, len(img_bytes), chunk_size):
                chunk = img_bytes[i:i + chunk_size]
                base64_chunk = base64.b64encode(chunk).decode('utf-8')
                base64_chunks.append(base64_chunk)
                del chunk  # Free chunk memory immediately
            
            base64_data = ''.join(base64_chunks)
            del base64_chunks  # Free chunk list
            del img_bytes  # Free the original bytes data
            
            current_app.logger.info(f"Base64 encoded image ready for LLM (final memory optimization complete)")
            
            return {
                "data": base64_data,
                "media_type": "image/jpeg"
            }
            
        except Exception as e:
            # Force garbage collection even on error
            gc.collect()
            current_app.logger.error(f"Failed to prepare image for LLM: {str(e)}")
            raise OCRExtractionError(f"Failed to prepare image for LLM: {str(e)}", e) from e

    def _generate_cache_key(self, image_path: Path) -> str:
        """Generate a hash-based cache key from the image file."""
        try:
            # Use file content hash for cache key
            with open(image_path, 'rb') as f:
                image_content = f.read()
            
            hash_key = hashlib.sha256(image_content).hexdigest()
            return f"llm_ocr:{hash_key}"
        except Exception:
            # Fallback to path-based key if file reading fails
            hash_key = hashlib.sha256(str(image_path).encode('utf-8')).hexdigest()
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
                cache_key, 
                self.cache_ttl, 
                json.dumps(extracted_text)
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
                    current_app.logger.warning(f"Cached result missing required key: {key}")
                    return False
            
            # If parsing was successful, validate the parsed recipe
            if cached_result.get("success") and cached_result.get("parsed_recipe"):
                parsed_recipe = cached_result["parsed_recipe"]
                
                # Check if title would cause database constraint violation
                title = parsed_recipe.get("title")
                if title is None or (isinstance(title, str) and not title.strip()):
                    current_app.logger.warning("Cached result has null/empty title, would cause database constraint violation")
                    return False
                
                # Check that ingredients and instructions are lists (if present)
                ingredients = parsed_recipe.get("ingredients")
                if ingredients is not None and not isinstance(ingredients, list):
                    current_app.logger.warning("Cached result has invalid ingredients format")
                    return False
                
                instructions = parsed_recipe.get("instructions") 
                if instructions is not None and not isinstance(instructions, list):
                    current_app.logger.warning("Cached result has invalid instructions format")
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
                current_app.logger.info(f"Invalidated cached result for key: {cache_key}")
        except Exception as e:
            current_app.logger.error(f"Failed to invalidate cache key {cache_key}: {str(e)}")

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
            "estimated_tokens_per_image": 1000  # Rough estimate
        }
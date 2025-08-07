import base64
import hashlib
import json
from pathlib import Path
from typing import Dict

import anthropic
import redis
from flask import current_app
from PIL import Image

from app.exceptions import OCRExtractionError


class LLMOCRService:
    """Service for LLM-based text extraction from images using Anthropic Claude."""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=current_app.config.get("ANTHROPIC_API_KEY")
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
            
    def _build_comprehensive_recipe_prompt(self) -> str:
        """Build a comprehensive prompt that extracts AND parses recipe in one step."""
        return """
Please analyze this recipe image and provide a comprehensive extraction and parsing in JSON format.

Extract all text from the image first, then immediately parse it into the structured format below.

Return your response as a JSON object with this exact structure:

{
    "extracted_text": "The complete text you can see in the image...",
    "recipe": {
        "title": "Recipe name",
        "description": "Brief description or null",
        "prep_time": minutes_as_number_or_null,
        "cook_time": minutes_as_number_or_null,
        "total_time": minutes_as_number_or_null,
        "servings": number_or_null,
        "difficulty": "easy/medium/hard or null",
        "ingredients": [
            {
                "name": "ingredient name",
                "quantity": number_or_null,
                "unit": "unit or null",
                "preparation": "preparation method or null",
                "optional": false
            }
        ],
        "instructions": [
            "Step 1 instructions",
            "Step 2 instructions"
        ],
        "tags": ["tag1", "tag2"],
        "source": "source information or null"
    }
}

CRITICAL REQUIREMENTS:
- Extract ALL visible text first in the "extracted_text" field
- Parse times into minutes (convert hours to minutes: 1h 30m = 90)
- Keep ingredient quantities as numbers when possible
- ingredients MUST be an array of objects, even if empty: []
- instructions MUST be an array of strings, even if empty: []
- tags MUST be an array of strings, even if empty: []
- Preserve the original instruction order
- Return ONLY valid JSON, no markdown, no additional text
- If you cannot parse something, use null for that field
"""

    def _parse_comprehensive_response(self, response_text: str) -> dict:
        """Parse the comprehensive LLM response into structured data."""
        import json
        import re
        
        try:
            # Clean up response text - sometimes LLM adds markdown formatting
            json_text = response_text.strip()
            if json_text.startswith('```json'):
                json_text = re.sub(r'^```json\s*', '', json_text)
            if json_text.endswith('```'):
                json_text = re.sub(r'\s*```$', '', json_text)
            
            # Parse JSON response
            parsed_response = json.loads(json_text)
            
            # Validate structure
            if "extracted_text" not in parsed_response or "recipe" not in parsed_response:
                raise ValueError("Response missing required fields")
                
            recipe_data = parsed_response["recipe"]
            
            # Ensure ingredients is a list
            if "ingredients" in recipe_data and not isinstance(recipe_data["ingredients"], list):
                current_app.logger.warning("LLM returned ingredients in wrong format, converting to list")
                recipe_data["ingredients"] = []
            
            # Ensure instructions is a list  
            if "instructions" in recipe_data and not isinstance(recipe_data["instructions"], list):
                current_app.logger.warning("LLM returned instructions in wrong format, converting to list")
                recipe_data["instructions"] = []
                
            current_app.logger.info(f"LLM returned {len(recipe_data.get('ingredients', []))} ingredients and {len(recipe_data.get('instructions', []))} instructions")
                
            # Return structured result
            return {
                "text": parsed_response["extracted_text"],
                "parsed_recipe": recipe_data,
                "method": "llm_comprehensive",
                "quality_score": 10,
                "success": True
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            current_app.logger.error(f"Failed to parse comprehensive LLM response: {str(e)}")
            current_app.logger.error(f"Raw response: {response_text[:500]}...")
            
            # Fallback: return raw text for manual processing
            return {
                "text": response_text,
                "parsed_recipe": None,
                "method": "llm_comprehensive_fallback", 
                "quality_score": 5,
                "success": False,
                "error": str(e)
            }

    def extract_and_parse_recipe(self, image_path: Path, use_cache: bool = True) -> dict:
        """
        Extract text from image AND parse it into recipe structure in a single LLM call.
        This dramatically reduces memory usage and processing time by eliminating the second LLM call.
        
        Args:
            image_path: Path to the image file
            use_cache: Whether to use caching for the extraction
            
        Returns:
            Dictionary containing both extracted text and parsed recipe data
        """
        try:
            # Generate cache key from image content
            cache_key = f"recipe_extract_parse_{self._generate_cache_key(image_path)}"
            
            # Check cache if enabled and Redis is available
            if use_cache and self.redis_client:
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    current_app.logger.info("Using cached LLM extract+parse result")
                    return cached_result

            # Prepare optimized image for LLM
            image_data = self._prepare_image_for_llm(image_path)
            
            # Single comprehensive prompt that extracts AND parses in one call
            prompt = self._build_comprehensive_recipe_prompt()

            current_app.logger.info("Starting single-pass LLM extract+parse operation")

            # Single LLM call for both extraction and parsing
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,  # Increased for comprehensive response
                temperature=0.1,
                system="You are an expert recipe extraction and parsing assistant. Extract text from recipe images and immediately structure it into a standardized recipe format.",
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

            # Parse the comprehensive response
            response_text = response.content[0].text.strip()
            result = self._parse_comprehensive_response(response_text)
            
            # Cache the result if caching is enabled and Redis is available
            if use_cache and self.redis_client:
                self._set_in_cache(cache_key, result)
                
            current_app.logger.info("Single-pass LLM extract+parse completed successfully")
            return result

        except Exception as e:
            current_app.logger.error(f"LLM extract+parse failed: {str(e)}")
            raise OCRExtractionError(f"LLM extract+parse failed: {str(e)}", e) from e

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
                temperature=0.1,
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
                
                # Aggressive resizing - use smaller max size to dramatically reduce memory
                max_size = current_app.config.get('MAX_IMAGE_DIMENSION', 1200)  # Default 1200px instead of 1568
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
                jpeg_quality = current_app.config.get('JPEG_QUALITY', 85)  # Default 85% quality
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
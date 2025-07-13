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
        Prepare image for LLM processing by converting to base64.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with base64 data and media type
        """
        try:
            # Open and potentially resize image to optimize for API limits
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large (max 1568x1568 for Claude)
                max_size = 1568
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Save to bytes
                import io
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=95)
                img_bytes = img_buffer.getvalue()
            
            # Encode to base64
            base64_data = base64.b64encode(img_bytes).decode('utf-8')
            
            return {
                "data": base64_data,
                "media_type": "image/jpeg"
            }
            
        except Exception as e:
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
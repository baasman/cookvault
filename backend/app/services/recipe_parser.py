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
        self.cache_ttl = current_app.config.get("RECIPE_CACHE_TTL", 86400)  # 24 hours default

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

    def parse_recipe_text(self, ocr_text: str, use_cache: bool = True) -> Dict:
        # Generate cache key from input text
        cache_key = self._generate_cache_key(ocr_text)

        # Check cache if enabled and Redis is available
        if use_cache and self.redis_client:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result

        prompt = self._build_parsing_prompt(ocr_text)

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.1,
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

    def _generate_cache_key(self, ocr_text: str) -> str:
        """Generate a hash-based cache key from the OCR text."""
        normalized_text = ocr_text.strip().lower()
        hash_key = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
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
                cache_key, 
                self.cache_ttl, 
                json.dumps(parsed_result)
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

    def _build_parsing_prompt(self, ocr_text: str) -> str:
        return f"""
Please parse this recipe text and extract structured information in JSON format:

{ocr_text}

Return a JSON object with these fields:
- title: recipe name
- description: brief description (if any)
- ingredients: array of ingredient strings
- instructions: array of instruction steps
- prep_time: preparation time in minutes (if mentioned)
- cook_time: cooking time in minutes (if mentioned)
- servings: number of servings (if mentioned)
- difficulty: easy/medium/hard (if mentioned or can be inferred)
- tags: array of relevant tags/categories

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

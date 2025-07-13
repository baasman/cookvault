import json
import hashlib
from typing import Dict, Tuple

import anthropic
import redis
from flask import current_app


class OCRQualityService:
    """Service to assess the quality of OCR-extracted text using a lightweight LLM."""

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

    def assess_quality(self, ocr_text: str, use_cache: bool = True) -> Tuple[int, str]:
        """
        Assess the quality of OCR-extracted text.

        Args:
            ocr_text: The text extracted by traditional OCR
            use_cache: Whether to use caching for the assessment

        Returns:
            Tuple of (quality_score, reasoning) where quality_score is 1-10
        """
        # Generate cache key from input text
        cache_key = self._generate_cache_key(ocr_text)

        # Check cache if enabled and Redis is available
        if use_cache and self.redis_client:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result["score"], cached_result["reasoning"]

        prompt = self._build_quality_assessment_prompt(ocr_text)

        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Fast, cost-effective model
                max_tokens=300,
                temperature=0.1,
                system="You are an OCR quality assessment specialist. Analyze text quality objectively and provide scores with clear reasoning.",
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            score, reasoning = self._extract_assessment_from_response(content)

            # Cache the result if caching is enabled and Redis is available
            if use_cache and self.redis_client:
                result = {"score": score, "reasoning": reasoning}
                self._set_in_cache(cache_key, result)

            return score, reasoning

        except Exception as e:
            current_app.logger.error(f"OCR quality assessment failed: {str(e)}")
            # Return conservative assessment on failure
            return 5, f"Assessment failed: {str(e)}"

    def _generate_cache_key(self, ocr_text: str) -> str:
        """Generate a hash-based cache key from the OCR text."""
        normalized_text = ocr_text.strip().lower()
        hash_key = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
        return f"ocr_quality:{hash_key}"

    def _get_from_cache(self, cache_key: str) -> Dict:
        """Get quality assessment from Redis cache."""
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass
        return None

    def _set_in_cache(self, cache_key: str, result: Dict) -> None:
        """Store quality assessment in Redis cache."""
        try:
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(result)
            )
        except Exception:
            pass

    def _build_quality_assessment_prompt(self, ocr_text: str) -> str:
        """Build the prompt for OCR quality assessment."""
        return f"""
Assess the quality of this OCR-extracted text for recipe processing on a scale of 1-10:

TEXT TO ASSESS:
{ocr_text}

Evaluation criteria:
- Text coherence and readability (1-3 points)
- Recipe-like structure and content (1-3 points)
- Character recognition accuracy (1-2 points)
- Completeness - no major missing sections (1-2 points)

Consider these quality indicators:
✓ GOOD: Clear ingredient lists, step-by-step instructions, readable measurements
✗ POOR: Garbled text, missing words, unrecognizable characters, fragmented sentences

Return your assessment in this exact format:
SCORE: [1-10]
REASONING: [Brief explanation of the score]

Examples:
- Score 8-10: High quality, ready for recipe parsing
- Score 6-7: Moderate quality, some issues but usable
- Score 3-5: Poor quality, significant issues present
- Score 1-2: Very poor, mostly unreadable
"""

    def _extract_assessment_from_response(self, response: str) -> Tuple[int, str]:
        """Extract quality score and reasoning from the LLM response."""
        try:
            lines = response.strip().split('\n')
            score = None
            reasoning = ""

            for line in lines:
                line = line.strip()
                if line.startswith("SCORE:"):
                    score_text = line.replace("SCORE:", "").strip()
                    score = int(score_text)
                elif line.startswith("REASONING:"):
                    reasoning = line.replace("REASONING:", "").strip()

            if score is None:
                # Fallback: try to extract any number between 1-10
                import re
                score_match = re.search(r'\b([1-9]|10)\b', response)
                if score_match:
                    score = int(score_match.group(1))
                else:
                    score = 5  # Default middle score

            if not reasoning:
                reasoning = "Unable to parse detailed reasoning from assessment"

            # Validate score range
            score = max(1, min(10, score))

            return score, reasoning

        except Exception as e:
            current_app.logger.error(f"Failed to parse quality assessment response: {str(e)}")
            return 5, f"Failed to parse assessment: {str(e)}"

    def clear_cache(self) -> None:
        """Clear all quality assessment cache entries."""
        if self.redis_client:
            try:
                keys = self.redis_client.keys("ocr_quality:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception:
                pass

    def get_cache_size(self) -> int:
        """Get the current cache size for quality assessments."""
        if self.redis_client:
            try:
                return len(self.redis_client.keys("ocr_quality:*"))
            except Exception:
                pass
        return 0
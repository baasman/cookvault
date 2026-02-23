"""
Service for importing recipes from URLs.

Extracts recipe data using schema.org JSON-LD (preferred) or Claude AI fallback.
"""

import hashlib
import ipaddress
import json
import re
import traceback
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import redis
import requests
from bs4 import BeautifulSoup
from flask import current_app

from app.services.recipe_parser import RecipeParser


class UrlValidationError(Exception):
    """Raised when URL validation fails."""

    pass


class UrlFetchError(Exception):
    """Raised when fetching URL fails."""

    pass


class BotProtectionError(Exception):
    """Raised when the site blocks the request."""

    pass


class RecipeNotFoundError(Exception):
    """Raised when no recipe is found on the page."""

    pass


class UrlRecipeService:
    """Service for extracting recipes from URLs."""

    # Common browser User-Agent to avoid bot blocking
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Request configuration
    TIMEOUT_SECONDS = 15
    MAX_CONTENT_SIZE = 5 * 1024 * 1024  # 5MB
    CACHE_TTL = 86400  # 24 hours

    def __init__(self):
        self.redis_client = self._init_redis()

    def _init_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis connection for caching."""
        try:
            redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception as e:
            current_app.logger.warning(f"Redis connection failed: {e}")
            return None

    def import_from_url(
        self, url: str, translate_to_english: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point - fetch URL and extract recipe.

        Args:
            url: The URL to import recipe from
            translate_to_english: Whether to translate the recipe to English

        Returns:
            Dict containing parsed recipe data and extraction metadata

        Raises:
            UrlValidationError: If URL is invalid or blocked
            UrlFetchError: If fetching the page fails
            BotProtectionError: If the site blocks the request
            RecipeNotFoundError: If no recipe is found on the page
        """
        # Validate URL
        validated_url = self._validate_url(url)

        # Check cache first
        cache_key = self._generate_cache_key(validated_url, translate_to_english)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            current_app.logger.info(f"Cache hit for URL: {validated_url}")
            cached_result["from_cache"] = True
            return cached_result

        # Fetch the page
        html_content = self._fetch_page(validated_url)

        # Try to extract JSON-LD recipe first
        recipe_data = self._extract_json_ld_recipe(html_content)
        extraction_method = "json_ld"

        # Fall back to Claude parsing if no JSON-LD found
        if recipe_data is None:
            current_app.logger.info(
                f"No JSON-LD recipe found for {validated_url}, falling back to Claude"
            )
            recipe_data = self._extract_recipe_with_claude(
                html_content, validated_url, translate_to_english
            )
            extraction_method = "claude"

        if recipe_data is None:
            raise RecipeNotFoundError(
                "No recipe found on this page. Try the text input instead."
            )

        result = {
            "recipe_data": recipe_data,
            "extraction_method": extraction_method,
            "source_url": validated_url,
            "from_cache": False,
        }

        # Cache the result
        self._set_in_cache(cache_key, result)

        return result

    def _validate_url(self, url: str) -> str:
        """
        Validate URL format and block private IPs (SSRF prevention).

        Args:
            url: The URL to validate

        Returns:
            The validated URL (potentially normalized)

        Raises:
            UrlValidationError: If URL is invalid or points to private IP
        """
        if not url or not isinstance(url, str):
            raise UrlValidationError("Please enter a valid URL")

        url = url.strip()

        # Add https if no scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            parsed = urlparse(url)
        except Exception as e:
            current_app.logger.error(
                f"URL parse error: {e}\n{traceback.format_exc()}"
            )
            raise UrlValidationError("Please enter a valid URL")

        # Validate scheme
        if parsed.scheme not in ("http", "https"):
            raise UrlValidationError("URL must use HTTP or HTTPS")

        # Validate hostname exists
        if not parsed.netloc or not parsed.hostname:
            raise UrlValidationError("Please enter a valid URL")

        hostname = parsed.hostname.lower()

        # Block localhost and common local hostnames
        blocked_hostnames = {
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
            "host.docker.internal",
            "kubernetes.default",
        }
        if hostname in blocked_hostnames:
            raise UrlValidationError("Cannot access local addresses")

        # Block internal domain patterns
        internal_patterns = [
            r"\.local$",
            r"\.internal$",
            r"\.localhost$",
            r"\.corp$",
            r"\.lan$",
            r"\.home$",
        ]
        for pattern in internal_patterns:
            if re.search(pattern, hostname):
                raise UrlValidationError("Cannot access internal addresses")

        # Try to resolve hostname and check for private IPs
        try:
            import socket

            ip_addresses = socket.getaddrinfo(hostname, None)
            for addr_info in ip_addresses:
                ip_str = addr_info[4][0]
                try:
                    ip_obj = ipaddress.ip_address(ip_str)
                    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
                        raise UrlValidationError("Cannot access private addresses")
                except ValueError:
                    # If we can't parse the IP, allow it (rare edge case)
                    pass
        except socket.gaierror:
            # DNS resolution failed - let the fetch attempt handle this
            pass
        except UrlValidationError:
            raise
        except Exception as e:
            current_app.logger.warning(f"IP validation warning: {e}")

        return url

    def _fetch_page(self, url: str) -> str:
        """
        Fetch page content with appropriate headers.

        Args:
            url: The URL to fetch

        Returns:
            HTML content of the page

        Raises:
            UrlFetchError: If fetching fails
            BotProtectionError: If site blocks the request
        """
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.TIMEOUT_SECONDS,
                allow_redirects=True,
                stream=True,
            )

            # Check for bot protection / blocking
            if response.status_code == 403:
                raise BotProtectionError(
                    "This site blocked our request. Try copying the recipe text instead."
                )

            if response.status_code == 404:
                raise UrlFetchError("Page not found. Please check the URL.")

            if response.status_code == 429:
                raise BotProtectionError(
                    "Too many requests. Please wait a moment and try again."
                )

            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("Content-Type", "")
            if not any(
                ct in content_type
                for ct in ["text/html", "application/xhtml+xml", "text/plain"]
            ):
                raise UrlFetchError(
                    "URL does not point to a web page. Please provide a recipe page URL."
                )

            # Read content with size limit
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.MAX_CONTENT_SIZE:
                    raise UrlFetchError(
                        "Page is too large. Please try a different recipe page."
                    )

            # Decode content
            encoding = response.encoding or "utf-8"
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                return content.decode("utf-8", errors="ignore")

        except requests.exceptions.Timeout:
            raise UrlFetchError("Request timed out. The site may be slow.")
        except requests.exceptions.SSLError:
            raise UrlFetchError("SSL error. The site may have security issues.")
        except requests.exceptions.ConnectionError:
            raise UrlFetchError(
                "Could not connect to the site. Please check the URL."
            )
        except (BotProtectionError, UrlFetchError):
            raise
        except requests.exceptions.RequestException as e:
            current_app.logger.error(
                f"Request error for {url}: {e}\n{traceback.format_exc()}"
            )
            raise UrlFetchError("Failed to fetch the page. Please try again.")

    def _extract_json_ld_recipe(self, html: str) -> Optional[Dict[str, Any]]:
        """
        Parse HTML for JSON-LD recipe data.

        Args:
            html: HTML content of the page

        Returns:
            Parsed recipe data dict or None if not found
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Find all JSON-LD script tags
            json_ld_scripts = soup.find_all(
                "script", {"type": "application/ld+json"}
            )

            for script in json_ld_scripts:
                try:
                    if not script.string:
                        continue

                    data = json.loads(script.string)

                    # Handle @graph structure
                    if isinstance(data, dict) and "@graph" in data:
                        data = data["@graph"]

                    # Handle single object or list
                    if isinstance(data, dict):
                        recipe = self._find_recipe_in_json_ld(data)
                        if recipe:
                            return self._map_json_ld_to_recipe(recipe)
                    elif isinstance(data, list):
                        for item in data:
                            recipe = self._find_recipe_in_json_ld(item)
                            if recipe:
                                return self._map_json_ld_to_recipe(recipe)

                except json.JSONDecodeError as e:
                    current_app.logger.debug(f"JSON-LD parse error: {e}")
                    continue

            return None

        except Exception as e:
            current_app.logger.error(
                f"JSON-LD extraction error: {e}\n{traceback.format_exc()}"
            )
            return None

    def _find_recipe_in_json_ld(self, data: Dict) -> Optional[Dict]:
        """Find Recipe type in JSON-LD data structure."""
        if not isinstance(data, dict):
            return None

        # Check if this is a Recipe
        schema_type = data.get("@type", "")
        if isinstance(schema_type, list):
            # Handle multiple types
            if "Recipe" in schema_type:
                return data
        elif schema_type == "Recipe":
            return data

        # Check nested structures (some sites nest Recipe in ItemPage etc.)
        for key, value in data.items():
            if isinstance(value, dict):
                result = self._find_recipe_in_json_ld(value)
                if result:
                    return result
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        result = self._find_recipe_in_json_ld(item)
                        if result:
                            return result

        return None

    def _map_json_ld_to_recipe(self, json_ld: Dict) -> Dict[str, Any]:
        """
        Map schema.org Recipe JSON-LD to our recipe format.

        Args:
            json_ld: JSON-LD Recipe object

        Returns:
            Recipe data in our standard format
        """
        recipe = {
            "title": json_ld.get("name", "Untitled Recipe"),
            "description": json_ld.get("description"),
            "ingredients": [],
            "instructions": [],
            "prep_time": None,
            "cook_time": None,
            "servings": None,
            "difficulty": None,
            "tags": [],
        }

        # Extract ingredients
        ingredients = json_ld.get("recipeIngredient", [])
        if isinstance(ingredients, list):
            recipe["ingredients"] = [str(i).strip() for i in ingredients if i]

        # Extract instructions
        instructions = json_ld.get("recipeInstructions", [])
        recipe["instructions"] = self._parse_instructions(instructions)

        # Extract times
        recipe["prep_time"] = self._parse_iso_duration(json_ld.get("prepTime"))
        recipe["cook_time"] = self._parse_iso_duration(json_ld.get("cookTime"))

        # If no cook time but total time exists, try to use that
        if recipe["cook_time"] is None:
            total_time = self._parse_iso_duration(json_ld.get("totalTime"))
            if total_time and recipe["prep_time"]:
                recipe["cook_time"] = max(0, total_time - recipe["prep_time"])
            elif total_time:
                recipe["cook_time"] = total_time

        # Extract servings
        recipe["servings"] = self._parse_servings(json_ld.get("recipeYield"))

        # Extract tags from category and cuisine
        tags = []
        category = json_ld.get("recipeCategory")
        if category:
            if isinstance(category, list):
                tags.extend(category)
            else:
                tags.append(category)

        cuisine = json_ld.get("recipeCuisine")
        if cuisine:
            if isinstance(cuisine, list):
                tags.extend(cuisine)
            else:
                tags.append(cuisine)

        # Add keywords
        keywords = json_ld.get("keywords")
        if keywords:
            if isinstance(keywords, str):
                tags.extend([k.strip() for k in keywords.split(",") if k.strip()])
            elif isinstance(keywords, list):
                tags.extend(keywords)

        recipe["tags"] = list(set(tags))[:10]  # Dedupe and limit

        return recipe

    def _parse_instructions(self, instructions: Any) -> list:
        """Parse instructions from various JSON-LD formats."""
        result = []

        if isinstance(instructions, str):
            # Plain text instructions - split by sentences or newlines
            for line in instructions.split("\n"):
                line = line.strip()
                if line:
                    result.append(line)
            return result

        if isinstance(instructions, list):
            for item in instructions:
                if isinstance(item, str):
                    result.append(item.strip())
                elif isinstance(item, dict):
                    # HowToStep or HowToSection
                    item_type = item.get("@type", "")

                    if item_type == "HowToSection":
                        # Section with steps
                        section_name = item.get("name", "")
                        section_items = item.get("itemListElement", [])
                        if section_name:
                            result.append(f"**{section_name}**")
                        for sub_item in section_items:
                            if isinstance(sub_item, str):
                                result.append(sub_item.strip())
                            elif isinstance(sub_item, dict):
                                text = sub_item.get("text", "")
                                if text:
                                    result.append(text.strip())
                    else:
                        # HowToStep or similar
                        text = item.get("text", "")
                        if not text:
                            text = item.get("name", "")
                        if text:
                            result.append(text.strip())

        return result

    def _parse_iso_duration(self, duration: Optional[str]) -> Optional[int]:
        """
        Convert ISO 8601 duration to minutes.

        Args:
            duration: ISO 8601 duration string (e.g., "PT30M", "PT1H30M")

        Returns:
            Duration in minutes or None
        """
        if not duration or not isinstance(duration, str):
            return None

        duration = duration.strip().upper()

        # Handle simple minute format
        if duration.isdigit():
            return int(duration)

        # Handle ISO 8601 format
        pattern = r"^PT?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$"
        match = re.match(pattern, duration)

        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            total_minutes = hours * 60 + minutes + (seconds // 60)
            return total_minutes if total_minutes > 0 else None

        # Handle day format (rare but possible)
        day_pattern = r"^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$"
        match = re.match(day_pattern, duration)
        if match:
            days = int(match.group(1) or 0)
            hours = int(match.group(2) or 0)
            minutes = int(match.group(3) or 0)
            seconds = int(match.group(4) or 0)
            total_minutes = days * 24 * 60 + hours * 60 + minutes + (seconds // 60)
            return total_minutes if total_minutes > 0 else None

        return None

    def _parse_servings(self, yield_value: Any) -> Optional[int]:
        """
        Parse recipe yield/servings from various formats.

        Args:
            yield_value: Recipe yield value (string, int, or list)

        Returns:
            Number of servings or None
        """
        if yield_value is None:
            return None

        if isinstance(yield_value, int):
            return yield_value

        if isinstance(yield_value, list):
            # Take first item
            yield_value = yield_value[0] if yield_value else None

        if isinstance(yield_value, str):
            # Extract first number from string
            match = re.search(r"(\d+)", yield_value)
            if match:
                return int(match.group(1))

        return None

    def _extract_recipe_with_claude(
        self, html: str, url: str, translate_to_english: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback: Clean HTML and use RecipeParser to extract recipe.

        Args:
            html: HTML content
            url: Source URL for context
            translate_to_english: Whether to translate to English

        Returns:
            Parsed recipe data or None
        """
        try:
            # Extract main text content from HTML
            text_content = self._extract_main_content(html)

            if not text_content or len(text_content.strip()) < 100:
                current_app.logger.info(
                    f"Insufficient text content extracted from {url}"
                )
                return None

            # Use RecipeParser to parse the text
            recipe_parser = RecipeParser()

            # Add URL context to the text
            text_with_context = f"Source URL: {url}\n\n{text_content}"

            parsed_recipe = recipe_parser.parse_recipe_text(
                text_with_context,
                use_cache=True,
                translate_to_english=translate_to_english,
            )

            # Validate we got actual recipe data
            if not parsed_recipe.get("ingredients") and not parsed_recipe.get(
                "instructions"
            ):
                return None

            return parsed_recipe

        except Exception as e:
            current_app.logger.error(
                f"Claude extraction error: {e}\n{traceback.format_exc()}"
            )
            return None

    def _extract_main_content(self, html: str) -> str:
        """
        Extract main text content from HTML, removing navigation, ads, etc.

        Args:
            html: HTML content

        Returns:
            Cleaned text content
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Remove unwanted elements
            unwanted_tags = [
                "script",
                "style",
                "nav",
                "header",
                "footer",
                "aside",
                "iframe",
                "noscript",
                "svg",
                "form",
            ]
            for tag in unwanted_tags:
                for element in soup.find_all(tag):
                    element.decompose()

            # Remove elements with common ad/nav classes
            unwanted_classes = [
                "nav",
                "navigation",
                "menu",
                "sidebar",
                "footer",
                "header",
                "ad",
                "advertisement",
                "social",
                "share",
                "comment",
                "comments",
                "related",
                "recommended",
            ]
            for class_name in unwanted_classes:
                for element in soup.find_all(class_=re.compile(class_name, re.I)):
                    element.decompose()

            # Try to find recipe-specific containers
            recipe_containers = soup.find_all(
                class_=re.compile(r"recipe|ingredient|instruction", re.I)
            )

            if recipe_containers:
                # Use recipe containers
                text_parts = []
                for container in recipe_containers:
                    text_parts.append(container.get_text(separator="\n", strip=True))
                text = "\n\n".join(text_parts)
            else:
                # Fall back to main content areas
                main_content = (
                    soup.find("main")
                    or soup.find("article")
                    or soup.find(class_=re.compile(r"content|post|entry", re.I))
                    or soup.body
                )

                if main_content:
                    text = main_content.get_text(separator="\n", strip=True)
                else:
                    text = soup.get_text(separator="\n", strip=True)

            # Clean up text
            lines = []
            for line in text.split("\n"):
                line = line.strip()
                if line and len(line) > 2:  # Skip very short lines
                    lines.append(line)

            text = "\n".join(lines)

            # Limit text length to avoid overwhelming Claude
            max_length = 15000
            if len(text) > max_length:
                text = text[:max_length] + "..."

            return text

        except Exception as e:
            current_app.logger.error(
                f"Content extraction error: {e}\n{traceback.format_exc()}"
            )
            return ""

    def _generate_cache_key(self, url: str, translate: bool = False) -> str:
        """Generate cache key from URL."""
        normalized = url.strip().lower()
        suffix = "_translated" if translate else ""
        hash_key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"url_recipe:{hash_key}{suffix}"

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get cached recipe data."""
        if not self.redis_client:
            return None
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            current_app.logger.warning(f"Cache read error: {e}")
        return None

    def _set_in_cache(self, cache_key: str, data: Dict) -> None:
        """Cache recipe data."""
        if not self.redis_client:
            return
        try:
            self.redis_client.setex(cache_key, self.CACHE_TTL, json.dumps(data))
        except Exception as e:
            current_app.logger.warning(f"Cache write error: {e}")

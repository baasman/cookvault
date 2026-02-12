"""
Google Books API Service

This service handles integration with the Google Books API to search for books
and retrieve book metadata for cookbook creation.
"""

import json
import hashlib
import requests
import redis
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from flask import current_app

logger = logging.getLogger(__name__)

# Cache TTL in seconds (1 hour for search results, 24 hours for book details)
SEARCH_CACHE_TTL = 3600
DETAILS_CACHE_TTL = 86400


class GoogleBooksService:
    """Service for interacting with Google Books API"""

    BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    def __init__(self, api_key: Optional[str] = None, redis_url: Optional[str] = None):
        """Initialize the Google Books service

        Args:
            api_key: Google Books API key (optional for basic searches)
            redis_url: Redis URL for caching (optional)
        """
        # Only use API key if it's provided and not empty/blank
        self.api_key = api_key.strip() if api_key and api_key.strip() else None

        if self.api_key:
            logger.info("Google Books service initialized with API key")
        else:
            logger.info(
                "Google Books service initialized without API key (using free tier)"
            )

        # Initialize Redis for caching
        self.redis_client = None
        redis_url = redis_url or self._get_redis_url()
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("Google Books service: Redis cache enabled")
            except Exception as e:
                logger.warning(f"Google Books service: Redis cache unavailable: {e}")
                self.redis_client = None

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Cookbook-Creator/1.0"})

    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL from Flask app config"""
        try:
            return current_app.config.get("REDIS_URL")
        except RuntimeError:
            # Not in Flask app context
            return None

    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """Generate a cache key"""
        hash_id = hashlib.md5(identifier.encode()).hexdigest()[:16]
        return f"google_books:{prefix}:{hash_id}"

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data"""
        if not self.redis_client:
            return None
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    def _set_cached(self, key: str, data: Any, ttl: int) -> None:
        """Set cached data"""
        if not self.redis_client:
            return
        try:
            self.redis_client.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def search_books(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for books using Google Books API

        Args:
            query: Search query (can include title, author, ISBN)
            max_results: Maximum number of results to return

        Returns:
            List of book dictionaries with mapped fields
        """
        # Check cache first
        cache_key = self._get_cache_key("search", f"{query}:{max_results}")
        cached_result = self._get_cached(cache_key)
        if cached_result is not None:
            logger.info(f"Cache hit for query: {query}")
            return cached_result

        try:
            # Prepare search parameters
            params = {
                "q": query,
                "maxResults": min(max_results, 40),  # Google Books API limit
                "printType": "books",
                "langRestrict": "en",
            }

            if self.api_key:
                params["key"] = self.api_key

            # Make API request
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Process results
            books = []
            for item in data.get("items", []):
                book_data = self._map_google_book_to_cookbook(item)
                if book_data:
                    books.append(book_data)

            logger.info(f"Found {len(books)} books for query: {query}")

            # Cache the results
            self._set_cached(cache_key, books, SEARCH_CACHE_TTL)

            return books

        except requests.exceptions.RequestException as e:
            # Log the specific response for debugging
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                logger.error(
                    f"Google Books API request failed with status {status_code}: {e.response.text}"
                )
                if status_code == 429:
                    raise GoogleBooksAPIError(
                        "Too many requests. Please wait a moment and try again."
                    )
                if status_code == 403:
                    raise GoogleBooksAPIError(
                        "Google Books API access denied. This may be due to quota limits."
                    )
            else:
                logger.error(f"Google Books API request failed: {e}")
            raise GoogleBooksAPIError(f"Failed to search books: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in book search: {e}")
            raise GoogleBooksAPIError(f"Unexpected error: {str(e)}")

    def search_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """Search for a specific book by ISBN

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            Book dictionary or None if not found
        """
        # Clean ISBN (remove hyphens and spaces)
        cleaned_isbn = isbn.replace("-", "").replace(" ", "")

        query = f"isbn:{cleaned_isbn}"
        results = self.search_books(query, max_results=1)

        return results[0] if results else None

    def search_by_title_author(
        self, title: str, author: str = None
    ) -> List[Dict[str, Any]]:
        """Search for books by title and optionally author

        Args:
            title: Book title
            author: Author name (optional)

        Returns:
            List of book dictionaries
        """
        query_parts = [f"intitle:{title}"]

        if author:
            query_parts.append(f"inauthor:{author}")

        query = " ".join(query_parts)
        return self.search_books(query)

    def get_book_details(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific book

        Args:
            book_id: Google Books volume ID

        Returns:
            Book dictionary or None if not found
        """
        # Check cache first
        cache_key = self._get_cache_key("details", book_id)
        cached_result = self._get_cached(cache_key)
        if cached_result is not None:
            logger.info(f"Cache hit for book details: {book_id}")
            return cached_result

        try:
            params = {}
            if self.api_key:
                params["key"] = self.api_key

            url = f"{self.BASE_URL}/{book_id}"
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            item = response.json()
            book_data = self._map_google_book_to_cookbook(item)

            # Cache the result
            if book_data:
                self._set_cached(cache_key, book_data, DETAILS_CACHE_TTL)

            return book_data

        except requests.exceptions.RequestException as e:
            # Log the specific response for debugging
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                logger.error(
                    f"Google Books API request failed with status {status_code}: {e.response.text}"
                )
                if status_code == 429:
                    logger.error(
                        f"Rate limited when getting book details for {book_id}"
                    )
                elif status_code == 403:
                    logger.error(
                        f"Google Books API access denied for book details {book_id}"
                    )
            else:
                logger.error(f"Failed to get book details for {book_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting book details: {e}")
            return None

    def _map_google_book_to_cookbook(
        self, item: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Map Google Books API response to cookbook format

        Args:
            item: Google Books API item

        Returns:
            Mapped cookbook dictionary
        """
        try:
            volume_info = item.get("volumeInfo", {})

            # Extract basic information
            title = volume_info.get("title", "").strip()
            if not title:
                return None

            # Extract authors
            authors = volume_info.get("authors", [])
            author = authors[0] if authors else ""

            # Extract identifiers (ISBN)
            isbn = ""
            identifiers = volume_info.get("industryIdentifiers", [])
            for identifier in identifiers:
                if identifier.get("type") in ["ISBN_13", "ISBN_10"]:
                    isbn = identifier.get("identifier", "")
                    break

            # Extract publication date
            publication_date = None
            pub_date_str = volume_info.get("publishedDate", "")
            if pub_date_str:
                try:
                    # Handle various date formats
                    if len(pub_date_str) == 4:  # Just year
                        publication_date = datetime(int(pub_date_str), 1, 1)
                    elif len(pub_date_str) == 7:  # Year-month
                        year, month = pub_date_str.split("-")
                        publication_date = datetime(int(year), int(month), 1)
                    else:  # Full date
                        publication_date = datetime.strptime(pub_date_str, "%Y-%m-%d")
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse publication date: {pub_date_str}")

            # Extract description
            description = volume_info.get("description", "")

            # Extract thumbnail
            image_links = volume_info.get("imageLinks", {})
            thumbnail = image_links.get("thumbnail") or image_links.get(
                "smallThumbnail"
            )

            # Build cookbook dictionary
            cookbook_data = {
                "google_books_id": item.get("id"),
                "title": title,
                "author": author,
                "publisher": volume_info.get("publisher", ""),
                "publication_date": publication_date,
                "isbn": isbn,
                "description": description,
                "page_count": volume_info.get("pageCount"),
                "categories": volume_info.get("categories", []),
                "language": volume_info.get("language", "en"),
                "thumbnail_url": thumbnail,
                "google_books_url": item.get("selfLink"),
                "source": "google_books",
            }

            return cookbook_data

        except Exception as e:
            logger.error(f"Error mapping Google Books item: {e}")
            return None


class GoogleBooksAPIError(Exception):
    """Exception raised for Google Books API errors"""

    pass


# Helper functions for common search patterns
def search_cookbook_by_title(title: str, api_key: str = None) -> List[Dict[str, Any]]:
    """Convenience function to search for cookbooks by title

    Args:
        title: Book title to search for
        api_key: Google Books API key

    Returns:
        List of book dictionaries
    """
    service = GoogleBooksService(api_key)

    # Add cookbook-specific search terms
    enhanced_query = f"{title} cookbook OR cooking OR recipe"
    return service.search_books(enhanced_query)


def search_cookbook_by_author(author: str, api_key: str = None) -> List[Dict[str, Any]]:
    """Convenience function to search for cookbooks by author

    Args:
        author: Author name to search for
        api_key: Google Books API key

    Returns:
        List of book dictionaries
    """
    service = GoogleBooksService(api_key)

    # Add cookbook-specific search terms
    enhanced_query = f"inauthor:{author} cookbook OR cooking OR recipe"
    return service.search_books(enhanced_query)

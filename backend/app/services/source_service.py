"""
Source service for managing recipe sources (domains).
Handles domain extraction, favicon URLs, and source creation.
"""

import logging
import traceback
from typing import Optional
from urllib.parse import urlparse

from app import db
from app.models.source import Source

logger = logging.getLogger(__name__)


class SourceService:
    """Service for managing recipe sources."""

    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """
        Extract and normalize the domain from a URL.

        Args:
            url: The URL to extract the domain from

        Returns:
            The normalized domain (lowercase, without www. prefix) or None if invalid
        """
        if not url:
            return None

        try:
            # Parse the URL
            parsed = urlparse(url)

            # Get the netloc (domain with port)
            domain = parsed.netloc

            # If no netloc, try treating the path as a domain (for URLs without scheme)
            if not domain and parsed.path:
                # Handle URLs like "example.com/recipe"
                domain = parsed.path.split("/")[0]

            if not domain:
                return None

            # Remove port if present
            domain = domain.split(":")[0]

            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]

            # Lowercase
            domain = domain.lower()

            # Basic validation - must have at least one dot
            if "." not in domain:
                return None

            return domain

        except Exception as e:
            logger.error(
                f"Error extracting domain from URL '{url}': {str(e)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            return None

    @staticmethod
    def get_favicon_url(domain: str) -> str:
        """
        Get a favicon URL for a domain using Google's favicon service.

        Args:
            domain: The domain to get the favicon for

        Returns:
            URL to the favicon image
        """
        # Use Google's favicon service for reliable favicon fetching
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=32"

    @staticmethod
    def get_or_create_source(user_id: int, source_url: str) -> Optional[Source]:
        """
        Get an existing source for a domain or create a new one.
        Increments the recipe_count for the source.

        Args:
            user_id: The ID of the user who owns the source
            source_url: The URL of the recipe source

        Returns:
            The Source object or None if the URL is invalid
        """
        domain = SourceService.extract_domain(source_url)

        if not domain:
            logger.warning(f"Could not extract domain from URL: {source_url}")
            return None

        try:
            # Try to find existing source for this user and domain
            source = Source.query.filter_by(
                user_id=user_id,
                domain=domain
            ).first()

            if source:
                # Increment recipe count for existing source
                source.increment_recipe_count()
                logger.info(
                    f"Found existing source {source.id} for domain '{domain}', "
                    f"recipe_count now {source.recipe_count}"
                )
            else:
                # Create new source
                favicon_url = SourceService.get_favicon_url(domain)

                source = Source(
                    domain=domain,
                    name=None,  # User can set this later
                    favicon_url=favicon_url,
                    recipe_count=1,  # Start with 1 since we're creating it for a recipe
                    user_id=user_id,
                )
                db.session.add(source)
                db.session.flush()  # Get the ID

                logger.info(
                    f"Created new source {source.id} for domain '{domain}' "
                    f"for user {user_id}"
                )

            return source

        except Exception as e:
            logger.error(
                f"Error getting/creating source for domain '{domain}': {str(e)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            return None

    @staticmethod
    def decrement_source_count(source_id: int) -> None:
        """
        Decrement the recipe count for a source.
        Called when a recipe is deleted.

        Args:
            source_id: The ID of the source to update
        """
        try:
            source = Source.query.get(source_id)
            if source:
                source.decrement_recipe_count()
                logger.info(
                    f"Decremented recipe_count for source {source_id}, "
                    f"now {source.recipe_count}"
                )
        except Exception as e:
            logger.error(
                f"Error decrementing source count for source {source_id}: {str(e)}\n"
                f"Traceback: {traceback.format_exc()}"
            )

    @staticmethod
    def update_source_name(source_id: int, user_id: int, name: Optional[str]) -> Optional[Source]:
        """
        Update the display name for a source.

        Args:
            source_id: The ID of the source to update
            user_id: The ID of the user (for authorization)
            name: The new display name (or None to clear)

        Returns:
            The updated Source or None if not found/unauthorized
        """
        try:
            source = Source.query.filter_by(id=source_id, user_id=user_id).first()

            if not source:
                logger.warning(
                    f"Source {source_id} not found or not owned by user {user_id}"
                )
                return None

            source.name = name.strip() if name else None
            logger.info(f"Updated source {source_id} name to '{source.name}'")

            return source

        except Exception as e:
            logger.error(
                f"Error updating source name for source {source_id}: {str(e)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            return None

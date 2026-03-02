from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class Source(db.Model):
    """
    Represents a recipe source domain (e.g., seriouseats.com).
    Sources are auto-created when importing recipes from URLs.
    Each user has their own source records (domain + user_id unique).
    """

    __tablename__ = "source"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(
        String(200)
    )  # User-editable display name
    favicon_url: Mapped[Optional[str]] = mapped_column(String(500))
    recipe_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Unique constraint: each user can only have one source per domain
    __table_args__ = (
        UniqueConstraint("domain", "user_id", name="unique_source_domain_per_user"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sources")
    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe", back_populates="source_ref", lazy="dynamic"
    )

    def get_display_name(self) -> str:
        """Return the display name, falling back to domain if name is not set."""
        return self.name if self.name else self.domain

    def increment_recipe_count(self) -> None:
        """Increment the recipe count."""
        self.recipe_count += 1

    def decrement_recipe_count(self) -> None:
        """Decrement the recipe count (minimum 0)."""
        if self.recipe_count > 0:
            self.recipe_count -= 1

    def to_dict(self) -> dict:
        """Convert source to dictionary representation."""
        return {
            "id": self.id,
            "domain": self.domain,
            "name": self.name,
            "display_name": self.get_display_name(),
            "favicon_url": self.favicon_url,
            "recipe_count": self.recipe_count,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

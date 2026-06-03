"""BookProject and related models.

A BookProject is a multi-contributor cookbook project: an organizer creates the project,
generates a share link, and contributors (with or without accounts) submit recipes that
land in the organizer's project. The project ultimately produces a downloadable PDF
(free watermarked preview / paid clean export) and, in Phase 2, a printed book.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class ProjectType(str, Enum):
    """Drives template selection and contributor-landing copy. Generic enough to support
    new occasions in future without schema changes."""

    WEDDING = "wedding"
    ANNIVERSARY = "anniversary"
    HEIRLOOM = "heirloom"
    MEMORIAL = "memorial"
    HOLIDAY = "holiday"
    GENERAL = "general"


class ProjectStatus(str, Enum):
    """Project lifecycle from open collection through final export."""

    COLLECTING = "collecting"
    REVIEW = "review"
    FINALIZED = "finalized"
    EXPORTED = "exported"


class BookProject(db.Model):
    """A collaborative cookbook project owned by one user, contributed to by many."""

    __tablename__ = "book_project"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"), nullable=False, index=True
    )

    # SQLAlchemy's default db.Enum serializes by enum NAME (uppercase like
    # WEDDING). Our PG enum types are created with lowercase VALUES (see
    # book_projects_001 migration), so without values_callable PG rejects
    # inserts with "invalid input value for enum projecttype: WEDDING".
    # SQLite stores enums as plain strings and accepts either, which is why
    # this bug only surfaces in production.
    project_type: Mapped[ProjectType] = mapped_column(
        db.Enum(
            ProjectType,
            name="projecttype",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ProjectType.GENERAL,
        nullable=False,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        db.Enum(
            ProjectStatus,
            name="projectstatus",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ProjectStatus.COLLECTING,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(300))
    dedication: Mapped[Optional[str]] = mapped_column(Text)

    honorees: Mapped[Optional[list]] = mapped_column(JSON)

    occasion_date: Mapped[Optional[datetime]] = mapped_column(Date)
    submission_deadline: Mapped[Optional[datetime]] = mapped_column(Date)

    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500))

    project_metadata: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped["User"] = relationship("User", backref="book_projects")
    share_links: Mapped[List["ProjectShareLink"]] = relationship(
        "ProjectShareLink",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    contributors: Mapped[List["GuestContributor"]] = relationship(
        "GuestContributor",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe", back_populates="book_project"
    )
    exports: Mapped[List["BookProjectExport"]] = relationship(
        "BookProjectExport",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_counts: bool = True) -> dict:
        result = {
            "id": self.id,
            "owner_user_id": self.owner_user_id,
            "project_type": self.project_type.value if self.project_type else None,
            "status": self.status.value if self.status else None,
            "title": self.title,
            "subtitle": self.subtitle,
            "dedication": self.dedication,
            "honorees": self.honorees or [],
            "occasion_date": self.occasion_date.isoformat()
            if self.occasion_date
            else None,
            "submission_deadline": self.submission_deadline.isoformat()
            if self.submission_deadline
            else None,
            "cover_image_url": self.cover_image_url,
            "metadata": self.project_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_counts:
            included_recipes = [
                r
                for r in self.recipes
                if not getattr(r, "is_excluded_from_project", False)
            ]
            result["recipe_count"] = len(included_recipes)
            result["contributor_count"] = len(self.contributors)
        return result


class ProjectShareLink(db.Model):
    """A shareable token that lets unauthenticated visitors submit recipes to a project."""

    __tablename__ = "project_share_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("book_project.id"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    submission_cap: Mapped[Optional[int]] = mapped_column(Integer)
    submission_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["BookProject"] = relationship(
        "BookProject", back_populates="share_links"
    )
    contributors: Mapped[List["GuestContributor"]] = relationship(
        "GuestContributor", back_populates="share_link"
    )

    def is_active(self) -> bool:
        """Whether the link still accepts submissions right now."""
        if self.revoked:
            return False
        if self.expires_at is not None and self.expires_at < datetime.utcnow():
            return False
        if (
            self.submission_cap is not None
            and self.submission_count >= self.submission_cap
        ):
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "token": self.token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "submission_cap": self.submission_cap,
            "submission_count": self.submission_count,
            "revoked": self.revoked,
            "is_active": self.is_active(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GuestContributor(db.Model):
    """A non-account contributor who submitted recipes via a project share link.

    No password, no auth credentials. The display_name is used for per-recipe
    attribution ("From Aunt Linda"). The optional email is kept for a future
    magic-link claim flow that will let contributors take ownership of their
    submissions if they ever create an account.
    """

    __tablename__ = "guest_contributor"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("book_project.id"), nullable=False, index=True
    )
    share_link_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("project_share_link.id"), index=True
    )

    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["BookProject"] = relationship(
        "BookProject", back_populates="contributors"
    )
    share_link: Mapped[Optional["ProjectShareLink"]] = relationship(
        "ProjectShareLink", back_populates="contributors"
    )

    def to_dict(self, include_email: bool = False) -> dict:
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_email:
            result["email"] = self.email
        return result


class BookProjectExport(db.Model):
    """A generated PDF export of a BookProject. Watermarked previews are free; clean
    exports are gated by a one-time Stripe payment recorded on the linked Payment row."""

    __tablename__ = "book_project_export"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("book_project.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"), nullable=False, index=True
    )
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payments.id"))

    pdf_file_path: Mapped[Optional[str]] = mapped_column(String(500))
    cloudinary_public_id: Mapped[Optional[str]] = mapped_column(String(500))
    cloudinary_url: Mapped[Optional[str]] = mapped_column(String(1000))
    is_watermarked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["BookProject"] = relationship(
        "BookProject", back_populates="exports"
    )
    user: Mapped["User"] = relationship("User", backref="book_project_exports")

    def to_dict(self) -> dict:
        # is_ready signals whether the rendered PDF is actually available for
        # download. Paid exports are placeholder rows from the moment the
        # PaymentIntent is created; the storage fields don't get populated
        # until the Stripe webhook fires and the render completes. Without
        # this signal the frontend can't distinguish "row exists" from "file
        # exists" and ends up offering a download that 202s.
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "payment_id": self.payment_id,
            "is_watermarked": self.is_watermarked,
            "is_ready": bool(self.pdf_file_path or self.cloudinary_url),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

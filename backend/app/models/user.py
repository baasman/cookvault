from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db, bcrypt


class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile information
    first_name: Mapped[Optional[str]] = mapped_column(String(50))
    last_name: Mapped[Optional[str]] = mapped_column(String(50))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Account status and role
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER)
    status: Mapped[UserStatus] = mapped_column(default=UserStatus.PENDING_VERIFICATION)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Email verification
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255))
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255))
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    passwords: Mapped[List["Password"]] = relationship(
        "Password", back_populates="user", cascade="all, delete-orphan"
    )
    cookbooks: Mapped[List["Cookbook"]] = relationship(
        "Cookbook", back_populates="user"
    )
    recipes: Mapped[List["Recipe"]] = relationship("Recipe", back_populates="user")
    user_sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    recipe_collections: Mapped[List["UserRecipeCollection"]] = relationship(
        "UserRecipeCollection", back_populates="user", cascade="all, delete-orphan"
    )
    recipe_notes: Mapped[List["RecipeNote"]] = relationship(
        "RecipeNote", back_populates="user", cascade="all, delete-orphan"
    )
    recipe_comments: Mapped[List["RecipeComment"]] = relationship(
        "RecipeComment", back_populates="user", cascade="all, delete-orphan"
    )
    recipe_groups: Mapped[List["RecipeGroup"]] = relationship(
        "RecipeGroup", back_populates="user", cascade="all, delete-orphan"
    )
    copyright_consents: Mapped[List["CopyrightConsent"]] = relationship(
        "CopyrightConsent", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the user's password."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_account_locked(self) -> bool:
        """Check if the account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def increment_failed_login(self) -> None:
        """Increment failed login attempts and lock account if needed."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            # Lock account for 30 minutes after 5 failed attempts
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)

    def reset_failed_login(self) -> None:
        """Reset failed login attempts and unlock account."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.utcnow()

    def generate_verification_token(self) -> str:
        """Generate a new email verification token."""
        import secrets

        token = secrets.token_urlsafe(32)
        self.email_verification_token = token
        return token

    def generate_password_reset_token(self) -> str:
        """Generate a new password reset token."""
        import secrets
        from datetime import timedelta

        token = secrets.token_urlsafe(32)
        self.password_reset_token = token
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        return token

    def is_password_reset_valid(self) -> bool:
        """Check if the password reset token is still valid."""
        if not self.password_reset_token or not self.password_reset_expires:
            return False
        return datetime.utcnow() < self.password_reset_expires

    def clear_password_reset(self) -> None:
        """Clear password reset token and expiration."""
        self.password_reset_token = None
        self.password_reset_expires = None

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert user to dictionary representation."""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email if include_sensitive else None,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "role": self.role.value,
            "status": self.status.value,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

        if include_sensitive:
            data.update(
                {
                    "failed_login_attempts": self.failed_login_attempts,
                    "is_locked": self.is_account_locked(),
                    "email_verified_at": (
                        self.email_verified_at.isoformat()
                        if self.email_verified_at
                        else None
                    ),
                }
            )

        return data


class Password(db.Model):
    """Model to track password history for security purposes."""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Optional: Track password strength/quality
    strength_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100

    # Track if password was compromised (e.g., found in breached password lists)
    is_compromised: Mapped[bool] = mapped_column(Boolean, default=False)
    compromised_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="passwords")

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches this stored password."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Convert password record to dictionary (without sensitive data)."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "strength_score": self.strength_score,
            "is_compromised": self.is_compromised,
            "compromised_at": (
                self.compromised_at.isoformat() if self.compromised_at else None
            ),
        }


class UserSession(db.Model):
    """Model to track user sessions for security and analytics."""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Session metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    device_info: Mapped[Optional[str]] = mapped_column(String(255))

    # Session lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    logout_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_sessions")

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the session is valid (active and not expired)."""
        return self.is_active and not self.is_expired()

    def invalidate(self) -> None:
        """Invalidate the session."""
        self.is_active = False
        self.logout_at = datetime.utcnow()

    def extend_session(self, hours: int = 24) -> None:
        """Extend the session expiration time."""
        from datetime import timedelta

        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_activity = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert session to dictionary representation."""
        return {
            "id": self.id,
            "ip_address": self.ip_address,
            "device_info": self.device_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "logout_at": self.logout_at.isoformat() if self.logout_at else None,
        }


class CopyrightConsent(db.Model):
    """Model to track copyright consent for recipe uploads and publications."""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    recipe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recipe.id"))

    # Consent details
    consent_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    consent_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'upload' or 'publish'

    # Tracking
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Status
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="copyright_consents")
    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")

    def revoke(self) -> None:
        """Revoke this consent record."""
        self.is_valid = False
        self.revoked_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert consent to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "recipe_id": self.recipe_id,
            "consent_data": self.consent_data,
            "consent_type": self.consent_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_valid": self.is_valid,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }

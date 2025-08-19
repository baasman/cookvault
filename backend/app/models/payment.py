from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class SubscriptionTier(Enum):
    FREE = "free"
    PREMIUM = "premium"


class SubscriptionStatus(Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    UNPAID = "unpaid"


class PaymentType(Enum):
    SUBSCRIPTION = "subscription"
    COOKBOOK = "cookbook"


class PaymentStatus(Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class Subscription(db.Model):
    """Model for user subscriptions and premium account management."""
    __tablename__ = 'subscriptions'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, unique=True)
    
    # Stripe integration fields
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Subscription details
    tier: Mapped[SubscriptionTier] = mapped_column(default=SubscriptionTier.FREE)
    status: Mapped[SubscriptionStatus] = mapped_column(default=SubscriptionStatus.ACTIVE)
    
    # Billing cycle info
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Upload tracking for free tier
    monthly_upload_count: Mapped[int] = mapped_column(Integer, default=0)
    upload_count_reset_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscription")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="subscription")

    def is_premium(self) -> bool:
        """Check if user has active premium subscription."""
        return (
            self.tier == SubscriptionTier.PREMIUM 
            and self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
        )

    def can_upload_recipe(self) -> bool:
        """Check if user can upload another recipe based on their plan."""
        if self.is_premium():
            return True
        
        # Free tier upload limit check
        return self.get_remaining_uploads() > 0

    def get_remaining_uploads(self) -> int:
        """Get remaining uploads for current period (free tier only)."""
        if self.is_premium():
            return -1  # Unlimited for premium
        
        from app.config import Config
        free_limit = getattr(Config, 'FREE_TIER_UPLOAD_LIMIT', 10)
        
        # Handle None case for monthly_upload_count
        upload_count = self.monthly_upload_count if self.monthly_upload_count is not None else 0
        
        return max(0, free_limit - upload_count)

    def increment_upload_count(self) -> None:
        """Increment upload count for free tier users."""
        if not self.is_premium():
            # Handle None case
            if self.monthly_upload_count is None:
                self.monthly_upload_count = 1
            else:
                self.monthly_upload_count += 1

    def reset_monthly_uploads(self) -> None:
        """Reset monthly upload count (called by scheduled task)."""
        self.monthly_upload_count = 0
        self.upload_count_reset_date = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert subscription to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tier": self.tier.value,
            "status": self.status.value,
            "is_premium": self.is_premium(),
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "canceled_at": self.canceled_at.isoformat() if self.canceled_at else None,
            "monthly_upload_count": self.monthly_upload_count,
            "remaining_uploads": self.get_remaining_uploads(),
            "can_upload": self.can_upload_recipe(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Payment(db.Model):
    """Model for tracking all payments and transactions."""
    __tablename__ = 'payments'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    subscription_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subscriptions.id"))
    cookbook_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cookbook.id"))
    
    # Stripe integration fields
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Payment details
    payment_type: Mapped[PaymentType] = mapped_column(nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.PENDING)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(String(500))
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription", back_populates="payments")
    cookbook: Mapped[Optional["Cookbook"]] = relationship("Cookbook")

    def to_dict(self) -> dict:
        """Convert payment to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subscription_id": self.subscription_id,
            "cookbook_id": self.cookbook_id,
            "payment_type": self.payment_type.value,
            "status": self.status.value,
            "amount": float(self.amount),
            "currency": self.currency,
            "description": self.description,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CookbookPurchase(db.Model):
    """Model for tracking cookbook purchases by users."""
    __tablename__ = 'cookbook_purchases'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    cookbook_id: Mapped[int] = mapped_column(ForeignKey("cookbook.id"), nullable=False)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    
    # Purchase details
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    access_granted: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    purchase_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    access_revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="cookbook_purchases")
    cookbook: Mapped["Cookbook"] = relationship("Cookbook", back_populates="purchases")
    payment: Mapped["Payment"] = relationship("Payment")

    # Unique constraint to prevent duplicate purchases
    __table_args__ = (db.UniqueConstraint('user_id', 'cookbook_id', name='unique_user_cookbook_purchase'),)

    def has_access(self) -> bool:
        """Check if user still has access to this cookbook."""
        return self.access_granted and self.access_revoked_at is None

    def revoke_access(self) -> None:
        """Revoke access to this cookbook (e.g., due to refund)."""
        self.access_granted = False
        self.access_revoked_at = datetime.utcnow()

    def restore_access(self) -> None:
        """Restore access to this cookbook."""
        self.access_granted = True
        self.access_revoked_at = None

    def to_dict(self) -> dict:
        """Convert cookbook purchase to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "cookbook_id": self.cookbook_id,
            "payment_id": self.payment_id,
            "purchase_price": float(self.purchase_price),
            "access_granted": self.access_granted,
            "has_access": self.has_access(),
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "access_revoked_at": self.access_revoked_at.isoformat() if self.access_revoked_at else None,
        }
"""
Database models for print-on-demand orders via Lulu API.

This module contains models for managing cookbook print orders,
specifications, and fulfillment tracking.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Boolean,
    Numeric,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class PrintOrderStatus(Enum):
    """Status of a print order throughout its lifecycle."""

    DRAFT = "draft"  # Order being configured
    PENDING_PAYMENT = "pending_payment"  # Awaiting payment
    PAID = "paid"  # Payment completed, ready for processing
    PROCESSING = "processing"  # Payment received, preparing for print
    VALIDATING = "validating"  # Files being validated by Lulu
    PRINTING = "printing"  # In production at printer
    SHIPPED = "shipped"  # Order shipped
    DELIVERED = "delivered"  # Order delivered
    CANCELLED = "cancelled"  # Order cancelled
    FAILED = "failed"  # Order failed (validation or other error)
    REFUNDED = "refunded"  # Order refunded


class BindingType(Enum):
    """Available binding types for printed books."""

    PERFECT_BOUND = "perfect_bound"  # Standard paperback
    COIL_BOUND = "coil_bound"  # Spiral binding
    SADDLE_STITCH = "saddle_stitch"  # Stapled (for smaller books)
    CASE_WRAP = "case_wrap"  # Hardcover with printed case
    DUST_JACKET = "dust_jacket"  # Hardcover with dust jacket


class TrimSize(Enum):
    """Standard book trim sizes."""

    US_LETTER = "US_LETTER"  # 8.5" x 11"
    US_TRADE = "US_TRADE"  # 6" x 9"
    DIGEST = "DIGEST"  # 5.5" x 8.5"
    SQUARE_8 = "SQUARE_8"  # 8" x 8"
    LANDSCAPE_9x7 = "LANDSCAPE_9x7"  # 9" x 7"
    A4 = "A4"  # 210mm x 297mm
    A5 = "A5"  # 148mm x 210mm


class PaperType(Enum):
    """Paper types available for interior pages."""

    STANDARD_WHITE = "standard_white"  # Standard 60# white
    STANDARD_CREAM = "standard_cream"  # Standard 60# cream
    PREMIUM_WHITE = "premium_white"  # Premium 70# white
    PREMIUM_COLOR = "premium_color"  # Premium color pages


class CoverFinish(Enum):
    """Cover finish options."""

    MATTE = "matte"
    GLOSS = "gloss"


class PrintSpecification(db.Model):
    """Specifications for a print job."""

    __tablename__ = "print_specifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Physical specifications
    trim_size: Mapped[TrimSize] = mapped_column(default=TrimSize.US_TRADE)
    binding_type: Mapped[BindingType] = mapped_column(default=BindingType.PERFECT_BOUND)
    paper_type: Mapped[PaperType] = mapped_column(default=PaperType.STANDARD_WHITE)
    cover_finish: Mapped[CoverFinish] = mapped_column(default=CoverFinish.MATTE)

    # Template selection (affects interior PDF and cover styling)
    # Values: 'modern' (default), 'classic', 'book'
    template: Mapped[str] = mapped_column(String(50), default="modern")

    # Page information
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    color_pages: Mapped[bool] = mapped_column(Boolean, default=False)

    # Lulu specific product codes (populated after validation)
    lulu_pod_package_id: Mapped[Optional[str]] = mapped_column(String(100))
    lulu_page_count: Mapped[Optional[int]] = mapped_column(
        Integer
    )  # May differ from our count

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    print_orders: Mapped[list["PrintOrder"]] = relationship(
        "PrintOrder", back_populates="specification"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert specification to dictionary."""
        return {
            "id": self.id,
            "trim_size": self.trim_size.value,
            "binding_type": self.binding_type.value,
            "paper_type": self.paper_type.value,
            "cover_finish": self.cover_finish.value,
            "template": self.template,
            "page_count": self.page_count,
            "color_pages": self.color_pages,
            "lulu_pod_package_id": self.lulu_pod_package_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PrintOrder(db.Model):
    """Model for managing print-on-demand orders."""

    __tablename__ = "print_orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    # User and cookbook references
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    cookbook_id: Mapped[int] = mapped_column(ForeignKey("cookbook.id"), nullable=False)
    specification_id: Mapped[int] = mapped_column(
        ForeignKey("print_specifications.id"), nullable=False
    )

    # Order details
    order_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[PrintOrderStatus] = mapped_column(default=PrintOrderStatus.DRAFT)

    # Lulu integration
    lulu_print_job_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    lulu_line_item_id: Mapped[Optional[str]] = mapped_column(String(255))
    lulu_status: Mapped[Optional[str]] = mapped_column(String(100))

    # File URLs (temporary signed URLs for Lulu)
    interior_file_url: Mapped[Optional[str]] = mapped_column(Text)
    cover_file_url: Mapped[Optional[str]] = mapped_column(Text)

    # Validation results from Lulu
    interior_validation_status: Mapped[Optional[str]] = mapped_column(String(50))
    interior_validation_errors: Mapped[Optional[str]] = mapped_column(Text)
    cover_validation_status: Mapped[Optional[str]] = mapped_column(String(50))
    cover_validation_errors: Mapped[Optional[str]] = mapped_column(Text)

    # Shipping information
    shipping_name: Mapped[str] = mapped_column(String(200), nullable=False)
    shipping_address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    shipping_city: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_state_code: Mapped[str] = mapped_column(String(50), nullable=False)
    shipping_postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_country_code: Mapped[str] = mapped_column(
        String(2), default="US", nullable=False
    )
    shipping_phone: Mapped[Optional[str]] = mapped_column(String(50))
    shipping_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Shipping tracking
    shipping_carrier: Mapped[Optional[str]] = mapped_column(String(100))
    tracking_number: Mapped[Optional[str]] = mapped_column(String(255))
    tracking_url: Mapped[Optional[str]] = mapped_column(Text)
    estimated_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    actual_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Cost breakdown (all amounts in USD)
    printing_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Payment reference
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payments.id"))
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255))
    payment_status: Mapped[Optional[str]] = mapped_column(String(50))

    # Refund tracking
    refund_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    refund_reason: Mapped[Optional[str]] = mapped_column(String(500))
    stripe_refund_id: Mapped[Optional[str]] = mapped_column(String(255))
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Additional metadata
    order_metadata: Mapped[Optional[Dict]] = mapped_column(JSON)  # Additional data

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime
    )  # When sent to Lulu
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime
    )  # When payment completed
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="print_orders")
    cookbook: Mapped["Cookbook"] = relationship(
        "Cookbook", back_populates="print_orders"
    )
    specification: Mapped["PrintSpecification"] = relationship(
        "PrintSpecification", back_populates="print_orders"
    )
    payment: Mapped[Optional["Payment"]] = relationship(
        "Payment", back_populates="print_order", foreign_keys="Payment.print_order_id"
    )
    status_updates: Mapped[list["PrintOrderStatusUpdate"]] = relationship(
        "PrintOrderStatusUpdate",
        back_populates="print_order",
        cascade="all, delete-orphan",
    )

    def calculate_total(self) -> Decimal:
        """Calculate total cost including all fees."""
        return (
            self.printing_cost
            + self.shipping_cost
            + self.tax_amount
            + self.platform_fee
        )

    def can_cancel(self) -> bool:
        """Check if order can be cancelled."""
        return self.status in [
            PrintOrderStatus.DRAFT,
            PrintOrderStatus.PENDING_PAYMENT,
            PrintOrderStatus.PAID,
            PrintOrderStatus.PROCESSING,
            PrintOrderStatus.VALIDATING,
        ]

    def can_reorder(self) -> bool:
        """Check if order can be reordered."""
        return self.status in [
            PrintOrderStatus.DELIVERED,
            PrintOrderStatus.CANCELLED,
            PrintOrderStatus.REFUNDED,
        ]

    def to_dict(self, include_shipping: bool = False) -> Dict[str, Any]:
        """Convert order to dictionary."""
        result = {
            "id": self.id,
            "order_number": self.order_number,
            "cookbook_id": self.cookbook_id,
            "quantity": self.quantity,
            "status": self.status.value,
            "specification": self.specification.to_dict()
            if self.specification
            else None,
            "printing_cost": float(self.printing_cost),
            "shipping_cost": float(self.shipping_cost),
            "tax_amount": float(self.tax_amount),
            "platform_fee": float(self.platform_fee),
            "total_cost": float(self.total_cost),
            "tracking_number": self.tracking_number,
            "tracking_url": self.tracking_url,
            "estimated_delivery_date": (
                self.estimated_delivery_date.isoformat()
                if self.estimated_delivery_date
                else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "refund_amount": float(self.refund_amount) if self.refund_amount else None,
            "refund_reason": self.refund_reason,
            "refunded_at": self.refunded_at.isoformat() if self.refunded_at else None,
            "can_cancel": self.can_cancel(),
            "can_reorder": self.can_reorder(),
        }

        if include_shipping:
            result["shipping_address"] = {
                "name": self.shipping_name,
                "address_line1": self.shipping_address_line1,
                "address_line2": self.shipping_address_line2,
                "city": self.shipping_city,
                "state_code": self.shipping_state_code,
                "postal_code": self.shipping_postal_code,
                "country_code": self.shipping_country_code,
                "email": self.shipping_email,
                "phone": self.shipping_phone,
            }

        return result


class PrintOrderStatusUpdate(db.Model):
    """Track status changes for print orders."""

    __tablename__ = "print_order_status_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    print_order_id: Mapped[int] = mapped_column(
        ForeignKey("print_orders.id"), nullable=False
    )

    # Status change
    previous_status: Mapped[Optional[PrintOrderStatus]] = mapped_column()
    new_status: Mapped[PrintOrderStatus] = mapped_column(nullable=False)

    # Additional information
    message: Mapped[Optional[str]] = mapped_column(Text)
    lulu_event_type: Mapped[Optional[str]] = mapped_column(
        String(100)
    )  # Webhook event type
    lulu_event_data: Mapped[Optional[Dict]] = mapped_column(JSON)  # Raw webhook data

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    print_order: Mapped["PrintOrder"] = relationship(
        "PrintOrder", back_populates="status_updates"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert status update to dictionary."""
        return {
            "id": self.id,
            "previous_status": self.previous_status.value
            if self.previous_status
            else None,
            "new_status": self.new_status.value,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

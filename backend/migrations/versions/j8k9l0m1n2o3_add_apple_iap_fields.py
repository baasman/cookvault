"""Add Apple IAP fields to subscriptions

Revision ID: j8k9l0m1n2o3
Revises: i7j8k9l0m1n2
Create Date: 2026-03-30 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "j8k9l0m1n2o3"
down_revision = "i7j8k9l0m1n2"
branch_labels = None
depends_on = None


def upgrade():
    # Add payment provider field to track which provider manages the subscription
    op.add_column(
        "subscriptions",
        sa.Column("payment_provider", sa.String(20), nullable=True),
    )

    # Add Apple IAP specific fields
    op.add_column(
        "subscriptions",
        sa.Column("apple_original_transaction_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("apple_product_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("apple_expires_date", sa.DateTime(), nullable=True),
    )

    # Set existing subscriptions to 'stripe' as the payment provider
    # Only set for subscriptions that have a stripe_subscription_id
    op.execute(
        "UPDATE subscriptions SET payment_provider = 'stripe' WHERE stripe_subscription_id IS NOT NULL"
    )

    # Create index on apple_original_transaction_id for webhook lookups
    op.create_index(
        "ix_subscriptions_apple_original_transaction_id",
        "subscriptions",
        ["apple_original_transaction_id"],
    )


def downgrade():
    # Drop index first
    op.drop_index(
        "ix_subscriptions_apple_original_transaction_id", table_name="subscriptions"
    )

    # Remove Apple IAP columns
    op.drop_column("subscriptions", "apple_expires_date")
    op.drop_column("subscriptions", "apple_product_id")
    op.drop_column("subscriptions", "apple_original_transaction_id")
    op.drop_column("subscriptions", "payment_provider")

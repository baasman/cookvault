"""Add BOOK_PROJECT_EXPORT to the PaymentType enum.

Lets the existing Payment + Stripe webhook pipeline carry the paid-PDF
purchase for a BookProject. On PostgreSQL we extend the native enum type;
SQLite stores enum values as plain strings, so no DDL is needed there.

Revision ID: book_projects_003
Revises: book_projects_002
Create Date: 2026-05-14 17:30:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "book_projects_003"
down_revision = "book_projects_002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # IF NOT EXISTS guard so reruns / mixed environments stay idempotent.
        op.execute(
            "ALTER TYPE paymenttype ADD VALUE IF NOT EXISTS 'BOOK_PROJECT_EXPORT'"
        )


def downgrade():
    # PostgreSQL doesn't support removing enum values without rebuilding the type
    # and all dependent columns. Following the precedent of update_payment_type_enum,
    # this downgrade is a no-op.
    pass

"""Add phone verification fields

Revision ID: c7d8e9f0a1b2
Revises: be39cbc74574
Create Date: 2025-11-17 11:15:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c7d8e9f0a1b2"
down_revision = "be39cbc74574"
branch_labels = None
depends_on = None


def upgrade():
    # Add phone verification fields to user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("phone_number", sa.String(length=20), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "phone_verified", sa.Boolean(), nullable=False, server_default="0"
            )
        )
        batch_op.add_column(
            sa.Column("phone_verification_token", sa.String(length=10), nullable=True)
        )
        batch_op.add_column(
            sa.Column("phone_verification_sent_at", sa.DateTime(), nullable=True)
        )
        batch_op.create_unique_constraint("uq_user_phone_number", ["phone_number"])


def downgrade():
    # Remove phone verification fields from user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_constraint("uq_user_phone_number", type_="unique")
        batch_op.drop_column("phone_verification_sent_at")
        batch_op.drop_column("phone_verification_token")
        batch_op.drop_column("phone_verified")
        batch_op.drop_column("phone_number")

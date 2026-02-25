"""Add course_type column to recipe table

Revision ID: i7j8k9l0m1n2
Revises: h6i7j8k9l0m1
Create Date: 2026-02-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "i7j8k9l0m1n2"
down_revision = "h6i7j8k9l0m1"
branch_labels = None
depends_on = None


def upgrade():
    # Add course_type column to recipe table
    op.add_column("recipe", sa.Column("course_type", sa.String(50), nullable=True))

    # Create index for efficient filtering
    op.create_index("ix_recipe_course_type", "recipe", ["course_type"])


def downgrade():
    # Drop index first
    op.drop_index("ix_recipe_course_type", table_name="recipe")

    # Remove column
    op.drop_column("recipe", "course_type")

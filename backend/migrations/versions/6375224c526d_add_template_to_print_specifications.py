"""add_template_to_print_specifications

Revision ID: 6375224c526d
Revises: 4f75724a3f63
Create Date: 2025-11-26 11:39:09.509747

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6375224c526d"
down_revision = "4f75724a3f63"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "print_specifications",
        sa.Column("template", sa.String(50), nullable=False, server_default="modern"),
    )


def downgrade():
    op.drop_column("print_specifications", "template")

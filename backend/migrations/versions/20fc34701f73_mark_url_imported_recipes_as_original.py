"""mark url imported recipes as original

Revision ID: 20fc34701f73
Revises: 6e1730861e20
Create Date: 2026-04-23 10:30:22.597937

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20fc34701f73"
down_revision = "6e1730861e20"
branch_labels = None
depends_on = None


def upgrade():
    # URL-imported recipes have a source URL set. These are from public blogs
    # and should be shareable. Update any that were previously marked as
    # not original (is_original_recipe = False) when they have a source URL.
    op.execute(
        "UPDATE recipe SET is_original_recipe = true "
        "WHERE source IS NOT NULL AND source != '' AND is_original_recipe = false"
    )


def downgrade():
    op.execute(
        "UPDATE recipe SET is_original_recipe = false "
        "WHERE source IS NOT NULL AND source != ''"
    )

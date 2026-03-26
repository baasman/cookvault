"""Add missing enum values to processing enums

Revision ID: c8f9d2a3b4e5
Revises: 3bb951b65276
Create Date: 2026-03-09 11:05:00.000000

This migration adds enum values that were defined in Python but never properly
added to the PostgreSQL enum types. The previous migration (b5b229f5fefa)
attempted to use alter_column which doesn't work for adding enum values in PG.

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c8f9d2a3b4e5'
down_revision = '3bb951b65276'
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL requires ALTER TYPE ... ADD VALUE for enum additions
    # Note: ADD VALUE cannot be run inside a transaction in older PG versions,
    # but "IF NOT EXISTS" makes it safe to run even if values already exist.

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Add missing values to videoprocessingstatus enum
        # These were supposed to be added in b5b229f5fefa but alter_column doesn't work for PG enums
        video_status_values = [
            'FETCHING_METADATA',
            'EXTRACTING_CAPTIONS',
            'DOWNLOADING_AUDIO',
            'CANCELLED',
        ]
        for value in video_status_values:
            op.execute(f"ALTER TYPE videoprocessingstatus ADD VALUE IF NOT EXISTS '{value}'")

        # Add CANCELLED to processingstatus enum (for ProcessingJob and MultiRecipeJob)
        op.execute("ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade():
    # PostgreSQL doesn't support removing enum values easily
    # Would need to recreate the type and migrate data
    # For simplicity, we leave the values in place on downgrade
    pass

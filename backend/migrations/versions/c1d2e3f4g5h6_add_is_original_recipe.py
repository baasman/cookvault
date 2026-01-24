"""add_is_original_recipe

Revision ID: c1d2e3f4g5h6
Revises: b4c5d6e7f8a9
Create Date: 2026-01-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'b4c5d6e7f8a9'
branch_labels = None
depends_on = None


def upgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite: Use batch mode for table alterations
        # Add to recipe table
        with op.batch_alter_table('recipe', schema=None) as batch_op:
            # Default to True for backwards compatibility (existing recipes can be published)
            batch_op.add_column(sa.Column('is_original_recipe', sa.Boolean(), nullable=True, server_default='1'))

        # Add to processing_job table (to pass through from upload to recipe creation)
        with op.batch_alter_table('processing_job', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_original_recipe', sa.Boolean(), nullable=True))

        # Add to multi_recipe_job table (for multi-image uploads)
        with op.batch_alter_table('multi_recipe_job', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_original_recipe', sa.Boolean(), nullable=True))
    else:
        # PostgreSQL: Use standard operations
        # Add to recipe table - default to True for backwards compatibility
        op.add_column('recipe', sa.Column('is_original_recipe', sa.Boolean(), nullable=True, server_default='true'))

        # Add to processing_job table (to pass through from upload to recipe creation)
        op.add_column('processing_job', sa.Column('is_original_recipe', sa.Boolean(), nullable=True))

        # Add to multi_recipe_job table (for multi-image uploads)
        op.add_column('multi_recipe_job', sa.Column('is_original_recipe', sa.Boolean(), nullable=True))


def downgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite: Use batch mode
        with op.batch_alter_table('recipe', schema=None) as batch_op:
            batch_op.drop_column('is_original_recipe')
        with op.batch_alter_table('processing_job', schema=None) as batch_op:
            batch_op.drop_column('is_original_recipe')
        with op.batch_alter_table('multi_recipe_job', schema=None) as batch_op:
            batch_op.drop_column('is_original_recipe')
    else:
        # PostgreSQL: Use standard operations
        op.drop_column('recipe', 'is_original_recipe')
        op.drop_column('processing_job', 'is_original_recipe')
        op.drop_column('multi_recipe_job', 'is_original_recipe')

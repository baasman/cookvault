"""add_translate_to_english_option

Revision ID: e3f4g5h6i7j8
Revises: d2e3f4g5h6i7
Create Date: 2026-02-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3f4g5h6i7j8'
down_revision = 'd2e3f4g5h6i7'
branch_labels = None
depends_on = None


def upgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite: Use batch mode for table alterations
        with op.batch_alter_table('processing_job', schema=None) as batch_op:
            batch_op.add_column(sa.Column('translate_to_english', sa.Boolean(), nullable=False, server_default='0'))

        with op.batch_alter_table('multi_recipe_job', schema=None) as batch_op:
            batch_op.add_column(sa.Column('translate_to_english', sa.Boolean(), nullable=False, server_default='0'))
    else:
        # PostgreSQL: Use standard operations
        op.add_column('processing_job', sa.Column('translate_to_english', sa.Boolean(), nullable=False, server_default='false'))
        op.add_column('multi_recipe_job', sa.Column('translate_to_english', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        with op.batch_alter_table('processing_job', schema=None) as batch_op:
            batch_op.drop_column('translate_to_english')

        with op.batch_alter_table('multi_recipe_job', schema=None) as batch_op:
            batch_op.drop_column('translate_to_english')
    else:
        op.drop_column('processing_job', 'translate_to_english')
        op.drop_column('multi_recipe_job', 'translate_to_english')

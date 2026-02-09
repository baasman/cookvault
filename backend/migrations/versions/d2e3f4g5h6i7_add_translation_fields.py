"""add_translation_fields

Revision ID: d2e3f4g5h6i7
Revises: 22db193b35d3
Create Date: 2026-02-08 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2e3f4g5h6i7'
down_revision = '22db193b35d3'
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
            batch_op.add_column(sa.Column('source_language', sa.String(10), nullable=True))
            batch_op.add_column(sa.Column('source_language_name', sa.String(50), nullable=True))
            batch_op.add_column(sa.Column('is_translated', sa.Boolean(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('original_title', sa.String(200), nullable=True))
            batch_op.add_column(sa.Column('original_description', sa.Text(), nullable=True))

        # Add to instruction table
        with op.batch_alter_table('instruction', schema=None) as batch_op:
            batch_op.add_column(sa.Column('original_text', sa.Text(), nullable=True))

        # Add to processing_job table
        with op.batch_alter_table('processing_job', schema=None) as batch_op:
            batch_op.add_column(sa.Column('detected_language', sa.String(10), nullable=True))
            batch_op.add_column(sa.Column('detected_language_name', sa.String(50), nullable=True))
    else:
        # PostgreSQL: Use standard operations
        # Add to recipe table
        op.add_column('recipe', sa.Column('source_language', sa.String(10), nullable=True))
        op.add_column('recipe', sa.Column('source_language_name', sa.String(50), nullable=True))
        op.add_column('recipe', sa.Column('is_translated', sa.Boolean(), nullable=True, server_default='false'))
        op.add_column('recipe', sa.Column('original_title', sa.String(200), nullable=True))
        op.add_column('recipe', sa.Column('original_description', sa.Text(), nullable=True))

        # Add to instruction table
        op.add_column('instruction', sa.Column('original_text', sa.Text(), nullable=True))

        # Add to processing_job table
        op.add_column('processing_job', sa.Column('detected_language', sa.String(10), nullable=True))
        op.add_column('processing_job', sa.Column('detected_language_name', sa.String(50), nullable=True))


def downgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite: Use batch mode
        with op.batch_alter_table('recipe', schema=None) as batch_op:
            batch_op.drop_column('source_language')
            batch_op.drop_column('source_language_name')
            batch_op.drop_column('is_translated')
            batch_op.drop_column('original_title')
            batch_op.drop_column('original_description')

        with op.batch_alter_table('instruction', schema=None) as batch_op:
            batch_op.drop_column('original_text')

        with op.batch_alter_table('processing_job', schema=None) as batch_op:
            batch_op.drop_column('detected_language')
            batch_op.drop_column('detected_language_name')
    else:
        # PostgreSQL: Use standard operations
        op.drop_column('recipe', 'source_language')
        op.drop_column('recipe', 'source_language_name')
        op.drop_column('recipe', 'is_translated')
        op.drop_column('recipe', 'original_title')
        op.drop_column('recipe', 'original_description')

        op.drop_column('instruction', 'original_text')

        op.drop_column('processing_job', 'detected_language')
        op.drop_column('processing_job', 'detected_language_name')

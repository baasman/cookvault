"""add_user_id_to_processing_job

Revision ID: a8b9c0d1e2f3
Revises: 7a075144a4e5
Create Date: 2026-01-03 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8b9c0d1e2f3'
down_revision = '7a075144a4e5'
branch_labels = None
depends_on = None


def upgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite: Use batch mode for table alterations
        with op.batch_alter_table('processing_job', schema=None) as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
            batch_op.create_index('ix_processing_job_user_id', ['user_id'])
            batch_op.create_foreign_key(
                'fk_processing_job_user_id',
                'user',
                ['user_id'],
                ['id']
            )
    else:
        # PostgreSQL: Use standard operations
        op.add_column('processing_job', sa.Column('user_id', sa.Integer(), nullable=True))
        op.create_index('ix_processing_job_user_id', 'processing_job', ['user_id'])
        op.create_foreign_key(
            'fk_processing_job_user_id',
            'processing_job',
            'user',
            ['user_id'],
            ['id']
        )

    # Backfill: For completed jobs with recipes, use recipe.uploaded_by_id
    # For jobs without recipes, we can't backfill (that's OK, they're temporary)
    op.execute('''
        UPDATE processing_job
        SET user_id = (
            SELECT r.uploaded_by_id
            FROM recipe r
            WHERE r.id = processing_job.recipe_id
        )
        WHERE processing_job.recipe_id IS NOT NULL
        AND processing_job.user_id IS NULL
    ''')


def downgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite: Use batch mode
        with op.batch_alter_table('processing_job', schema=None) as batch_op:
            batch_op.drop_constraint('fk_processing_job_user_id', type_='foreignkey')
            batch_op.drop_index('ix_processing_job_user_id')
            batch_op.drop_column('user_id')
    else:
        # PostgreSQL: Use standard operations
        op.drop_constraint('fk_processing_job_user_id', 'processing_job', type_='foreignkey')
        op.drop_index('ix_processing_job_user_id', table_name='processing_job')
        op.drop_column('processing_job', 'user_id')

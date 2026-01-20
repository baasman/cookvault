"""add_system_group_fields

Revision ID: b4c5d6e7f8a9
Revises: a8b9c0d1e2f3
Create Date: 2026-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4c5d6e7f8a9'
down_revision = 'a8b9c0d1e2f3'
branch_labels = None
depends_on = None


def upgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite: Use batch mode for table alterations
        with op.batch_alter_table('recipe_group', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_system', sa.Boolean(), nullable=False, server_default='0'))
            batch_op.add_column(sa.Column('system_type', sa.String(50), nullable=True))
            # Note: SQLite doesn't support partial unique indexes, so we skip that
    else:
        # PostgreSQL: Use standard operations
        op.add_column('recipe_group', sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'))
        op.add_column('recipe_group', sa.Column('system_type', sa.String(50), nullable=True))
        # Create partial unique index to ensure only one system group of each type per user
        op.execute('''
            CREATE UNIQUE INDEX ix_recipe_group_user_system_type
            ON recipe_group (user_id, system_type)
            WHERE system_type IS NOT NULL
        ''')


def downgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if is_sqlite:
        # SQLite: Use batch mode
        with op.batch_alter_table('recipe_group', schema=None) as batch_op:
            batch_op.drop_column('system_type')
            batch_op.drop_column('is_system')
    else:
        # PostgreSQL: Use standard operations
        op.drop_index('ix_recipe_group_user_system_type', table_name='recipe_group')
        op.drop_column('recipe_group', 'system_type')
        op.drop_column('recipe_group', 'is_system')

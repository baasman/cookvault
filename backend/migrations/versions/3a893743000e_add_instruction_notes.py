"""add_instruction_notes

Revision ID: 3a893743000e
Revises: b76a528f4b72
Create Date: 2026-04-01 14:41:17.461507

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a893743000e'
down_revision = 'b76a528f4b72'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('instruction_notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('instruction_id', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['instruction_id'], ['instruction.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'instruction_id', name='unique_user_instruction_note')
    )


def downgrade():
    op.drop_table('instruction_notes')

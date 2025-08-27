"""Add image fields to instruction table

Revision ID: 445834817155
Revises: aeb529f3d285
Create Date: 2025-08-26 13:44:07.877470

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '445834817155'
down_revision = 'aeb529f3d285'
branch_labels = None
depends_on = None


def upgrade():
    # Add optional image fields to instruction table
    op.add_column('instruction', sa.Column('image_filename', sa.String(255), nullable=True))
    op.add_column('instruction', sa.Column('image_url', sa.String(500), nullable=True))
    op.add_column('instruction', sa.Column('cloudinary_public_id', sa.String(255), nullable=True))
    op.add_column('instruction', sa.Column('cloudinary_url', sa.String(500), nullable=True))
    op.add_column('instruction', sa.Column('cloudinary_thumbnail_url', sa.String(500), nullable=True))


def downgrade():
    # Remove image fields from instruction table
    op.drop_column('instruction', 'cloudinary_thumbnail_url')
    op.drop_column('instruction', 'cloudinary_url')
    op.drop_column('instruction', 'cloudinary_public_id')
    op.drop_column('instruction', 'image_url')
    op.drop_column('instruction', 'image_filename')

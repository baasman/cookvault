"""Add Cloudinary fields to RecipeImage

Revision ID: 573c9d494ec2
Revises: f6bb73209d4e
Create Date: 2025-08-21 09:30:28.630380

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '573c9d494ec2'
down_revision = 'f6bb73209d4e'
branch_labels = None
depends_on = None


def upgrade():
    # Add Cloudinary fields to recipe_image table
    op.add_column('recipe_image', sa.Column('cloudinary_public_id', sa.String(255), nullable=True))
    op.add_column('recipe_image', sa.Column('cloudinary_url', sa.String(500), nullable=True))
    op.add_column('recipe_image', sa.Column('cloudinary_thumbnail_url', sa.String(500), nullable=True))
    op.add_column('recipe_image', sa.Column('cloudinary_width', sa.Integer(), nullable=True))
    op.add_column('recipe_image', sa.Column('cloudinary_height', sa.Integer(), nullable=True))
    op.add_column('recipe_image', sa.Column('cloudinary_format', sa.String(10), nullable=True))
    op.add_column('recipe_image', sa.Column('cloudinary_bytes', sa.Integer(), nullable=True))
    
    # Add index on cloudinary_public_id for faster lookups
    op.create_index('idx_recipe_image_cloudinary_public_id', 'recipe_image', ['cloudinary_public_id'])


def downgrade():
    # Remove index and columns in reverse order
    op.drop_index('idx_recipe_image_cloudinary_public_id', table_name='recipe_image')
    op.drop_column('recipe_image', 'cloudinary_bytes')
    op.drop_column('recipe_image', 'cloudinary_format')
    op.drop_column('recipe_image', 'cloudinary_height')
    op.drop_column('recipe_image', 'cloudinary_width')
    op.drop_column('recipe_image', 'cloudinary_thumbnail_url')
    op.drop_column('recipe_image', 'cloudinary_url')
    op.drop_column('recipe_image', 'cloudinary_public_id')

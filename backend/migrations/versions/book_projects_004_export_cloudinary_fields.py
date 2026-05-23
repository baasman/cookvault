"""Add Cloudinary storage columns to book_project_export.

Lets BookProject PDFs persist across Render deploys (which wipe local disk).
``cloudinary_public_id`` is the canonical handle for delete/replace; the URL
column is kept so the download endpoint can stream the file without an extra
Cloudinary API roundtrip. ``pdf_file_path`` stays for local-dev fallback when
USE_CLOUDINARY is off.

Revision ID: book_projects_004
Revises: book_projects_003
Create Date: 2026-05-19 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "book_projects_004"
down_revision = "book_projects_003"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("book_project_export") as batch_op:
        batch_op.add_column(
            sa.Column("cloudinary_public_id", sa.String(500), nullable=True)
        )
        batch_op.add_column(
            sa.Column("cloudinary_url", sa.String(1000), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("book_project_export") as batch_op:
        batch_op.drop_column("cloudinary_url")
        batch_op.drop_column("cloudinary_public_id")

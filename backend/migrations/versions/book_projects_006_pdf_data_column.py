"""Add pdf_data BYTEA column to book_project_export.

Replaces the Cloudinary + ephemeral-disk dance with direct Postgres storage
for BookProject preview/clean PDFs. The motivation came from production:
Cloudinary's account-level restrictions on raw resource delivery returned
401 even with signed URLs and Basic Auth, and the ~150 KB PDFs are small
enough that storing them inline is cheap. Removes a vendor-specific
delivery dependency from the paid-flow critical path.

Older rows keep their ``pdf_file_path`` / ``cloudinary_*`` values for
inspection; the download endpoint just checks ``pdf_data`` first now, so
those rows surface as 410 "missing" — the user regenerates and the new
row goes through the DB-storage path.

Revision ID: book_projects_006
Revises: book_projects_005
Create Date: 2026-06-04 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "book_projects_006"
down_revision = "book_projects_005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "book_project_export",
        sa.Column("pdf_data", sa.LargeBinary(), nullable=True),
    )


def downgrade():
    op.drop_column("book_project_export", "pdf_data")

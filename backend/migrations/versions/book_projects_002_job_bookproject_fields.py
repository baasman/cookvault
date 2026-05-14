"""Add book_project_id and guest_contributor_id to processing_job.

Lets the existing async image-OCR Celery pipeline create Recipes that are
attributed to a BookProject + GuestContributor instead of a Cookbook + User.
The columns are nullable so existing processing-job rows are unaffected.

Revision ID: book_projects_002
Revises: book_projects_001
Create Date: 2026-05-14 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "book_projects_002"
down_revision = "book_projects_001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    op.add_column(
        "processing_job",
        sa.Column("book_project_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "processing_job",
        sa.Column("guest_contributor_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_processing_job_book_project_id",
        "processing_job",
        ["book_project_id"],
    )
    op.create_index(
        "ix_processing_job_guest_contributor_id",
        "processing_job",
        ["guest_contributor_id"],
    )
    # SQLite can't ALTER TABLE ADD CONSTRAINT for FKs; we keep ORM-level
    # relationships and rely on app-layer integrity in dev. PostgreSQL gets
    # the DB-level constraints.
    if not is_sqlite:
        op.create_foreign_key(
            "fk_processing_job_book_project_id",
            "processing_job",
            "book_project",
            ["book_project_id"],
            ["id"],
        )
        op.create_foreign_key(
            "fk_processing_job_guest_contributor_id",
            "processing_job",
            "guest_contributor",
            ["guest_contributor_id"],
            ["id"],
        )


def downgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if not is_sqlite:
        op.drop_constraint(
            "fk_processing_job_guest_contributor_id",
            "processing_job",
            type_="foreignkey",
        )
        op.drop_constraint(
            "fk_processing_job_book_project_id",
            "processing_job",
            type_="foreignkey",
        )
    op.drop_index(
        "ix_processing_job_guest_contributor_id", table_name="processing_job"
    )
    op.drop_index(
        "ix_processing_job_book_project_id", table_name="processing_job"
    )
    op.drop_column("processing_job", "guest_contributor_id")
    op.drop_column("processing_job", "book_project_id")

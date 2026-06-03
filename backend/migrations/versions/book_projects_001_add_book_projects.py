"""Add BookProject, ProjectShareLink, GuestContributor, BookProjectExport tables
and book_project_id/guest_contributor_id/is_excluded_from_project columns on Recipe.

Foundation for the multi-contributor cookbook project feature (Phase 1).

Revision ID: book_projects_001
Revises: 20fc34701f73
Create Date: 2026-05-14 14:30:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "book_projects_001"
down_revision = "20fc34701f73"
branch_labels = None
depends_on = None


_PROJECT_TYPE_VALUES = (
    "wedding",
    "anniversary",
    "heirloom",
    "memorial",
    "holiday",
    "general",
)
_PROJECT_STATUS_VALUES = ("collecting", "review", "finalized", "exported")


def upgrade():
    op.create_table(
        "book_project",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.Integer(),
            sa.ForeignKey("user.id"),
            nullable=False,
        ),
        sa.Column(
            "project_type",
            sa.Enum(*_PROJECT_TYPE_VALUES, name="projecttype"),
            nullable=False,
            server_default="general",
        ),
        sa.Column(
            "status",
            sa.Enum(*_PROJECT_STATUS_VALUES, name="projectstatus"),
            nullable=False,
            server_default="collecting",
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("subtitle", sa.String(300), nullable=True),
        sa.Column("dedication", sa.Text(), nullable=True),
        sa.Column("honorees", sa.JSON(), nullable=True),
        sa.Column("occasion_date", sa.Date(), nullable=True),
        sa.Column("submission_deadline", sa.Date(), nullable=True),
        sa.Column("cover_image_url", sa.String(500), nullable=True),
        sa.Column("project_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_book_project_owner_user_id", "book_project", ["owner_user_id"])

    op.create_table(
        "project_share_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("book_project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("submission_cap", sa.Integer(), nullable=True),
        sa.Column(
            "submission_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_project_share_link_project_id", "project_share_link", ["project_id"]
    )
    op.create_index(
        "ix_project_share_link_token", "project_share_link", ["token"], unique=True
    )

    op.create_table(
        "guest_contributor",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("book_project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "share_link_id",
            sa.Integer(),
            sa.ForeignKey("project_share_link.id"),
            nullable=True,
        ),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_guest_contributor_project_id", "guest_contributor", ["project_id"]
    )
    op.create_index(
        "ix_guest_contributor_share_link_id",
        "guest_contributor",
        ["share_link_id"],
    )
    op.create_index("ix_guest_contributor_email", "guest_contributor", ["email"])

    op.create_table(
        "book_project_export",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("book_project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("user.id"),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.Integer(),
            sa.ForeignKey("payments.id"),
            nullable=True,
        ),
        sa.Column("pdf_file_path", sa.String(500), nullable=True),
        sa.Column(
            "is_watermarked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_book_project_export_project_id",
        "book_project_export",
        ["project_id"],
    )
    op.create_index(
        "ix_book_project_export_user_id", "book_project_export", ["user_id"]
    )

    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    op.add_column("recipe", sa.Column("book_project_id", sa.Integer(), nullable=True))
    op.add_column(
        "recipe", sa.Column("guest_contributor_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "recipe",
        sa.Column(
            "is_excluded_from_project",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index("ix_recipe_book_project_id", "recipe", ["book_project_id"])
    op.create_index(
        "ix_recipe_guest_contributor_id", "recipe", ["guest_contributor_id"]
    )
    # SQLite doesn't support ALTER TABLE ADD CONSTRAINT for foreign keys; the FK
    # is still enforced at the ORM layer. On PostgreSQL we add the DB-level FK.
    if not is_sqlite:
        op.create_foreign_key(
            "fk_recipe_book_project_id",
            "recipe",
            "book_project",
            ["book_project_id"],
            ["id"],
        )
        op.create_foreign_key(
            "fk_recipe_guest_contributor_id",
            "recipe",
            "guest_contributor",
            ["guest_contributor_id"],
            ["id"],
        )


def downgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if not is_sqlite:
        op.drop_constraint(
            "fk_recipe_guest_contributor_id", "recipe", type_="foreignkey"
        )
        op.drop_constraint("fk_recipe_book_project_id", "recipe", type_="foreignkey")
    op.drop_index("ix_recipe_guest_contributor_id", table_name="recipe")
    op.drop_index("ix_recipe_book_project_id", table_name="recipe")
    op.drop_column("recipe", "is_excluded_from_project")
    op.drop_column("recipe", "guest_contributor_id")
    op.drop_column("recipe", "book_project_id")

    op.drop_index("ix_book_project_export_user_id", table_name="book_project_export")
    op.drop_index("ix_book_project_export_project_id", table_name="book_project_export")
    op.drop_table("book_project_export")

    op.drop_index("ix_guest_contributor_email", table_name="guest_contributor")
    op.drop_index("ix_guest_contributor_share_link_id", table_name="guest_contributor")
    op.drop_index("ix_guest_contributor_project_id", table_name="guest_contributor")
    op.drop_table("guest_contributor")

    op.drop_index("ix_project_share_link_token", table_name="project_share_link")
    op.drop_index("ix_project_share_link_project_id", table_name="project_share_link")
    op.drop_table("project_share_link")

    op.drop_index("ix_book_project_owner_user_id", table_name="book_project")
    op.drop_table("book_project")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS projectstatus")
        op.execute("DROP TYPE IF EXISTS projecttype")

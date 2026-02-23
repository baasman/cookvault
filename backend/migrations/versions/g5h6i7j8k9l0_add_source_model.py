"""add_source_model

Revision ID: g5h6i7j8k9l0
Revises: f4g5h6i7j8k9
Create Date: 2026-02-20 15:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "g5h6i7j8k9l0"
down_revision = "f4g5h6i7j8k9"
branch_labels = None
depends_on = None


def upgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Create source table
    op.create_table(
        "source",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(200), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("favicon_url", sa.String(500), nullable=True),
        sa.Column("recipe_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain", "user_id", name="unique_source_domain_per_user"),
    )
    op.create_index("ix_source_domain", "source", ["domain"], unique=False)
    op.create_index("ix_source_user_id", "source", ["user_id"], unique=False)

    # Add source_id column to recipe table
    if is_sqlite:
        # SQLite: Use batch mode for table alterations
        with op.batch_alter_table("recipe", schema=None) as batch_op:
            batch_op.add_column(sa.Column("source_id", sa.Integer(), nullable=True))
            batch_op.create_index("ix_recipe_source_id", ["source_id"], unique=False)
            batch_op.create_foreign_key(
                "fk_recipe_source_id", "source", ["source_id"], ["id"]
            )
    else:
        # PostgreSQL: Use standard operations
        op.add_column("recipe", sa.Column("source_id", sa.Integer(), nullable=True))
        op.create_index("ix_recipe_source_id", "recipe", ["source_id"], unique=False)
        op.create_foreign_key(
            "fk_recipe_source_id", "recipe", "source", ["source_id"], ["id"]
        )


def downgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Remove source_id column from recipe table
    if is_sqlite:
        with op.batch_alter_table("recipe", schema=None) as batch_op:
            batch_op.drop_constraint("fk_recipe_source_id", type_="foreignkey")
            batch_op.drop_index("ix_recipe_source_id")
            batch_op.drop_column("source_id")
    else:
        op.drop_constraint("fk_recipe_source_id", "recipe", type_="foreignkey")
        op.drop_index("ix_recipe_source_id", table_name="recipe")
        op.drop_column("recipe", "source_id")

    # Drop source table indexes and table
    op.drop_index("ix_source_user_id", table_name="source")
    op.drop_index("ix_source_domain", table_name="source")
    op.drop_table("source")

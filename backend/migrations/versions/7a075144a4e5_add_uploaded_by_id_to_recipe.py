"""add_uploaded_by_id_to_recipe

Revision ID: 7a075144a4e5
Revises: 31bb03084408
Create Date: 2026-01-02 14:03:28.785038

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7a075144a4e5"
down_revision = "31bb03084408"
branch_labels = None
depends_on = None


def upgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: Use batch mode for table alterations
        with op.batch_alter_table("recipe", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("uploaded_by_id", sa.Integer(), nullable=True)
            )
            batch_op.create_index("ix_recipe_uploaded_by_id", ["uploaded_by_id"])
            batch_op.create_foreign_key(
                "fk_recipe_uploaded_by_id", "user", ["uploaded_by_id"], ["id"]
            )
    else:
        # PostgreSQL: Use standard operations
        op.add_column(
            "recipe", sa.Column("uploaded_by_id", sa.Integer(), nullable=True)
        )
        op.create_index("ix_recipe_uploaded_by_id", "recipe", ["uploaded_by_id"])
        op.create_foreign_key(
            "fk_recipe_uploaded_by_id", "recipe", "user", ["uploaded_by_id"], ["id"]
        )

    # Backfill: existing recipes get uploaded_by_id = user_id
    # This assumes that before this change, the uploader was always the user_id
    op.execute(
        "UPDATE recipe SET uploaded_by_id = user_id WHERE uploaded_by_id IS NULL"
    )


def downgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: Use batch mode
        with op.batch_alter_table("recipe", schema=None) as batch_op:
            batch_op.drop_constraint("fk_recipe_uploaded_by_id", type_="foreignkey")
            batch_op.drop_index("ix_recipe_uploaded_by_id")
            batch_op.drop_column("uploaded_by_id")
    else:
        # PostgreSQL: Use standard operations
        op.drop_constraint("fk_recipe_uploaded_by_id", "recipe", type_="foreignkey")
        op.drop_index("ix_recipe_uploaded_by_id", table_name="recipe")
        op.drop_column("recipe", "uploaded_by_id")

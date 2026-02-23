"""add_recipe_ratings

Revision ID: f4g5h6i7j8k9
Revises: e3f4g5h6i7j8
Create Date: 2026-02-20 14:30:00.000000

"""

import re
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4g5h6i7j8k9"
down_revision = "e3f4g5h6i7j8"
branch_labels = None
depends_on = None


def normalize_title(title: str) -> str:
    """Normalize a recipe title for matching."""
    if not title:
        return ""
    normalized = title.lower()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip()
    return normalized


def upgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Create recipe_ratings table
    op.create_table(
        "recipe_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipe.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "recipe_id", name="unique_user_recipe_rating"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="valid_rating_range"),
    )

    # Add normalized_title column to recipe table
    if is_sqlite:
        # SQLite: Use batch mode for table alterations
        with op.batch_alter_table("recipe", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("normalized_title", sa.String(200), nullable=True)
            )
            batch_op.create_index(
                "ix_recipe_normalized_title", ["normalized_title"], unique=False
            )
    else:
        # PostgreSQL: Use standard operations
        op.add_column(
            "recipe", sa.Column("normalized_title", sa.String(200), nullable=True)
        )
        op.create_index(
            "ix_recipe_normalized_title", "recipe", ["normalized_title"], unique=False
        )

    # Backfill normalized_title for existing recipes
    connection = op.get_bind()
    recipes = connection.execute(
        sa.text("SELECT id, title FROM recipe WHERE title IS NOT NULL")
    ).fetchall()

    for recipe_id, title in recipes:
        normalized = normalize_title(title)
        connection.execute(
            sa.text("UPDATE recipe SET normalized_title = :normalized WHERE id = :id"),
            {"normalized": normalized, "id": recipe_id},
        )


def downgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Remove normalized_title column from recipe table
    if is_sqlite:
        with op.batch_alter_table("recipe", schema=None) as batch_op:
            batch_op.drop_index("ix_recipe_normalized_title")
            batch_op.drop_column("normalized_title")
    else:
        op.drop_index("ix_recipe_normalized_title", table_name="recipe")
        op.drop_column("recipe", "normalized_title")

    # Drop recipe_ratings table
    op.drop_table("recipe_ratings")

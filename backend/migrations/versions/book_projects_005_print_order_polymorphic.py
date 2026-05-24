"""Make PrintOrder polymorphic: support BookProject in addition to Cookbook.

Adds nullable ``book_project_id`` alongside the existing ``cookbook_id``
(which becomes nullable). Exactly one of the two must be set on each row —
enforced via a CHECK constraint on PostgreSQL; on SQLite we rely on
app-layer integrity (the helper properties on PrintOrder raise if both or
neither is set) since SQLite's ALTER TABLE doesn't support adding CHECK
constraints in-place.

Existing cookbook-only rows are unaffected: their ``cookbook_id`` stays
non-null and ``book_project_id`` defaults to NULL.

Revision ID: book_projects_005
Revises: book_projects_004
Create Date: 2026-05-19 15:30:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "book_projects_005"
down_revision = "book_projects_004"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    op.add_column(
        "print_orders",
        sa.Column("book_project_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_print_orders_book_project_id",
        "print_orders",
        ["book_project_id"],
    )

    if is_sqlite:
        # SQLite: rebuild the table to relax NOT NULL on cookbook_id.
        with op.batch_alter_table("print_orders") as batch_op:
            batch_op.alter_column(
                "cookbook_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
    else:
        op.alter_column(
            "print_orders",
            "cookbook_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        op.create_foreign_key(
            "fk_print_orders_book_project_id",
            "print_orders",
            "book_project",
            ["book_project_id"],
            ["id"],
        )
        # Exactly one of cookbook_id or book_project_id must be non-null.
        # ``IS NULL`` evaluates to a boolean and != on two booleans is XOR,
        # which is exactly the "exactly one" semantics we want.
        op.create_check_constraint(
            "ck_print_orders_exactly_one_entity",
            "print_orders",
            "(cookbook_id IS NULL) != (book_project_id IS NULL)",
        )


def downgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if not is_sqlite:
        op.drop_constraint(
            "ck_print_orders_exactly_one_entity",
            "print_orders",
            type_="check",
        )
        op.drop_constraint(
            "fk_print_orders_book_project_id",
            "print_orders",
            type_="foreignkey",
        )
        op.alter_column(
            "print_orders",
            "cookbook_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
    else:
        with op.batch_alter_table("print_orders") as batch_op:
            batch_op.alter_column(
                "cookbook_id",
                existing_type=sa.Integer(),
                nullable=False,
            )

    op.drop_index(
        "ix_print_orders_book_project_id", table_name="print_orders"
    )
    op.drop_column("print_orders", "book_project_id")

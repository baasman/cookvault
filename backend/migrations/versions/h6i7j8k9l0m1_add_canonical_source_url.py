"""add_canonical_source_url

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2026-02-20 16:00:00.000000

"""

from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "h6i7j8k9l0m1"
down_revision = "g5h6i7j8k9l0"
branch_labels = None
depends_on = None

# Common tracking parameters to remove from URLs
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "source",
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "_ga",
    "_gl",
    "yclid",
    "twclid",
    "igshid",
}


def normalize_url(url: str):
    """Normalize URL for matching (migration version of the function)."""
    if not url:
        return None

    try:
        parsed = urlparse(url)

        if not parsed.scheme or not parsed.netloc:
            return None

        scheme = parsed.scheme.lower()
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]

        path = parsed.path.rstrip("/") or "/"

        query_params = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMS
        }

        if filtered_params:
            sorted_params = sorted(filtered_params.items())
            query = urlencode(sorted_params, doseq=True)
        else:
            query = ""

        normalized = urlunparse((scheme, host, path, "", query, ""))
        return normalized

    except Exception:
        return None


def upgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Add canonical_source_url column to recipe table
    if is_sqlite:
        # SQLite: Use batch mode for table alterations
        with op.batch_alter_table("recipe", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("canonical_source_url", sa.String(500), nullable=True)
            )
            batch_op.create_index(
                "ix_recipe_canonical_source_url",
                ["canonical_source_url"],
                unique=False,
            )
    else:
        # PostgreSQL: Use standard operations
        op.add_column(
            "recipe", sa.Column("canonical_source_url", sa.String(500), nullable=True)
        )
        op.create_index(
            "ix_recipe_canonical_source_url",
            "recipe",
            ["canonical_source_url"],
            unique=False,
        )

    # Backfill canonical_source_url for existing recipes with source URLs
    connection = op.get_bind()
    recipes = connection.execute(
        sa.text("SELECT id, source FROM recipe WHERE source IS NOT NULL")
    ).fetchall()

    for recipe_id, source in recipes:
        # Only process if source looks like a URL (starts with http)
        if source and (source.startswith("http://") or source.startswith("https://")):
            canonical = normalize_url(source)
            if canonical:
                connection.execute(
                    sa.text(
                        "UPDATE recipe SET canonical_source_url = :canonical WHERE id = :id"
                    ),
                    {"canonical": canonical, "id": recipe_id},
                )


def downgrade():
    # Check if we're running on SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Remove canonical_source_url column from recipe table
    if is_sqlite:
        with op.batch_alter_table("recipe", schema=None) as batch_op:
            batch_op.drop_index("ix_recipe_canonical_source_url")
            batch_op.drop_column("canonical_source_url")
    else:
        op.drop_index("ix_recipe_canonical_source_url", table_name="recipe")
        op.drop_column("recipe", "canonical_source_url")

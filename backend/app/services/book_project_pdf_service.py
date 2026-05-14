"""WeasyPrint-backed PDF generation for BookProject exports.

Renders a BookProject (its included submissions, with contributor attribution)
into a PDF artifact. Two flavors:
- watermarked preview: free for any organizer to download
- clean: gated by a paid BookProjectExport (handled in routes, not here)

The HTML template is in app/services/book_project_templates/<template_name>/
and uses Jinja2 syntax. Templates choose their copy variations by reading
``project.project_type`` — wedding/anniversary/heirloom/etc. share one layout
and differ on cover wording, intro page, and section headers.

Local-dev macOS note: WeasyPrint depends on system libraries (pango, cairo,
glib). On macOS install with ``brew install pango`` (which pulls in cairo/glib).
Apple Silicon may need ``DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`` exported
before launching the dev server, or symlinks in /usr/local/lib. Production
Linux (Render) has these as standard packages.
"""

from __future__ import annotations

import io
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from flask import current_app
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import BookProject, Recipe

logger = logging.getLogger(__name__)

# Template directory relative to this module. Each subdirectory is one named
# template with a template.html (Jinja2) and template.css (print CSS).
_TEMPLATES_ROOT = Path(__file__).parent / "book_project_templates"


def list_available_templates() -> list[str]:
    """Return the names of available template directories."""
    if not _TEMPLATES_ROOT.exists():
        return []
    return [p.name for p in _TEMPLATES_ROOT.iterdir() if p.is_dir()]


def _included_recipes(project: BookProject) -> list[Recipe]:
    """Recipes that should appear in the book (auto-land + organizer-excluded
    filter). Ordered by submission time so the book reflects the natural flow
    of contributions."""
    return [
        r
        for r in sorted(project.recipes, key=lambda r: r.created_at or 0)
        if not r.is_excluded_from_project
    ]


def _build_template_context(
    project: BookProject, watermarked: bool
) -> dict:
    """Assemble the variables passed to the Jinja2 template."""
    included = _included_recipes(project)
    return {
        "project": project,
        "watermarked": watermarked,
        "watermark_text": current_app.config.get(
            "BOOK_PROJECT_WATERMARK_TEXT", "PREVIEW — cookle.food"
        ),
        "recipes": [_recipe_view(r) for r in included],
        "recipe_count": len(included),
        "honorees": project.honorees or [],
        "honorees_joined": _join_names(project.honorees or []),
    }


def _recipe_view(recipe: Recipe) -> dict:
    """Lightweight, template-friendly view of a recipe + its contributor."""
    contributor = recipe.guest_contributor
    return {
        "id": recipe.id,
        "title": recipe.title or "Untitled Recipe",
        "description": recipe.description,
        "prep_time": recipe.prep_time,
        "cook_time": recipe.cook_time,
        "servings": recipe.servings,
        "ingredients": [
            {
                "name": ing.name,
                # Get the association row for this recipe/ingredient.
                "quantity": _ingredient_assoc_field(recipe, ing, "quantity"),
                "unit": _ingredient_assoc_field(recipe, ing, "unit"),
                "preparation": _ingredient_assoc_field(recipe, ing, "preparation"),
            }
            for ing in recipe.ingredients
        ],
        "instructions": [
            {"step_number": ins.step_number, "text": ins.text}
            for ins in recipe.recipe_instructions
        ],
        "contributor_name": contributor.display_name if contributor else None,
    }


def _ingredient_assoc_field(recipe: Recipe, ingredient, field: str):
    """Pull a column from the recipe_ingredients association table for one ing.

    Recipe.ingredients is a many-to-many; the quantity/unit live on the join,
    not on the Ingredient itself. SQLAlchemy lazy-loads them through the
    association proxy but we look them up directly here for template clarity.
    """
    from app import db
    from app.models.recipe import recipe_ingredients

    row = db.session.execute(
        recipe_ingredients.select().where(
            recipe_ingredients.c.recipe_id == recipe.id,
            recipe_ingredients.c.ingredient_id == ingredient.id,
        )
    ).first()
    if not row:
        return None
    return row._mapping.get(field)


def _join_names(names: list[str]) -> str:
    """Render an "&"-joined honoree list, e.g. ['Sarah','Maya'] -> 'Sarah & Maya'."""
    names = [n for n in names if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return f"{', '.join(names[:-1])} & {names[-1]}"


def _output_dir() -> Path:
    """Where generated PDFs are written on disk. Configurable via env so prod
    can point at an attached volume."""
    base = current_app.config.get("BOOK_PROJECT_EXPORT_DIR")
    if base:
        path = Path(base)
    else:
        path = Path(current_app.config.get("UPLOAD_FOLDER", "uploads")) / "book_project_exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_book_project_pdf(
    project: BookProject,
    *,
    watermarked: bool,
    template_name: str = "wedding_basic",
) -> str:
    """Render the project to a PDF on disk and return the file path.

    Raises if the template doesn't exist or if WeasyPrint's system libraries
    are missing on the host — callers should catch and translate to an HTTP
    500 (with logging) so the user gets a coherent error rather than a stack
    trace.
    """
    template_dir = _TEMPLATES_ROOT / template_name
    if not template_dir.is_dir():
        raise FileNotFoundError(
            f"Book project template not found: {template_name}"
        )

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("template.html")
    context = _build_template_context(project, watermarked=watermarked)
    html_str = template.render(**context)

    css_path = template_dir / "template.css"
    css_str: Optional[str] = None
    if css_path.exists():
        css_str = css_path.read_text(encoding="utf-8")

    out_path = _output_dir() / f"project-{project.id}-{uuid.uuid4().hex}.pdf"

    # Imported here so module import works on hosts where WeasyPrint's system
    # deps aren't installed — only PDF generation itself fails, the rest of
    # the app (and tests that don't touch this path) still runs.
    from weasyprint import CSS, HTML

    html_doc = HTML(string=html_str, base_url=str(template_dir))
    stylesheets = [CSS(string=css_str)] if css_str else None
    html_doc.write_pdf(target=str(out_path), stylesheets=stylesheets)

    logger.info(
        "Rendered BookProject PDF: project=%s template=%s watermarked=%s out=%s",
        project.id,
        template_name,
        watermarked,
        out_path,
    )

    return str(out_path)


def render_book_project_pdf_to_bytes(
    project: BookProject,
    *,
    watermarked: bool,
    template_name: str = "wedding_basic",
) -> bytes:
    """Like ``render_book_project_pdf`` but returns bytes instead of writing
    to disk. Useful when the caller wants to stream the PDF directly in an
    HTTP response without touching the filesystem."""
    template_dir = _TEMPLATES_ROOT / template_name
    if not template_dir.is_dir():
        raise FileNotFoundError(
            f"Book project template not found: {template_name}"
        )

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("template.html")
    context = _build_template_context(project, watermarked=watermarked)
    html_str = template.render(**context)

    css_path = template_dir / "template.css"
    css_str: Optional[str] = None
    if css_path.exists():
        css_str = css_path.read_text(encoding="utf-8")

    from weasyprint import CSS, HTML

    html_doc = HTML(string=html_str, base_url=str(template_dir))
    stylesheets = [CSS(string=css_str)] if css_str else None

    buf = io.BytesIO()
    html_doc.write_pdf(target=buf, stylesheets=stylesheets)
    return buf.getvalue()

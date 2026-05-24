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

import ctypes
import io
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Optional, TypedDict

from flask import current_app
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import BookProject, Recipe
from app.models.print_order import TrimSize
from app.services.cloudinary_service import cloudinary_service


# Physical dimensions for each Lulu trim size. Used to emit a runtime
# @page { size: WxH mm } stylesheet so a single print.css works across
# every supported trim. Sourced from Lulu's POD trim chart.
_TRIM_SIZE_MM: dict[TrimSize, tuple[float, float]] = {
    TrimSize.US_LETTER: (215.9, 279.4),
    TrimSize.US_TRADE: (152.4, 228.6),
    TrimSize.DIGEST: (139.7, 215.9),
    TrimSize.SQUARE_8: (203.2, 203.2),
    TrimSize.LANDSCAPE_9x7: (228.6, 177.8),
    TrimSize.A4: (210.0, 297.0),
    TrimSize.A5: (148.0, 210.0),
}


def _page_size_css(trim_size: TrimSize) -> str:
    """Return a CSS snippet that sets @page size to the given trim. Designed
    to be passed to WeasyPrint as an additional stylesheet, applied last so
    it overrides any size declared in template.css or print.css."""
    width_mm, height_mm = _TRIM_SIZE_MM[trim_size]
    return f"@page {{ size: {width_mm}mm {height_mm}mm; }}"


class RenderedPdf(TypedDict):
    """Where the rendered PDF lives. Exactly one of cloudinary_url or
    pdf_file_path is populated; the other is None. Callers persist all three
    fields onto the BookProjectExport row and the download endpoint picks
    whichever storage backend is set."""

    cloudinary_public_id: Optional[str]
    cloudinary_url: Optional[str]
    pdf_file_path: Optional[str]

logger = logging.getLogger(__name__)


# WeasyPrint depends on pango / cairo / glib / harfbuzz / fontconfig system
# libraries. On macOS the dylibs Homebrew installs are named with version
# suffixes (libgobject-2.0.0.dylib) that ``ctypes.util.find_library`` can't
# resolve from the bare names WeasyPrint searches for ("libgobject-2.0-0").
# DYLD_FALLBACK_LIBRARY_PATH is the canonical fix, but macOS SIP strips
# DYLD_* env vars when spawning child processes through /bin/sh — so even
# setting it in the Makefile doesn't reliably reach the Flask + Celery
# workers. We load the dylibs explicitly by absolute path here so they
# show up in the process's loaded-libraries table BEFORE WeasyPrint's
# cffi import runs. On Linux (where everything lives on the standard
# loader path) this is a no-op.
_MACOS_HOMEBREW_LIB = "/opt/homebrew/lib"
_MACOS_DYLIB_NAMES = (
    "libgobject-2.0.0.dylib",
    "libpango-1.0.0.dylib",
    "libpangoft2-1.0.0.dylib",
    "libharfbuzz.0.dylib",
    "libfontconfig.1.dylib",
    "libcairo.2.dylib",
)
_dylib_preload_attempted = False


def _preload_weasyprint_dylibs() -> None:
    """Best-effort: make the Homebrew-installed WeasyPrint native deps
    discoverable by ``ctypes.util.find_library`` (which is what cffi uses).
    macOS reads ``DYLD_FALLBACK_LIBRARY_PATH`` at lookup time for that
    function, so injecting it into ``os.environ`` here (before WeasyPrint
    is imported) is enough — we don't have to rely on the env var
    surviving the shell → make → honcho → Python process chain, which
    macOS SIP can strip along the way.

    Also dlopens each lib explicitly so dyld caches it for the rest of the
    process. On Linux (and on macOS hosts without Homebrew at
    /opt/homebrew) this is a no-op.
    """
    global _dylib_preload_attempted
    if _dylib_preload_attempted:
        return
    _dylib_preload_attempted = True

    if sys.platform != "darwin":
        return
    if not os.path.isdir(_MACOS_HOMEBREW_LIB):
        return

    # Prepend Homebrew's lib dir so find_library() picks it up. Keep any
    # existing value so user-set paths still win.
    existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    parts = [p for p in existing.split(":") if p]
    if _MACOS_HOMEBREW_LIB not in parts:
        parts.insert(0, _MACOS_HOMEBREW_LIB)
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(parts)

    for name in _MACOS_DYLIB_NAMES:
        path = os.path.join(_MACOS_HOMEBREW_LIB, name)
        if not os.path.exists(path):
            continue
        try:
            ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
        except OSError as e:
            logger.warning(
                "Could not pre-load WeasyPrint dylib %s: %s", path, e
            )

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


def build_cover_metadata(project: BookProject) -> dict:
    """Build the cookbook_data-shaped dict that CoverGenerationService expects
    from a BookProject. Cover service is data-agnostic (takes a plain dict),
    so this adapter is the only Cookbook→BookProject bridge needed for cover
    rendering.

    Mapping:
      title       <- project.title
      subtitle    <- project.subtitle or a project-type-aware default
      author      <- honorees joined ("Sarah & Maya") for keepsake-style
                     projects; for general/heirloom we leave it blank rather
                     than guess
      description <- project.dedication (used on back cover)
      recipes     <- the included recipes (used by cover service for page
                     count estimation if it does any)
    """
    included = _included_recipes(project)
    honorees = project.honorees or []
    subtitle = project.subtitle or _default_subtitle(project)
    author = _join_names(honorees) if honorees else ""
    return {
        "title": project.title,
        "subtitle": subtitle,
        "author": author,
        "description": project.dedication or "",
        "recipes": [{"id": r.id, "title": r.title} for r in included],
    }


def _default_subtitle(project: BookProject) -> str:
    """Project-type-aware subtitle fallback when the organizer didn't set one.
    Kept short — covers have limited real estate."""
    # Lazy import to avoid cycles at module load.
    from app.models.book_project import ProjectType

    defaults = {
        ProjectType.WEDDING: "A gift from your guests",
        ProjectType.ANNIVERSARY: "A celebration in recipes",
        ProjectType.HEIRLOOM: "Family recipes, collected",
        ProjectType.MEMORIAL: "Recipes in remembrance",
        ProjectType.HOLIDAY: "A holiday recipe collection",
        ProjectType.GENERAL: "",
    }
    return defaults.get(project.project_type, "")


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
) -> RenderedPdf:
    """Render the project to a PDF and return where it was stored.

    When Cloudinary is enabled (USE_CLOUDINARY=true + creds configured) the
    PDF is rendered to bytes and uploaded as a raw resource — surviving
    Render's ephemeral disk between deploys. Otherwise the PDF is written to
    the local upload directory for dev/local use.

    Raises if the template doesn't exist or if WeasyPrint's system libraries
    are missing on the host — callers should catch and translate to an HTTP
    500 (with logging) so the user gets a coherent error rather than a stack
    trace.
    """
    if cloudinary_service.is_enabled():
        pdf_bytes = render_book_project_pdf_to_bytes(
            project, watermarked=watermarked, template_name=template_name
        )
        filename = (
            f"project-{project.id}"
            f"{'-preview' if watermarked else '-clean'}-{uuid.uuid4().hex}.pdf"
        )
        upload = cloudinary_service.upload_pdf(
            pdf_bytes,
            filename=filename,
            folder="book_project_exports",
        )
        logger.info(
            "Rendered BookProject PDF to Cloudinary: project=%s template=%s "
            "watermarked=%s public_id=%s bytes=%s",
            project.id,
            template_name,
            watermarked,
            upload["public_id"],
            upload["bytes"],
        )
        return {
            "cloudinary_public_id": upload["public_id"],
            "cloudinary_url": upload["url"],
            "pdf_file_path": None,
        }

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
    _preload_weasyprint_dylibs()
    from weasyprint import CSS, HTML

    html_doc = HTML(string=html_str, base_url=str(template_dir))
    stylesheets = [CSS(string=css_str)] if css_str else None
    html_doc.write_pdf(target=str(out_path), stylesheets=stylesheets)

    logger.info(
        "Rendered BookProject PDF to disk: project=%s template=%s watermarked=%s out=%s",
        project.id,
        template_name,
        watermarked,
        out_path,
    )

    return {
        "cloudinary_public_id": None,
        "cloudinary_url": None,
        "pdf_file_path": str(out_path),
    }


def render_book_project_pdf_to_bytes(
    project: BookProject,
    *,
    watermarked: bool,
    template_name: str = "wedding_basic",
    print_ready: bool = False,
    trim_size: Optional[TrimSize] = None,
) -> bytes:
    """Like ``render_book_project_pdf`` but returns bytes instead of writing
    to disk. Useful when the caller wants to stream the PDF directly in an
    HTTP response without touching the filesystem.

    When ``print_ready=True``, additionally applies print.css (bleed + crop
    marks + page-number suppression) and an inline @page size derived from
    ``trim_size``. The combination produces a PDF that Lulu's interior
    validator accepts. ``trim_size`` is required when print_ready=True.
    """
    if print_ready and trim_size is None:
        raise ValueError("trim_size is required when print_ready=True")

    template_dir = _TEMPLATES_ROOT / template_name
    if not template_dir.is_dir():
        raise FileNotFoundError(
            f"Book project template not found: {template_name}"
        )

    _preload_weasyprint_dylibs()
    from weasyprint import CSS, HTML

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("template.html")
    context = _build_template_context(project, watermarked=watermarked)
    html_str = template.render(**context)

    stylesheets: list = []
    css_path = template_dir / "template.css"
    if css_path.exists():
        stylesheets.append(CSS(string=css_path.read_text(encoding="utf-8")))
    if print_ready:
        print_css_path = template_dir / "print.css"
        if print_css_path.exists():
            stylesheets.append(
                CSS(string=print_css_path.read_text(encoding="utf-8"))
            )
        # Trim-size override last so it wins.
        stylesheets.append(CSS(string=_page_size_css(trim_size)))

    html_doc = HTML(string=html_str, base_url=str(template_dir))

    buf = io.BytesIO()
    html_doc.write_pdf(target=buf, stylesheets=stylesheets or None)
    return buf.getvalue()

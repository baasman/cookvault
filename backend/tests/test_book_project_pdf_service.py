"""Tests for the WeasyPrint-based BookProject PDF service.

Real PDF rendering is gated by ``weasyprint_available``: WeasyPrint depends on
system libraries (pango, cairo, glib) that aren't always installed in local dev
on macOS. When those aren't loadable, we still verify the template + context
plumbing through unit-level tests and skip the bytes-out smoke test.
"""

from datetime import date

import pytest

from app import db
from app.models import (
    BookProject,
    GuestContributor,
    Instruction,
    Ingredient,
    ProjectType,
    Recipe,
)
from app.models.recipe import recipe_ingredients
from app.services.book_project_pdf_service import (
    _join_names,
    list_available_templates,
)


@pytest.fixture
def populated_project_id(app, test_user):
    """Create a BookProject with two submitted recipes, one excluded. Returns
    the project ID — tests re-fetch via the active session to avoid
    DetachedInstanceError when the fixture's context closes."""
    with app.app_context():
        project = BookProject(
            owner_user_id=test_user.id,
            title="Sarah & Maya's Recipe Book",
            subtitle="A gift from your guests",
            project_type=ProjectType.WEDDING,
            dedication="May your kitchen always smell of garlic.",
            honorees=["Sarah", "Maya"],
            occasion_date=date(2026, 8, 15),
        )
        db.session.add(project)
        db.session.flush()

        linda = GuestContributor(
            project_id=project.id, display_name="Aunt Linda"
        )
        db.session.add(linda)
        db.session.flush()

        flour = Ingredient(name="flour")
        sugar = Ingredient(name="sugar")
        db.session.add_all([flour, sugar])
        db.session.flush()

        included_recipe = Recipe(
            title="Linda's Apple Pie",
            description="Old family recipe.",
            user_id=test_user.id,
            uploaded_by_id=None,
            book_project_id=project.id,
            guest_contributor_id=linda.id,
            is_public=False,
            prep_time=30,
            cook_time=45,
            servings=8,
        )
        excluded_recipe = Recipe(
            title="Test Recipe Excluded",
            user_id=test_user.id,
            book_project_id=project.id,
            is_excluded_from_project=True,
            is_public=False,
        )
        db.session.add_all([included_recipe, excluded_recipe])
        db.session.flush()

        # Attach ingredients with quantities via the join table.
        db.session.execute(
            recipe_ingredients.insert().values(
                recipe_id=included_recipe.id,
                ingredient_id=flour.id,
                quantity=2.0,
                unit="cup",
                order=1,
            )
        )
        db.session.execute(
            recipe_ingredients.insert().values(
                recipe_id=included_recipe.id,
                ingredient_id=sugar.id,
                quantity=0.75,
                unit="cup",
                order=2,
            )
        )

        db.session.add_all(
            [
                Instruction(
                    recipe_id=included_recipe.id,
                    step_number=1,
                    text="Mix flour and sugar.",
                ),
                Instruction(
                    recipe_id=included_recipe.id,
                    step_number=2,
                    text="Bake for 45 minutes.",
                ),
            ]
        )

        db.session.commit()
        return project.id


class TestTemplateRegistry:
    def test_lists_wedding_basic(self):
        templates = list_available_templates()
        assert "wedding_basic" in templates


class TestJoinNames:
    @pytest.mark.parametrize(
        "names,expected",
        [
            ([], ""),
            (["Sarah"], "Sarah"),
            (["Sarah", "Maya"], "Sarah & Maya"),
            (["A", "B", "C"], "A, B & C"),
            (["", "Maya"], "Maya"),
        ],
    )
    def test_join(self, names, expected):
        assert _join_names(names) == expected


def _weasyprint_available() -> bool:
    """Probe WeasyPrint's runtime dependencies. Returns False if the system
    libraries can't be loaded (common on macOS in local dev without env vars)."""
    try:
        from weasyprint import HTML  # noqa: F401

        HTML(string="<p>probe</p>").render()
        return True
    except Exception:
        return False


@pytest.mark.skipif(
    not _weasyprint_available(),
    reason="WeasyPrint system libs (pango/cairo/glib) not available on this host",
)
class TestRenderPdfBytes:
    def test_render_clean_pdf_bytes(self, app, populated_project_id):
        from app.services.book_project_pdf_service import (
            render_book_project_pdf_to_bytes,
        )

        with app.app_context():
            project = db.session.get(BookProject, populated_project_id)
            pdf_bytes = render_book_project_pdf_to_bytes(
                project, watermarked=False
            )
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 1000

    def test_render_watermarked_pdf_bytes(self, app, populated_project_id):
        from app.services.book_project_pdf_service import (
            render_book_project_pdf_to_bytes,
        )

        with app.app_context():
            project = db.session.get(BookProject, populated_project_id)
            pdf_bytes = render_book_project_pdf_to_bytes(
                project, watermarked=True
            )
            assert pdf_bytes.startswith(b"%PDF-")
            clean = render_book_project_pdf_to_bytes(
                project, watermarked=False
            )
            assert len(pdf_bytes) > 1000
            assert len(clean) > 1000

    def test_render_missing_template_raises(self, app, populated_project_id):
        from app.services.book_project_pdf_service import (
            render_book_project_pdf_to_bytes,
        )

        with app.app_context():
            project = db.session.get(BookProject, populated_project_id)
            with pytest.raises(FileNotFoundError):
                render_book_project_pdf_to_bytes(
                    project,
                    watermarked=False,
                    template_name="does_not_exist",
                )


class TestTemplateRenderingNoWeasyPrint:
    """Verify the Jinja2 template renders to valid-looking HTML without
    needing WeasyPrint's system libs. Exercises the wedding-specific copy
    branch, recipe inclusion/exclusion, and contributor attribution."""

    def test_html_rendering_includes_expected_content(self, app, populated_project_id):
        from pathlib import Path

        from jinja2 import Environment, FileSystemLoader, select_autoescape

        from app.services.book_project_pdf_service import _build_template_context

        template_dir = (
            Path(__file__).resolve().parent.parent
            / "app"
            / "services"
            / "book_project_templates"
            / "wedding_basic"
        )
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("template.html")
        with app.app_context():
            project = db.session.get(BookProject, populated_project_id)
            context = _build_template_context(project, watermarked=True)
            html = template.render(**context)

        # Wedding-type cover copy.
        assert "A gift from your guests" in html
        assert "Sarah &amp; Maya" in html or "Sarah & Maya" in html

        # Included recipe is rendered; excluded recipe is NOT.
        # Jinja2's HTML autoescape converts ' to &#39;.
        assert "Apple Pie" in html
        assert "Test Recipe Excluded" not in html

        # Contributor attribution.
        assert "Aunt Linda" in html

        # Ingredients with quantities show up.
        assert "flour" in html
        assert "sugar" in html

        # Watermark text present when watermarked=True.
        assert "PREVIEW" in html

    def test_html_rendering_no_watermark_when_clean(self, app, populated_project_id):
        from pathlib import Path

        from jinja2 import Environment, FileSystemLoader, select_autoescape

        from app.services.book_project_pdf_service import _build_template_context

        template_dir = (
            Path(__file__).resolve().parent.parent
            / "app"
            / "services"
            / "book_project_templates"
            / "wedding_basic"
        )
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("template.html")
        with app.app_context():
            project = db.session.get(BookProject, populated_project_id)
            context = _build_template_context(project, watermarked=False)
            html = template.render(**context)

        assert "PREVIEW" not in html
        assert "watermark" not in html.lower() or "class=\"watermark\"" not in html

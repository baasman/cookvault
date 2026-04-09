"""
Tests for generating actual print-ready PDFs.
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from app.models.print_order import TrimSize
from app.services.print_pdf_builder import PrintReadyPDFBuilder
from app.services.cover_generation_service import CoverGenerationService
from app.services.pdf_service import PDFConfig


def test_interior_pdf_generation():
    """Test generating print-ready interior PDF."""
    config = PDFConfig()
    config.enable_print_ready_mode("US_TRADE", include_marks=True)
    config.gutter_adjustment = True

    builder = PrintReadyPDFBuilder(config)

    cookbook_data = {
        "title": "Test Print Cookbook",
        "author": "Test Author",
        "description": "A test cookbook for print-ready PDF generation.",
    }

    recipes_data = [
        {
            "title": "Test Recipe 1",
            "description": "A delicious test recipe",
            "prep_time_minutes": 15,
            "cook_time_minutes": 30,
            "servings": 4,
            "ingredients": [
                {"quantity": "2", "unit": "cups", "ingredient": "flour"},
                {"quantity": "1", "unit": "cup", "ingredient": "sugar"},
                {"quantity": "3", "unit": "", "ingredient": "eggs"},
            ],
            "instructions": [
                {"instruction": "Mix flour and sugar in a large bowl."},
                {"instruction": "Add eggs one at a time, mixing well."},
                {"instruction": "Bake at 350°F for 30 minutes."},
            ],
        },
        {
            "title": "Test Recipe 2",
            "description": "Another test recipe",
            "prep_time_minutes": 10,
            "cook_time_minutes": 20,
            "servings": 2,
            "ingredients": [
                {"quantity": "1", "unit": "lb", "ingredient": "pasta"},
                {"quantity": "2", "unit": "tbsp", "ingredient": "olive oil"},
            ],
            "instructions": [
                {"instruction": "Boil water in a large pot."},
                {"instruction": "Add pasta and cook according to package directions."},
                {"instruction": "Drain and toss with olive oil."},
            ],
        },
    ]

    pdf_bytes = builder.build_cookbook_pdf(cookbook_data, recipes_data)
    assert len(pdf_bytes) > 0, "Interior PDF should not be empty"

    specs = builder.get_print_specifications()
    assert "trim_size" in specs
    assert "dimensions" in specs


def test_cover_pdf_generation():
    """Test generating print-ready cover PDF."""
    service = CoverGenerationService()

    cookbook_data = {
        "title": "Test Print Cookbook",
        "author": "Test Author",
        "description": "A comprehensive test cookbook for validating print-ready PDF generation capabilities.",
        "recipes": [{"title": f"Recipe {i}"} for i in range(1, 11)],
    }

    pdf_bytes = service.generate_cover_pdf(
        cookbook_data=cookbook_data,
        trim_size=TrimSize.US_TRADE,
        page_count=30,
        template_name="minimalist",
        binding_type="perfect_bound",
    )

    assert len(pdf_bytes) > 0, "Cover PDF should not be empty"

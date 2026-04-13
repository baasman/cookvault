"""
Tests for print-ready PDF generation components.
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from app.models.print_order import TrimSize
from app.utils.trim_sizes import TrimSizeMapper
from app.services.cover_generation_service import CoverGenerationService
from app.services.pdf_service import PDFConfig


def test_trim_size_mapping():
    """Test the trim size mapping functionality."""
    trim_size = TrimSize.US_TRADE
    dimensions = TrimSizeMapper.get_dimensions(trim_size)

    assert dimensions.trim_width > 0
    assert dimensions.trim_height > 0
    assert dimensions.full_width > dimensions.trim_width
    assert dimensions.full_height > dimensions.trim_height
    assert dimensions.safe_width < dimensions.trim_width
    assert dimensions.safe_height < dimensions.trim_height
    assert dimensions.bleed_margin > 0
    assert dimensions.safety_margin > 0


def test_cover_generation():
    """Test the cover generation service."""
    service = CoverGenerationService()

    templates = service.get_available_templates()
    assert len(templates) > 0, "Should have at least one template"

    cookbook_data = {
        "title": "Test Cookbook",
        "author": "Test Author",
        "description": "A sample cookbook for testing purposes. This description is long enough to test the validation logic.",
        "recipes": [{"title": "Recipe 1"}, {"title": "Recipe 2"}],
    }

    validation = service.validate_cover_content(cookbook_data, TrimSize.US_TRADE)
    assert validation["is_valid"]

    page_count = service.estimate_page_count(2)
    assert page_count > 0


def test_pdf_config():
    """Test the enhanced PDFConfig."""
    config = PDFConfig()
    config.enable_print_ready_mode("US_TRADE", include_marks=True)

    assert config.print_ready is True
    assert config.crop_marks is True
    assert config.registration_marks is True
    assert config.bleed_margin > 0
    assert config.safety_margin > 0

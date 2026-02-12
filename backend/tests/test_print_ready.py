#!/usr/bin/env python3
"""
Test script for print-ready PDF generation components.
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.abspath("."))

from app.models.print_order import TrimSize
from app.utils.trim_sizes import TrimSizeMapper
from app.services.cover_generation_service import CoverGenerationService
from app.services.pdf_service import PDFConfig


def test_trim_size_mapping():
    """Test the trim size mapping functionality."""
    print("Testing TrimSizeMapper...")

    # Test getting dimensions for US_TRADE size
    try:
        trim_size = TrimSize.US_TRADE
        dimensions = TrimSizeMapper.get_dimensions(trim_size)

        print(f"✓ Trim size: {trim_size.value}")
        print(
            f'  Trim dimensions: {dimensions.trim_width / 72:.2f}" x {dimensions.trim_height / 72:.2f}"'
        )
        print(
            f'  Full dimensions: {dimensions.full_width / 72:.2f}" x {dimensions.full_height / 72:.2f}"'
        )
        print(
            f'  Safe dimensions: {dimensions.safe_width / 72:.2f}" x {dimensions.safe_height / 72:.2f}"'
        )
        print(f'  Bleed margin: {dimensions.bleed_margin / 72:.3f}"')
        print(f'  Safety margin: {dimensions.safety_margin / 72:.3f}"')

    except Exception as e:
        print(f"✗ Error testing trim size mapping: {e}")
        return False

    return True


def test_cover_generation():
    """Test the cover generation service."""
    print("\nTesting CoverGenerationService...")

    try:
        service = CoverGenerationService()

        # Test getting available templates
        templates = service.get_available_templates()
        print(f"✓ Available templates: {list(templates.keys())}")

        # Test cover validation
        cookbook_data = {
            "title": "Test Cookbook",
            "author": "Test Author",
            "description": "A sample cookbook for testing purposes. This description is long enough to test the validation logic.",
            "recipes": [{"title": "Recipe 1"}, {"title": "Recipe 2"}],
        }

        validation = service.validate_cover_content(cookbook_data, TrimSize.US_TRADE)
        print(f"✓ Cover validation: {validation}")

        # Test page count estimation
        page_count = service.estimate_page_count(2)
        print(f"✓ Estimated page count for 2 recipes: {page_count}")

    except Exception as e:
        print(f"✗ Error testing cover generation: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_pdf_config():
    """Test the enhanced PDFConfig."""
    print("\nTesting enhanced PDFConfig...")

    try:
        config = PDFConfig()

        # Test enabling print-ready mode
        config.enable_print_ready_mode("US_TRADE", include_marks=True)

        print("✓ Print-ready mode enabled")
        print(f"  Print ready: {config.print_ready}")
        print(f"  Trim size: {config.trim_size}")
        print(f"  Crop marks: {config.crop_marks}")
        print(f"  Registration marks: {config.registration_marks}")
        print(f'  Bleed margin: {config.bleed_margin / 72:.3f}"')
        print(f'  Safety margin: {config.safety_margin / 72:.3f}"')

    except Exception as e:
        print(f"✗ Error testing PDF config: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def main():
    """Run all tests."""
    print("=== Print-Ready PDF Generation Tests ===")

    all_passed = True

    if not test_trim_size_mapping():
        all_passed = False

    if not test_cover_generation():
        all_passed = False

    if not test_pdf_config():
        all_passed = False

    print("\n=== Test Results ===")
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

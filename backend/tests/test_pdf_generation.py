#!/usr/bin/env python3
"""
Test script for generating actual print-ready PDFs.
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.abspath("."))

from app.models.print_order import TrimSize
from app.services.print_pdf_builder import PrintReadyPDFBuilder
from app.services.cover_generation_service import CoverGenerationService
from app.services.pdf_service import PDFConfig


def test_interior_pdf_generation():
    """Test generating print-ready interior PDF."""
    print("Testing print-ready interior PDF generation...")

    try:
        # Create print-ready configuration
        config = PDFConfig()
        config.enable_print_ready_mode("US_TRADE", include_marks=True)
        config.gutter_adjustment = True

        # Create PDF builder
        builder = PrintReadyPDFBuilder(config)

        # Sample cookbook data
        cookbook_data = {
            "title": "Test Print Cookbook",
            "author": "Test Author",
            "description": "A test cookbook for print-ready PDF generation.",
        }

        # Sample recipes
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
                    {
                        "instruction": "Add pasta and cook according to package directions."
                    },
                    {"instruction": "Drain and toss with olive oil."},
                ],
            },
        ]

        # Generate PDF
        pdf_bytes = builder.build_cookbook_pdf(cookbook_data, recipes_data)

        print(f"✓ Generated interior PDF: {len(pdf_bytes)} bytes")

        # Save to file for inspection
        with open("test_interior.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("✓ Saved as test_interior.pdf")

        # Get print specifications
        specs = builder.get_print_specifications()
        print("✓ Print specifications:")
        for key, value in specs.items():
            print(f"  {key}: {value}")

    except Exception as e:
        print(f"✗ Error generating interior PDF: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_cover_pdf_generation():
    """Test generating print-ready cover PDF."""
    print("\nTesting print-ready cover PDF generation...")

    try:
        service = CoverGenerationService()

        # Sample cookbook data
        cookbook_data = {
            "title": "Test Print Cookbook",
            "author": "Test Author",
            "description": "A comprehensive test cookbook for validating print-ready PDF generation capabilities. This description provides enough content to test the back cover layout and text wrapping functionality.",
            "recipes": [{"title": f"Recipe {i}"} for i in range(1, 11)],  # 10 recipes
        }

        # Generate cover PDF
        pdf_bytes = service.generate_cover_pdf(
            cookbook_data=cookbook_data,
            trim_size=TrimSize.US_TRADE,
            page_count=30,  # Estimated page count
            template_name="minimalist",
            binding_type="perfect_bound",
        )

        print(f"✓ Generated cover PDF: {len(pdf_bytes)} bytes")

        # Save to file for inspection
        with open("test_cover.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("✓ Saved as test_cover.pdf")

    except Exception as e:
        print(f"✗ Error generating cover PDF: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def main():
    """Run all PDF generation tests."""
    print("=== Print-Ready PDF Generation Tests ===")

    all_passed = True

    if not test_interior_pdf_generation():
        all_passed = False

    if not test_cover_pdf_generation():
        all_passed = False

    print("\n=== Test Results ===")
    if all_passed:
        print("✓ All PDF generation tests passed!")
        print("\nGenerated files:")
        print("  - test_interior.pdf (Print-ready interior with crop marks)")
        print("  - test_cover.pdf (Print-ready cover with spine)")
        return 0
    else:
        print("✗ Some PDF generation tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

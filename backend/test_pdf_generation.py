#!/usr/bin/env python3
"""Test script for PDF generation functionality"""

from app import create_app
from app.services.pdf_service import PDFService, PDFConfig, PageSize, PDFTemplate

def test_pdf_generation():
    """Test basic PDF generation"""

    # Create app context
    app = create_app('development')

    with app.app_context():
        # Create sample recipe data
        recipe = {
            'title': 'Classic Chocolate Chip Cookies',
            'description': 'Delicious homemade chocolate chip cookies that are crispy on the outside and chewy on the inside.',
            'prep_time': 15,
            'cook_time': 12,
            'servings': 24,
            'difficulty': 'easy',
            'ingredients': [
                {'quantity': 2.25, 'unit': 'cups', 'name': 'all-purpose flour'},
                {'quantity': 1, 'unit': 'tsp', 'name': 'baking soda'},
                {'quantity': 1, 'unit': 'tsp', 'name': 'salt'},
                {'quantity': 1, 'unit': 'cup', 'name': 'butter, softened'},
                {'quantity': 0.75, 'unit': 'cup', 'name': 'granulated sugar'},
                {'quantity': 0.75, 'unit': 'cup', 'name': 'packed brown sugar'},
                {'quantity': 2, 'unit': 'large', 'name': 'eggs'},
                {'quantity': 1, 'unit': 'tsp', 'name': 'vanilla extract'},
                {'quantity': 2, 'unit': 'cups', 'name': 'chocolate chips'},
            ],
            'instructions': [
                'Preheat oven to 375°F (190°C).',
                'In a medium bowl, whisk together flour, baking soda, and salt. Set aside.',
                'In a large bowl, cream together butter and both sugars until light and fluffy.',
                'Beat in eggs one at a time, then stir in vanilla.',
                'Gradually blend in the dry ingredients.',
                'Fold in chocolate chips.',
                'Drop rounded tablespoons of dough onto ungreased cookie sheets.',
                'Bake for 9 to 11 minutes or until golden brown.',
                'Cool on baking sheet for 2 minutes; remove to wire rack.',
            ],
            'notes': 'For chewier cookies, slightly underbake them. Store in an airtight container for up to 1 week.',
            'images': []
        }

        # Create PDF service
        config = PDFConfig(
            page_size=PageSize.LETTER,
            template=PDFTemplate.CLASSIC,
            include_images=True,
            include_notes=True
        )

        pdf_service = PDFService(config)

        # Test single recipe PDF
        print("Testing single recipe PDF generation...")
        try:
            pdf_bytes = pdf_service.generate_recipe_pdf(recipe, config)

            # Save to file
            with open('test_recipe.pdf', 'wb') as f:
                f.write(pdf_bytes)

            print(f"✅ Successfully generated recipe PDF ({len(pdf_bytes)} bytes)")
            print("   Saved as: test_recipe.pdf")
        except Exception as e:
            print(f"❌ Failed to generate recipe PDF: {e}")
            import traceback
            traceback.print_exc()

        # Test cookbook PDF
        print("\nTesting cookbook PDF generation...")
        cookbook = {
            'title': 'My Test Cookbook',
            'author': 'Test Author',
            'description': 'A collection of delicious recipes for testing PDF generation.',
            'publication_date': '2025',
            'publisher': 'Test Publisher'
        }

        recipes = [recipe, recipe]  # Add the same recipe twice for testing

        try:
            pdf_bytes = pdf_service.generate_cookbook_pdf(cookbook, recipes, config)

            # Save to file
            with open('test_cookbook.pdf', 'wb') as f:
                f.write(pdf_bytes)

            print(f"✅ Successfully generated cookbook PDF ({len(pdf_bytes)} bytes)")
            print("   Saved as: test_cookbook.pdf")
        except Exception as e:
            print(f"❌ Failed to generate cookbook PDF: {e}")
            import traceback
            traceback.print_exc()

        print("\n✨ PDF generation test complete!")

if __name__ == '__main__':
    test_pdf_generation()
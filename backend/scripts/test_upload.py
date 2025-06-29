#!/usr/bin/env python3
"""
Test script to upload a recipe image using the Flask debug instance.
This script demonstrates how to use the Flask test client to upload files.
"""

import io
import json
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import Recipe, RecipeImage, ProcessingJob, Cookbook, Instruction, Tag


def create_sample_image_data() -> bytes:
    """Load the example image from the data folder."""
    image_path = Path(__file__).parent.parent / "tests" / "data" / "ex-image.png"
    if not image_path.exists():
        # Fallback to minimal PNG if file doesn't exist
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00"
            b"\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return png_data

    with open(image_path, "rb") as f:
        return f.read()


def test_upload_recipe():
    """Test uploading a recipe image and processing it."""
    print("Creating Flask app...")
    app = create_app("testing")
    with app.app_context():
        # Create all database tables
        db.create_all()

        # Create a sample cookbook first
        print("Creating sample cookbook...")
        cookbook = Cookbook(
            title="The Joy of Cooking",
            author="Irma S. Rombauer",
            description="A classic American cookbook",
            publisher="Scribner",
            isbn="978-0-7432-4626-2",
        )
        db.session.add(cookbook)
        db.session.commit()
        print(f"Created cookbook: {cookbook.title} (ID: {cookbook.id})")

        # Create test client
        client = app.test_client()
        print("Testing recipe upload with cookbook information...")
        image_data = create_sample_image_data()

        # Test the upload endpoint with cookbook information
        response = client.post(
            "/api/recipes/upload",
            data={
                "image": (io.BytesIO(image_data), "test_recipe.png"),
                "cookbook_id": str(cookbook.id),
                "page_number": "125",
            },
            content_type="multipart/form-data",
        )
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response data: {response.get_json()}")

        if response.status_code == 201:
            response_data = response.get_json()
            job_id = response_data.get("job_id")
            image_id = response_data.get("image_id")
            cookbook_info = response_data.get("cookbook")
            page_number = response_data.get("page_number")

            print(f"Upload successful! Job ID: {job_id}, Image ID: {image_id}")
            print(f"Linked to cookbook: {cookbook_info['title']} (Page {page_number})")

            # Test getting the processing job status
            job_response = client.get(f"/api/jobs/{job_id}")
            print(f"Job status response: {job_response.get_json()}")

            # Check if a recipe was created
            job = ProcessingJob.query.get(job_id)
            if job and job.recipe_id:
                recipe_response = client.get(f"/api/recipes/{job.recipe_id}")
                recipe_data = recipe_response.get_json()
                print(f"Created recipe: {recipe_data['title']}")
                print(
                    f"Recipe cookbook: {recipe_data.get('cookbook', {}).get('title', 'None')}"
                )
                print(f"Recipe page number: {recipe_data.get('page_number', 'None')}")

                # Test getting all recipes
                recipes_response = client.get("/api/recipes")
                print(
                    f"Total recipes in database: {recipes_response.get_json()['total']}"
                )
            else:
                print("No recipe was created yet (processing may be async)")
        else:
            print(f"Upload failed with status {response.status_code}")
            print(f"Error: {response.get_json()}")

        # Also test upload without cookbook information for comparison
        print("\nTesting upload without cookbook information...")
        response2 = client.post(
            "/api/recipes/upload",
            data={"image": (io.BytesIO(image_data), "test_recipe_no_book.png")},
            content_type="multipart/form-data",
        )
        print(f"Upload without cookbook - Status: {response2.status_code}")
        if response2.status_code == 201:
            response_data2 = response2.get_json()
            print(f"Cookbook info: {response_data2.get('cookbook')}")
            print(f"Page number: {response_data2.get('page_number')}")


def test_recipe_crud():
    """Test basic CRUD operations on recipes."""
    print("\nTesting recipe CRUD operations...")
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        client = app.test_client()

        # Test getting recipes when database is empty
        response = client.get("/api/recipes")
        print(f"Empty recipes response: {response.get_json()}")

        # Create a cookbook first
        cookbook = Cookbook(
            title="Test Cookbook from Script",
            author="Test Author",
            description="A test cookbook for CRUD operations",
        )
        db.session.add(cookbook)
        db.session.flush()

        # Create recipe with new schema
        recipe = Recipe(
            title="Test Recipe from Script",
            description="A test recipe created by the test script",
            cookbook_id=cookbook.id,
            page_number=42,
            prep_time=15,
            cook_time=30,
            servings=4,
            difficulty="easy",
        )

        db.session.add(recipe)
        db.session.flush()

        # Add instructions
        instructions = ["Mix ingredients", "Cook for 30 minutes", "Serve hot"]
        for i, instruction_text in enumerate(instructions, 1):
            instruction = Instruction(
                recipe_id=recipe.id, step_number=i, text=instruction_text
            )
            db.session.add(instruction)

        # Add tags
        tags = ["test", "script", "demo"]
        for tag_name in tags:
            tag = Tag(recipe_id=recipe.id, name=tag_name)
            db.session.add(tag)

        db.session.commit()
        print(f"Created recipe with ID: {recipe.id}")
        print(f"Linked to cookbook: {cookbook.title} (Page {recipe.page_number})")

        # Test getting the specific recipe
        response = client.get(f"/api/recipes/{recipe.id}")
        recipe_data = response.get_json()
        print(f"Get recipe response:")
        print(f"  Title: {recipe_data['title']}")
        print(f"  Cookbook: {recipe_data.get('cookbook', {}).get('title', 'None')}")
        print(f"  Page: {recipe_data.get('page_number', 'None')}")
        print(f"  Instructions: {len(recipe_data.get('instructions', []))} steps")
        print(f"  Tags: {[tag['name'] for tag in recipe_data.get('tags', [])]}")

        # Test getting all recipes
        response = client.get("/api/recipes")
        all_recipes_data = response.get_json()
        print(f"Total recipes in database: {all_recipes_data['total']}")
        if all_recipes_data["recipes"]:
            first_recipe = all_recipes_data["recipes"][0]
            print(f"First recipe: {first_recipe['title']}")


def main():
    """Main function to run all tests."""
    print("Starting Flask app test script...")
    print("=" * 50)

    try:
        test_upload_recipe()
        test_recipe_crud()
        print("\n" + "=" * 50)
        print("Test script completed successfully!")
    except Exception as e:
        print(f"Test script failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

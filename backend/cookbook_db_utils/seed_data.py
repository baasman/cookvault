#!/usr/bin/env python3
"""
Data Seeding System - Sample data generation for Cookbook Creator (Fixed Version)

This module provides utilities for:
- Creating sample users with different roles
- Generating sample cookbooks and recipes
- Populating ingredient database
- Creating test processing jobs
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict

from cookbook_db_utils.imports import (
    create_app, db, User, UserSession, Password, Recipe, Cookbook, Ingredient,
    Tag, Instruction, RecipeImage, ProcessingJob,
    UserRole, UserStatus, ProcessingStatus, recipe_ingredients
)


class DataSeeder:
    """Sample data seeding operations"""

    def __init__(self, config_name: str = "development"):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name

    def seed_all(self, dataset: str = "full") -> Dict[str, int]:
        """Seed all sample data in a single transaction"""
        print("🌱 Starting comprehensive data seeding...")
        print(f"📊 Dataset: {dataset}")
        print("=" * 50)

        results = {}

        try:
            with self.app.app_context():
                # Create all data in order within a single context and transaction
                
                # 1. Create users
                users = self._create_sample_users()
                results['users'] = len(users)
                db.session.flush()  # Get user IDs
                
                # 2. Create ingredients
                ingredients = self._create_sample_ingredients()
                results['ingredients'] = len(ingredients)
                db.session.flush()  # Get ingredient IDs
                
                # 3. Create cookbooks
                cookbooks = self._create_sample_cookbooks(users)
                results['cookbooks'] = len(cookbooks)
                db.session.flush()  # Get cookbook IDs
                
                # 4. Create recipes
                recipes = self._create_sample_recipes(users, cookbooks, ingredients)
                results['recipes'] = len(recipes)
                db.session.flush()  # Get recipe IDs
                
                # 5. Create processing jobs
                jobs = self._create_sample_processing_jobs(recipes)
                results['processing_jobs'] = len(jobs)

                # Commit all changes at once
                db.session.commit()

                print("\n🎉 Data seeding completed successfully!")
                print("📊 Summary:")
                for category, count in results.items():
                    print(f"   {category}: {count}")

                return results

        except Exception as e:
            print(f"❌ Error during data seeding: {e}")
            db.session.rollback()
            return {}

    def _create_sample_users(self) -> List[User]:
        """Create sample users"""
        sample_users = [
            {
                "username": "admin",
                "email": "admin@cookbook.com",
                "first_name": "Admin",
                "last_name": "User",
                "role": UserRole.ADMIN,
                "password": "admin123"
            },
            {
                "username": "chef_gordon",
                "email": "gordon@cookbook.com",
                "first_name": "Gordon",
                "last_name": "Chef",
                "role": UserRole.USER,
                "password": "chef123"
            },
            {
                "username": "home_cook",
                "email": "home@cookbook.com",
                "first_name": "Home",
                "last_name": "Cook",
                "role": UserRole.USER,
                "password": "cook123"
            }
        ]

        created_users = []
        
        for user_data in sample_users:
            # Check if user already exists
            existing = User.query.filter_by(username=user_data["username"]).first()
            if existing:
                created_users.append(existing)
                continue

            user = User(
                username=user_data["username"],
                email=user_data["email"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                role=user_data["role"],
                status=UserStatus.ACTIVE,
                is_verified=True
            )
            user.set_password(user_data["password"])
            
            db.session.add(user)
            created_users.append(user)

        print(f"✅ Created {len(created_users)} users")
        return created_users

    def _create_sample_ingredients(self) -> List[Ingredient]:
        """Create sample ingredients"""
        sample_ingredients = [
            # Basic seasonings
            {"name": "salt", "category": "seasoning"},
            {"name": "black pepper", "category": "seasoning"},
            {"name": "olive oil", "category": "oil"},
            {"name": "garlic", "category": "vegetable"},
            {"name": "onion", "category": "vegetable"},
            {"name": "butter", "category": "dairy"},
            {"name": "lemon", "category": "fruit"},
            
            # Brussels sprouts recipe ingredients
            {"name": "brussels sprouts", "category": "vegetable"},
            {"name": "black garlic", "category": "seasoning"},
            {"name": "thyme", "category": "herb"},
            {"name": "parmesan cheese", "category": "dairy"},
            
            # New potatoes recipe ingredients
            {"name": "new potatoes", "category": "vegetable"},
            {"name": "fresh peas", "category": "vegetable"},
            {"name": "cilantro", "category": "herb"},
            {"name": "mint", "category": "herb"},
            {"name": "spring onions", "category": "vegetable"},
            
            # Tofu chraimeh recipe ingredients
            {"name": "firm tofu", "category": "protein"},
            {"name": "haricots verts", "category": "vegetable"},
            {"name": "canned tomatoes", "category": "pantry"},
            {"name": "cumin", "category": "spice"},
            {"name": "paprika", "category": "spice"},
            {"name": "cayenne pepper", "category": "spice"},
            {"name": "coriander seeds", "category": "spice"},
            {"name": "fresh chilies", "category": "vegetable"},
        ]

        created_ingredients = []
        
        for ing_data in sample_ingredients:
            # Check if ingredient already exists
            existing = Ingredient.query.filter_by(name=ing_data["name"]).first()
            if existing:
                created_ingredients.append(existing)
                continue

            ingredient = Ingredient(
                name=ing_data["name"],
                category=ing_data["category"]
            )
            db.session.add(ingredient)
            created_ingredients.append(ingredient)

        print(f"✅ Created {len(created_ingredients)} ingredients")
        return created_ingredients

    def _create_sample_cookbooks(self, users: List[User]) -> List[Cookbook]:
        """Create sample cookbooks"""
        if not users:
            return []

        sample_cookbooks = [
            {
                "title": "Ottolenghi Simple",
                "author": "Yotam Ottolenghi",
                "description": "A cookbook of abundantly flavored recipes that offer maximum joy for minimum effort",
                "publisher": "Ten Speed Press",
                "isbn": "978-1607749165",
                "publication_date": datetime(2018, 10, 4)
            }
        ]

        created_cookbooks = []
        
        for i, cookbook_data in enumerate(sample_cookbooks):
            user = users[i % len(users)]
            
            cookbook = Cookbook(
                title=cookbook_data["title"],
                author=cookbook_data["author"],
                description=cookbook_data["description"],
                publisher=cookbook_data.get("publisher"),
                isbn=cookbook_data.get("isbn"),
                publication_date=cookbook_data.get("publication_date"),
                user_id=user.id
            )
            db.session.add(cookbook)
            created_cookbooks.append(cookbook)

        print(f"✅ Created {len(created_cookbooks)} cookbooks")
        return created_cookbooks

    def _create_sample_recipes(self, users: List[User], cookbooks: List[Cookbook], 
                              ingredients: List[Ingredient]) -> List[Recipe]:
        """Create sample recipes"""
        if not users or not cookbooks or not ingredients:
            return []

        sample_recipes = [
            {
                "title": "Brussels Sprouts with Browned Butter and Black Garlic",
                "description": "Charred Brussels sprouts enhanced with the deep, molasses-like sweetness of black garlic and nutty browned butter",
                "prep_time": 15,
                "cook_time": 25,
                "servings": 4,
                "difficulty": "medium",
                "page_number": 142,
                "image_filename": "brussel-sprouts-browned-butter-black-garlic.png"
            },
            {
                "title": "New Potatoes with Peas and Cilantro",
                "description": "Baby potatoes cooked with fresh peas and finished with bright cilantro and a lemony dressing",
                "prep_time": 10,
                "cook_time": 20,
                "servings": 6,
                "difficulty": "easy",
                "page_number": 98,
                "image_filename": "new-potatoes-peas-cilantro.png"
            },
            {
                "title": "Tofu and Haricots Verts Chraimeh",
                "description": "Silky tofu and crisp green beans in a spicy North African tomato sauce with warming spices",
                "prep_time": 20,
                "cook_time": 30,
                "servings": 4,
                "difficulty": "medium",
                "page_number": 176,
                "image_filename": "tofu-haricots-chraimeh.png"
            }
        ]

        created_recipes = []
        
        for i, recipe_data in enumerate(sample_recipes):
            user = users[i % len(users)]
            cookbook = cookbooks[0]  # Use the Ottolenghi Simple cookbook for all recipes
            
            recipe = Recipe(
                title=recipe_data["title"],
                description=recipe_data["description"],
                prep_time=recipe_data["prep_time"],
                cook_time=recipe_data["cook_time"],
                servings=recipe_data["servings"],
                difficulty=recipe_data["difficulty"],
                page_number=recipe_data.get("page_number"),
                user_id=user.id,
                cookbook_id=cookbook.id
            )
            db.session.add(recipe)
            db.session.flush()  # Get recipe ID
            
            # Add realistic cooking instructions for each recipe
            instructions_by_recipe = [
                # Brussels Sprouts with Browned Butter and Black Garlic
                [
                    "Preheat the oven to 220°C/200°C fan/425°F/gas 7.",
                    "Trim the Brussels sprouts and cut in half lengthwise through the core.",
                    "Toss the Brussels sprouts with olive oil, salt, and pepper on a large baking sheet.",
                    "Roast for 20-25 minutes until charred and tender, turning once halfway through.",
                    "Meanwhile, heat butter in a small pan over medium heat until it turns golden brown and smells nutty.",
                    "Mash the black garlic with a fork until smooth.",
                    "Toss the roasted sprouts with browned butter, black garlic, and fresh thyme.",
                    "Finish with grated Parmesan and serve immediately."
                ],
                # New Potatoes with Peas and Cilantro
                [
                    "Place new potatoes in a large pot of salted water and bring to a boil.",
                    "Cook for 15-18 minutes until tender when pierced with a knife.",
                    "Meanwhile, blanch fresh peas in boiling water for 2 minutes, then drain.",
                    "Drain potatoes and let cool slightly, then cut in half if large.",
                    "Make a dressing with olive oil, lemon juice, minced garlic, salt, and pepper.",
                    "Toss warm potatoes with peas, chopped cilantro, mint, and spring onions.",
                    "Add the dressing and toss gently to combine.",
                    "Taste and adjust seasoning, then serve warm or at room temperature."
                ],
                # Tofu and Haricots Verts Chraimeh
                [
                    "Heat oil in a large pan and fry cubed tofu until golden on all sides. Set aside.",
                    "In the same pan, sauté onions until softened, about 5 minutes.",
                    "Add garlic, cumin, paprika, coriander seeds, and cayenne. Cook for 1 minute.",
                    "Add crushed tomatoes, fresh chilies, salt, and a splash of water.",
                    "Simmer the sauce for 15 minutes until thickened.",
                    "Add trimmed haricots verts and cook for 8-10 minutes until tender.",
                    "Return tofu to the pan and simmer for 5 minutes to heat through.",
                    "Garnish with fresh cilantro and serve with rice or flatbread."
                ]
            ]
            
            recipe_instructions = instructions_by_recipe[i] if i < len(instructions_by_recipe) else [f"Follow the traditional method for {recipe_data['title']}"]
            
            for step_num, instruction_text in enumerate(recipe_instructions, 1):
                instruction = Instruction(
                    recipe_id=recipe.id,
                    step_number=step_num,
                    text=instruction_text
                )
                db.session.add(instruction)
            
            # Add one ingredient
            if ingredients:
                ingredient = ingredients[i % len(ingredients)]
                stmt = recipe_ingredients.insert().values(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=1,
                    unit="cup",
                    optional=False,
                    order=1
                )
                db.session.execute(stmt)
            
            created_recipes.append(recipe)

        print(f"✅ Created {len(created_recipes)} recipes")
        return created_recipes

    def _create_sample_processing_jobs(self, recipes: List[Recipe]) -> List[ProcessingJob]:
        """Create sample processing jobs"""
        if not recipes:
            return []

        # Image filenames from the seed_data directory
        image_files = [
            "brussel-sprouts-browned-butter-black-garlic.png",
            "new-potatoes-peas-cilantro.png",
            "tofu-haricots-chraimeh.png"
        ]

        created_jobs = []
        
        # Create processing jobs for all recipes
        for i, recipe in enumerate(recipes):
            image_filename = image_files[i] if i < len(image_files) else "sample_image.jpg"
            
            # Create a recipe image for each recipe
            recipe_image = RecipeImage(
                filename=image_filename,
                original_filename=image_filename,
                file_path=f"/Users/baasman/projects/cookbook-creator/backend/scripts/seed_data/{image_filename}",
                file_size=2048576,  # ~2MB realistic file size
                content_type="image/png"
            )
            db.session.add(recipe_image)
            db.session.flush()  # Get the image ID
            
            # Create processing job with realistic OCR text
            ocr_texts = [
                f"Recipe from Ottolenghi Simple: {recipe.title}. This delicious recipe combines traditional techniques with modern flavors.",
                f"From the cookbook Ottolenghi Simple by Yotam Ottolenghi. Page {recipe.page_number or 'unknown'}. {recipe.description}",
                f"Ottolenghi Simple recipe: {recipe.title}. Prep time: {recipe.prep_time} minutes. Cook time: {recipe.cook_time} minutes."
            ]
            
            job = ProcessingJob(
                recipe_id=recipe.id,
                image_id=recipe_image.id,
                status=ProcessingStatus.COMPLETED,
                ocr_text=ocr_texts[i] if i < len(ocr_texts) else f"OCR text for {recipe.title}"
            )
            db.session.add(job)
            created_jobs.append(job)

        print(f"✅ Created {len(created_jobs)} processing jobs")
        return created_jobs

    def clear_all_data(self, confirm: bool = False) -> bool:
        """Clear all seeded data"""
        if not confirm:
            print("⚠️  WARNING: This will delete all data!")
            response = input("Continue? (y/N): ").lower().strip()
            if response != 'y':
                print("Operation cancelled.")
                return False

        try:
            with self.app.app_context():
                # Delete in reverse order to avoid foreign key issues
                ProcessingJob.query.delete()
                Instruction.query.delete()
                Recipe.query.delete()
                Cookbook.query.delete()
                Ingredient.query.delete()
                User.query.delete()
                
                db.session.commit()
                print("✅ All data cleared successfully!")
                return True
        except Exception as e:
            print(f"❌ Error clearing data: {e}")
            db.session.rollback()
            return False

    # Legacy methods for backwards compatibility
    def seed_users(self) -> List[User]:
        """Create sample users (standalone)"""
        with self.app.app_context():
            users = self._create_sample_users()
            db.session.commit()
            return users

    def seed_ingredients(self) -> List[Ingredient]:
        """Create sample ingredients (standalone)"""
        with self.app.app_context():
            ingredients = self._create_sample_ingredients()
            db.session.commit()
            return ingredients


def main():
    """Command line interface for data seeder"""
    import argparse

    parser = argparse.ArgumentParser(description="Cookbook Creator Data Seeder")
    parser.add_argument("--env", default="development",
                       choices=["development", "testing"],
                       help="Environment configuration")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Seed all
    seed_parser = subparsers.add_parser("seed", help="Seed all sample data")
    seed_parser.add_argument("--dataset", default="full", 
                           choices=["minimal", "full", "demo"],
                           help="Dataset size to seed")

    # Clear data
    clear_parser = subparsers.add_parser("clear", help="Clear all data")
    clear_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # Individual components
    subparsers.add_parser("users", help="Seed only users")
    subparsers.add_parser("ingredients", help="Seed only ingredients")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Create seeder
    seeder = DataSeeder(args.env)

    # Execute command
    if args.command == "seed":
        seeder.seed_all(args.dataset)
    elif args.command == "clear":
        seeder.clear_all_data(confirm=args.yes)
    elif args.command == "users":
        seeder.seed_users()
    elif args.command == "ingredients":
        seeder.seed_ingredients()


if __name__ == "__main__":
    main()
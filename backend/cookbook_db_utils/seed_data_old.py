#!/usr/bin/env python3
"""
Data Seeding System - Sample data generation for Cookbook Creator

This module provides utilities for:
- Creating sample users with different roles
- Generating sample cookbooks and recipes
- Populating ingredient database
- Creating test processing jobs
- Different seed data sets for various purposes
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

    def _seed_users_internal(self) -> List[User]:
        """Create sample users (internal method, requires app context)"""
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
                "username": "baker_julia",
                "email": "julia@cookbook.com",
                "first_name": "Julia",
                "last_name": "Baker",
                "role": UserRole.USER,
                "password": "baker123"
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
            
        db.session.flush()  # Get IDs without committing
        print(f"✅ Created {len(created_users)} users")
        return created_users

    def seed_users(self) -> List[User]:
        """Create sample users"""
        with self.app.app_context():
            users = self._seed_users_internal()
            db.session.commit()
            return users

    def _seed_ingredients_internal(self) -> List[Ingredient]:
        """Create sample ingredients (internal method, requires app context)"""
        sample_ingredients = [
            {"name": "salt", "category": "seasoning"},
            {"name": "black pepper", "category": "seasoning"},
            {"name": "olive oil", "category": "oil"},
            {"name": "garlic", "category": "vegetable"},
            {"name": "onion", "category": "vegetable"},
            {"name": "tomato", "category": "vegetable"},
            {"name": "flour", "category": "baking"},
            {"name": "sugar", "category": "baking"},
            {"name": "eggs", "category": "dairy"},
            {"name": "butter", "category": "dairy"},
            {"name": "milk", "category": "dairy"},
            {"name": "chicken breast", "category": "meat"},
            {"name": "ground beef", "category": "meat"},
            {"name": "salmon", "category": "fish"},
            {"name": "rice", "category": "grain"},
            {"name": "pasta", "category": "grain"},
            {"name": "basil", "category": "herb"},
            {"name": "oregano", "category": "herb"},
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
            
        db.session.flush()  # Get IDs without committing
        print(f"✅ Created {len(created_ingredients)} ingredients")
        return created_ingredients

    def seed_ingredients(self) -> List[Ingredient]:
        """Create sample ingredients"""
        with self.app.app_context():
            ingredients = self._seed_ingredients_internal()
            db.session.commit()
            return ingredients

    def seed_cookbooks(self, users: List[User]) -> List[Cookbook]:
        """Create sample cookbooks"""
        if not users:
            print("❌ No users available for cookbook creation")
            return []

        sample_cookbooks = [
            {
                "title": "Quick & Easy Meals",
                "author": "Gordon Chef",
                "description": "Simple recipes for busy weeknights"
            },
            {
                "title": "Artisan Bread Recipes",
                "author": "Julia Baker", 
                "description": "Traditional and modern bread recipes"
            },
            {
                "title": "Healthy Home Cooking",
                "author": "Home Cook",
                "description": "Nutritious family-friendly recipes"
            }
        ]

        created_cookbooks = []
        
        with self.app.app_context():
            for i, cookbook_data in enumerate(sample_cookbooks):
                user = users[i % len(users)]
                
                cookbook = Cookbook(
                    title=cookbook_data["title"],
                    author=cookbook_data["author"],
                    description=cookbook_data["description"],
                    user_id=user.id
                )
                db.session.add(cookbook)
                created_cookbooks.append(cookbook)
                
            db.session.commit()
            print(f"✅ Created {len(created_cookbooks)} cookbooks")
            
        return created_cookbooks

    def seed_tags(self) -> List[Tag]:
        """Create sample tags"""
        sample_tags = [
            "quick", "easy", "healthy", "vegetarian", "vegan", 
            "gluten-free", "spicy", "comfort-food", "dessert", "appetizer"
        ]

        created_tags = []
        
        with self.app.app_context():
            for tag_name in sample_tags:
                # For this simple version, we'll create standalone tags
                # In a real implementation, tags would be associated with specific recipes
                pass  # Tags are created with recipes in this model
                
        return created_tags

    def seed_recipes(self, users: List[User], cookbooks: List[Cookbook], 
                    ingredients: List[Ingredient], tags: List[Tag]) -> List[Recipe]:
        """Create sample recipes"""
        if not users or not cookbooks or not ingredients:
            print("❌ Missing prerequisites for recipe creation")
            return []

        sample_recipes = [
            {
                "title": "Spaghetti Carbonara",
                "description": "Classic Italian pasta dish",
                "prep_time": 15,
                "cook_time": 20,
                "servings": 4,
                "difficulty": "medium"
            },
            {
                "title": "Grilled Chicken Salad", 
                "description": "Healthy protein-packed salad",
                "prep_time": 10,
                "cook_time": 15,
                "servings": 2,
                "difficulty": "easy"
            },
            {
                "title": "Chocolate Chip Cookies",
                "description": "Classic homemade cookies",
                "prep_time": 20,
                "cook_time": 12,
                "servings": 24,
                "difficulty": "easy"
            }
        ]

        created_recipes = []
        
        with self.app.app_context():
            for i, recipe_data in enumerate(sample_recipes):
                user = users[i % len(users)]
                cookbook = cookbooks[i % len(cookbooks)]
                
                recipe = Recipe(
                    title=recipe_data["title"],
                    description=recipe_data["description"],
                    prep_time=recipe_data["prep_time"],
                    cook_time=recipe_data["cook_time"],
                    servings=recipe_data["servings"],
                    difficulty=recipe_data["difficulty"],
                    user_id=user.id,
                    cookbook_id=cookbook.id
                )
                db.session.add(recipe)
                db.session.flush()  # Get recipe ID
                
                # Add sample instruction
                instruction = Instruction(
                    recipe_id=recipe.id,
                    step_number=1,
                    text=f"Follow the traditional method for {recipe_data['title']}"
                )
                db.session.add(instruction)
                
                # Add sample ingredients (simplified)
                if ingredients:
                    sample_ingredient = ingredients[i % len(ingredients)]
                    stmt = recipe_ingredients.insert().values(
                        recipe_id=recipe.id,
                        ingredient_id=sample_ingredient.id,
                        quantity=1,
                        unit="cup",
                        optional=False,
                        order=1
                    )
                    db.session.execute(stmt)
                
                created_recipes.append(recipe)
                
            db.session.commit()
            print(f"✅ Created {len(created_recipes)} recipes")
            
        return created_recipes

    def seed_processing_jobs(self, recipes: List[Recipe]) -> List[ProcessingJob]:
        """Create sample processing jobs"""
        if not recipes:
            return []

        created_jobs = []
        
        with self.app.app_context():
            for recipe in recipes[:2]:  # Only create jobs for first 2 recipes
                job = ProcessingJob(
                    recipe_id=recipe.id,
                    status=ProcessingStatus.COMPLETED,
                    ocr_text=f"Sample OCR text for {recipe.title}"
                )
                db.session.add(job)
                created_jobs.append(job)
                
            db.session.commit()
            print(f"✅ Created {len(created_jobs)} processing jobs")
            
        return created_jobs

    def seed_all(self, dataset: str = "full") -> Dict[str, int]:
        """Seed all sample data"""
        print("🌱 Starting comprehensive data seeding...")
        print(f"📊 Dataset: {dataset}")
        print("=" * 50)

        results = {}

        try:
            with self.app.app_context():
                # Create all data in order within a single context and transaction
                users = self._seed_users_internal()
                results['users'] = len(users)

                ingredients = self._seed_ingredients_internal()
                results['ingredients'] = len(ingredients)

                cookbooks = self._seed_cookbooks_internal(users)
                results['cookbooks'] = len(cookbooks)

                tags = self._seed_tags_internal()
                results['tags'] = len(tags)

                recipes = self._seed_recipes_internal(users, cookbooks, ingredients, tags)
                results['recipes'] = len(recipes)

                jobs = self._seed_processing_jobs_internal(recipes)
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
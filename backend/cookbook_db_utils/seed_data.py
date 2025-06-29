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
            {"name": "salt", "category": "seasoning"},
            {"name": "black pepper", "category": "seasoning"},
            {"name": "olive oil", "category": "oil"},
            {"name": "garlic", "category": "vegetable"},
            {"name": "onion", "category": "vegetable"},
            {"name": "flour", "category": "baking"},
            {"name": "eggs", "category": "dairy"},
            {"name": "butter", "category": "dairy"},
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
                "title": "Quick & Easy Meals",
                "author": "Gordon Chef",
                "description": "Simple recipes for busy weeknights"
            },
            {
                "title": "Healthy Home Cooking",
                "author": "Home Cook",
                "description": "Nutritious family-friendly recipes"
            }
        ]

        created_cookbooks = []
        
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

        print(f"✅ Created {len(created_cookbooks)} cookbooks")
        return created_cookbooks

    def _create_sample_recipes(self, users: List[User], cookbooks: List[Cookbook], 
                              ingredients: List[Ingredient]) -> List[Recipe]:
        """Create sample recipes"""
        if not users or not cookbooks or not ingredients:
            return []

        sample_recipes = [
            {
                "title": "Simple Pasta",
                "description": "A basic pasta recipe",
                "prep_time": 10,
                "cook_time": 15,
                "servings": 2,
                "difficulty": "easy"
            },
            {
                "title": "Basic Salad",
                "description": "Fresh and healthy salad",
                "prep_time": 5,
                "cook_time": 0,
                "servings": 1,
                "difficulty": "easy"
            }
        ]

        created_recipes = []
        
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
            
            # Add one instruction
            instruction = Instruction(
                recipe_id=recipe.id,
                step_number=1,
                text=f"Follow the traditional method for {recipe_data['title']}"
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

        created_jobs = []
        
        # First create a sample recipe image for the processing job
        for recipe in recipes[:1]:  # Only create job for first recipe
            # Create a sample recipe image first
            recipe_image = RecipeImage(
                recipe_id=recipe.id,
                filename="sample_image.jpg",
                original_filename="sample_recipe_image.jpg",
                file_path="/tmp/sample_image.jpg",
                file_size=1024,
                content_type="image/jpeg"
            )
            db.session.add(recipe_image)
            db.session.flush()  # Get the image ID
            
            # Now create the processing job with the image reference
            job = ProcessingJob(
                recipe_id=recipe.id,
                image_id=recipe_image.id,
                status=ProcessingStatus.COMPLETED,
                ocr_text=f"Sample OCR text for {recipe.title}"
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
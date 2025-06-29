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

import sys
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent.parent))

from app import create_app, db
from app.models import (
    User, UserSession, Password, Recipe, Cookbook, Ingredient,
    Tag, Instruction, RecipeImage, ProcessingJob,
    UserRole, UserStatus, ProcessingStatus, recipe_ingredients
)


class DataSeeder:
    """Comprehensive data seeding for development and testing"""
    
    def __init__(self, config_name: str = "development"):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name
        
        # Sample data templates
        self.sample_users = [
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
                "last_name": "Ramsay",
                "role": UserRole.USER,
                "password": "cooking123"
            },
            {
                "username": "baker_julia",
                "email": "julia@cookbook.com",
                "first_name": "Julia",
                "last_name": "Child",
                "role": UserRole.USER,
                "password": "baking123"
            },
            {
                "username": "home_cook",
                "email": "home@cookbook.com",
                "first_name": "Home",
                "last_name": "Cook",
                "role": UserRole.USER,
                "password": "homecook123"
            }
        ]
        
        self.sample_cookbooks = [
            {
                "title": "Mastering the Art of French Cooking",
                "author": "Julia Child",
                "description": "A comprehensive guide to French cuisine techniques and recipes.",
                "publisher": "Knopf",
                "isbn": "978-0375413408",
                "publication_date": datetime(1961, 10, 16)
            },
            {
                "title": "The Joy of Cooking",
                "author": "Irma S. Rombauer",
                "description": "America's most trusted cookbook with over 4,000 recipes.",
                "publisher": "Scribner",
                "isbn": "978-0743246262",
                "publication_date": datetime(1931, 1, 1)
            },
            {
                "title": "Salt, Fat, Acid, Heat",
                "author": "Samin Nosrat",
                "description": "Master the four fundamental elements of good cooking.",
                "publisher": "Simon & Schuster",
                "isbn": "978-1476753836",
                "publication_date": datetime(2017, 4, 25)
            },
            {
                "title": "Mediterranean Everyday",
                "author": "Peter Minaki",
                "description": "Simple, healthy Mediterranean recipes for everyday cooking.",
                "publisher": "Ten Speed Press",
                "isbn": "978-1580089999",
                "publication_date": datetime(2019, 3, 12)
            }
        ]
        
        self.sample_ingredients = [
            # Proteins
            {"name": "chicken breast", "category": "protein", "common_units": "lbs,pieces"},
            {"name": "ground beef", "category": "protein", "common_units": "lbs,oz"},
            {"name": "salmon fillet", "category": "protein", "common_units": "lbs,fillets"},
            {"name": "eggs", "category": "protein", "common_units": "pieces,dozen"},
            
            # Vegetables
            {"name": "onion", "category": "vegetable", "common_units": "pieces,cups"},
            {"name": "garlic", "category": "vegetable", "common_units": "cloves,tsp"},
            {"name": "tomatoes", "category": "vegetable", "common_units": "pieces,cups"},
            {"name": "bell pepper", "category": "vegetable", "common_units": "pieces,cups"},
            {"name": "carrots", "category": "vegetable", "common_units": "pieces,cups"},
            {"name": "potatoes", "category": "vegetable", "common_units": "pieces,lbs"},
            
            # Herbs & Spices
            {"name": "salt", "category": "seasoning", "common_units": "tsp,tbsp"},
            {"name": "black pepper", "category": "seasoning", "common_units": "tsp,tbsp"},
            {"name": "olive oil", "category": "oil", "common_units": "tbsp,cups"},
            {"name": "basil", "category": "herb", "common_units": "tsp,tbsp,leaves"},
            {"name": "oregano", "category": "herb", "common_units": "tsp,tbsp"},
            {"name": "thyme", "category": "herb", "common_units": "tsp,tbsp"},
            
            # Grains & Starches
            {"name": "rice", "category": "grain", "common_units": "cups,lbs"},
            {"name": "pasta", "category": "grain", "common_units": "oz,lbs"},
            {"name": "flour", "category": "baking", "common_units": "cups,lbs"},
            {"name": "bread", "category": "grain", "common_units": "slices,loaves"},
            
            # Dairy
            {"name": "milk", "category": "dairy", "common_units": "cups,gallons"},
            {"name": "butter", "category": "dairy", "common_units": "tbsp,sticks"},
            {"name": "cheese", "category": "dairy", "common_units": "cups,oz"},
            {"name": "cream", "category": "dairy", "common_units": "cups,oz"},
        ]
        
        self.sample_tags = [
            "Italian", "French", "Mediterranean", "Asian", "Mexican",
            "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Low-Carb",
            "Breakfast", "Lunch", "Dinner", "Dessert", "Appetizer",
            "Quick", "Easy", "Comfort Food", "Healthy", "Spicy"
        ]
    
    def seed_users(self) -> List[User]:
        """Create sample users with different roles"""
        print("👥 Seeding users...")
        users = []
        
        with self.app.app_context():
            for user_data in self.sample_users:
                # Check if user already exists
                existing = User.query.filter_by(username=user_data["username"]).first()
                if existing:
                    print(f"   User {user_data['username']} already exists, skipping...")
                    users.append(existing)
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
                users.append(user)
                print(f"   Created user: {user_data['username']}")
            
            db.session.commit()
            print(f"✅ Created {len(users)} users")
            return users
    
    def seed_ingredients(self) -> List[Ingredient]:
        """Create common cooking ingredients"""
        print("🥕 Seeding ingredients...")
        ingredients = []
        
        with self.app.app_context():
            for ing_data in self.sample_ingredients:
                # Check if ingredient already exists
                existing = Ingredient.query.filter_by(name=ing_data["name"]).first()
                if existing:
                    ingredients.append(existing)
                    continue
                
                ingredient = Ingredient(
                    name=ing_data["name"],
                    category=ing_data["category"],
                    common_units=ing_data["common_units"]
                )
                
                db.session.add(ingredient)
                ingredients.append(ingredient)
            
            db.session.commit()
            print(f"✅ Created {len(ingredients)} ingredients")
            return ingredients
    
    def seed_cookbooks(self, users: List[User]) -> List[Cookbook]:
        """Create sample cookbooks"""
        print("📚 Seeding cookbooks...")
        cookbooks = []
        
        with self.app.app_context():
            for i, cookbook_data in enumerate(self.sample_cookbooks):
                # Check if cookbook already exists
                existing = Cookbook.query.filter_by(title=cookbook_data["title"]).first()
                if existing:
                    cookbooks.append(existing)
                    continue
                
                # Assign to different users
                user = users[i % len(users)] if users else None
                
                cookbook = Cookbook(
                    title=cookbook_data["title"],
                    author=cookbook_data["author"],
                    description=cookbook_data["description"],
                    publisher=cookbook_data["publisher"],
                    isbn=cookbook_data["isbn"],
                    publication_date=cookbook_data["publication_date"],
                    user_id=user.id if user else None
                )
                
                db.session.add(cookbook)
                cookbooks.append(cookbook)
                print(f"   Created cookbook: {cookbook_data['title']}")
            
            db.session.commit()
            print(f"✅ Created {len(cookbooks)} cookbooks")
            return cookbooks
    
    def seed_tags(self) -> List[Tag]:
        """Create common recipe tags"""
        print("🏷️  Seeding tags...")
        tags = []
        
        with self.app.app_context():
            for tag_name in self.sample_tags:
                # Check if tag already exists
                existing = Tag.query.filter_by(name=tag_name).first()
                if existing:
                    tags.append(existing)
                    continue
                
                tag = Tag(name=tag_name)
                db.session.add(tag)
                tags.append(tag)
            
            db.session.commit()
            print(f"✅ Created {len(tags)} tags")
            return tags
    
    def seed_recipes(self, users: List[User], cookbooks: List[Cookbook], 
                    ingredients: List[Ingredient], tags: List[Tag]) -> List[Recipe]:
        """Create sample recipes with full details"""
        print("🍳 Seeding recipes...")
        
        sample_recipes = [
            {
                "title": "Classic Chicken Parmesan",
                "description": "Crispy breaded chicken breast topped with marinara sauce and melted mozzarella cheese.",
                "prep_time": 20,
                "cook_time": 25,
                "servings": 4,
                "difficulty": "medium",
                "source": "Family Recipe",
                "ingredients": [
                    {"name": "chicken breast", "quantity": 4, "unit": "pieces"},
                    {"name": "flour", "quantity": 1, "unit": "cup"},
                    {"name": "eggs", "quantity": 2, "unit": "pieces"},
                    {"name": "cheese", "quantity": 1, "unit": "cup", "preparation": "shredded mozzarella"}
                ],
                "instructions": [
                    "Preheat oven to 375°F",
                    "Pound chicken breasts to even thickness",
                    "Set up breading station with flour, beaten eggs, and breadcrumbs",
                    "Bread each chicken piece thoroughly",
                    "Bake for 20-25 minutes until golden brown",
                    "Top with sauce and cheese, bake 5 more minutes"
                ],
                "tags": ["Italian", "Dinner", "Comfort Food"]
            },
            {
                "title": "Mediterranean Quinoa Salad",
                "description": "Fresh and healthy quinoa salad with vegetables, herbs, and lemon dressing.",
                "prep_time": 15,
                "cook_time": 15,
                "servings": 6,
                "difficulty": "easy",
                "source": "Health Magazine",
                "ingredients": [
                    {"name": "rice", "quantity": 1, "unit": "cup", "preparation": "quinoa"},
                    {"name": "tomatoes", "quantity": 2, "unit": "cups", "preparation": "diced"},
                    {"name": "onion", "quantity": 0.5, "unit": "cup", "preparation": "diced red"},
                    {"name": "olive oil", "quantity": 3, "unit": "tbsp"}
                ],
                "instructions": [
                    "Cook quinoa according to package directions",
                    "Let quinoa cool completely",
                    "Dice all vegetables",
                    "Whisk together olive oil and lemon juice",
                    "Combine all ingredients and toss",
                    "Chill for at least 1 hour before serving"
                ],
                "tags": ["Mediterranean", "Healthy", "Vegetarian", "Lunch"]
            },
            {
                "title": "Chocolate Chip Cookies",
                "description": "Classic soft and chewy chocolate chip cookies that everyone loves.",
                "prep_time": 15,
                "cook_time": 12,
                "servings": 24,
                "difficulty": "easy",
                "source": "Grandma's Recipe",
                "ingredients": [
                    {"name": "flour", "quantity": 2.25, "unit": "cups"},
                    {"name": "butter", "quantity": 1, "unit": "cup", "preparation": "softened"},
                    {"name": "eggs", "quantity": 2, "unit": "pieces"},
                    {"name": "milk", "quantity": 1, "unit": "cup", "preparation": "chocolate chips"}
                ],
                "instructions": [
                    "Preheat oven to 375°F",
                    "Cream together butter and sugars",
                    "Beat in eggs and vanilla",
                    "Gradually mix in flour mixture",
                    "Stir in chocolate chips",
                    "Drop spoonfuls onto baking sheet",
                    "Bake 9-11 minutes until golden brown"
                ],
                "tags": ["Dessert", "Baking", "Easy", "Comfort Food"]
            }
        ]
        
        recipes = []
        
        with self.app.app_context():
            for i, recipe_data in enumerate(sample_recipes):
                # Check if recipe already exists
                existing = Recipe.query.filter_by(title=recipe_data["title"]).first()
                if existing:
                    recipes.append(existing)
                    continue
                
                # Assign to different users and cookbooks
                user = users[i % len(users)] if users else None
                cookbook = cookbooks[i % len(cookbooks)] if cookbooks else None
                
                recipe = Recipe(
                    title=recipe_data["title"],
                    description=recipe_data["description"],
                    prep_time=recipe_data["prep_time"],
                    cook_time=recipe_data["cook_time"],
                    servings=recipe_data["servings"],
                    difficulty=recipe_data["difficulty"],
                    source=recipe_data["source"],
                    user_id=user.id if user else None,
                    cookbook_id=cookbook.id if cookbook else None,
                    page_number=random.randint(1, 200)
                )
                
                db.session.add(recipe)
                db.session.flush()  # Get the recipe ID
                
                # Add ingredients
                for ing_data in recipe_data["ingredients"]:
                    ingredient = next((ing for ing in ingredients if ing.name == ing_data["name"]), None)
                    if ingredient:
                        # Use raw SQL for the association table
                        stmt = recipe_ingredients.insert().values(
                            recipe_id=recipe.id,
                            ingredient_id=ingredient.id,
                            quantity=ing_data["quantity"],
                            unit=ing_data["unit"],
                            preparation=ing_data.get("preparation"),
                            optional=False,
                            order=len(recipe_data["ingredients"])
                        )
                        db.session.execute(stmt)
                
                # Add instructions
                for j, instruction_text in enumerate(recipe_data["instructions"]):
                    instruction = Instruction(
                        recipe_id=recipe.id,
                        step_number=j + 1,
                        text=instruction_text
                    )
                    db.session.add(instruction)
                
                # Add tags
                for tag_name in recipe_data["tags"]:
                    tag = next((t for t in tags if t.name == tag_name), None)
                    if tag:
                        recipe.tags.append(tag)
                
                recipes.append(recipe)
                print(f"   Created recipe: {recipe_data['title']}")
            
            db.session.commit()
            print(f"✅ Created {len(recipes)} recipes")
            return recipes
    
    def seed_processing_jobs(self, recipes: List[Recipe]) -> List[ProcessingJob]:
        """Create sample processing jobs"""
        print("⚙️  Seeding processing jobs...")
        jobs = []
        
        with self.app.app_context():
            statuses = [ProcessingStatus.COMPLETED, ProcessingStatus.PENDING, ProcessingStatus.FAILED]
            
            for i, recipe in enumerate(recipes[:3]):  # Create jobs for first 3 recipes
                job = ProcessingJob(
                    recipe_id=recipe.id,
                    status=statuses[i % len(statuses)],
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                
                if job.status == ProcessingStatus.COMPLETED:
                    job.completed_at = job.created_at + timedelta(minutes=random.randint(1, 10))
                elif job.status == ProcessingStatus.FAILED:
                    job.error_message = "Sample error message for testing"
                
                db.session.add(job)
                jobs.append(job)
                print(f"   Created processing job: {job.status.value}")
            
            db.session.commit()
            print(f"✅ Created {len(jobs)} processing jobs")
            return jobs
    
    def seed_all(self, dataset: str = "full") -> Dict[str, int]:
        """Seed all sample data"""
        print("🌱 Starting comprehensive data seeding...")
        print(f"📊 Dataset: {dataset}")
        print("=" * 50)
        
        results = {}
        
        try:
            with self.app.app_context():
                # Create all data in order
                users = self.seed_users()
                results['users'] = len(users)
                
                ingredients = self.seed_ingredients()
                results['ingredients'] = len(ingredients)
                
                cookbooks = self.seed_cookbooks(users)
                results['cookbooks'] = len(cookbooks)
                
                tags = self.seed_tags()
                results['tags'] = len(tags)
                
                recipes = self.seed_recipes(users, cookbooks, ingredients, tags)
                results['recipes'] = len(recipes)
                
                jobs = self.seed_processing_jobs(recipes)
                results['processing_jobs'] = len(jobs)
                
                print("=" * 50)
                print("🎉 Data seeding completed successfully!")
                print(f"📊 Summary:")
                for category, count in results.items():
                    print(f"   {category:20} {count:>5}")
                
                return results
                
        except Exception as e:
            print(f"❌ Error during seeding: {e}")
            return {}
    
    def clear_all_data(self, confirm: bool = False) -> bool:
        """Clear all seeded data (dangerous operation)"""
        if not confirm:
            print("⚠️  WARNING: This will delete ALL data from the database!")
            print("This action cannot be undone.")
            response = input("Type 'DELETE ALL' to confirm: ").strip()
            if response != 'DELETE ALL':
                print("Operation cancelled.")
                return False
        
        try:
            with self.app.app_context():
                print("🗑️  Clearing all data...")
                
                # Delete in reverse order of dependencies
                ProcessingJob.query.delete()
                RecipeImage.query.delete()
                Instruction.query.delete()
                
                # Clear many-to-many relationships
                db.session.execute(recipe_ingredients.delete())
                
                Recipe.query.delete()
                Tag.query.delete()
                Cookbook.query.delete()
                Ingredient.query.delete()
                UserSession.query.delete()
                Password.query.delete()
                User.query.delete()
                
                db.session.commit()
                print("✅ All data cleared successfully!")
                return True
                
        except Exception as e:
            print(f"❌ Error clearing data: {e}")
            db.session.rollback()
            return False


def main():
    """Command line interface for data seeding"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cookbook Creator Data Seeder")
    parser.add_argument("--env", default="development",
                       choices=["development", "testing", "production"],
                       help="Environment configuration")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Seed all data
    seed_parser = subparsers.add_parser("seed", help="Seed sample data")
    seed_parser.add_argument("--dataset", default="full",
                           choices=["minimal", "full", "demo"],
                           help="Dataset size to seed")
    
    # Clear all data
    clear_parser = subparsers.add_parser("clear", help="Clear all data")
    clear_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    
    # Seed specific components
    subparsers.add_parser("users", help="Seed only users")
    subparsers.add_parser("ingredients", help="Seed only ingredients")
    subparsers.add_parser("cookbooks", help="Seed only cookbooks")
    subparsers.add_parser("recipes", help="Seed only recipes")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create data seeder
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
    elif args.command == "cookbooks":
        users = User.query.all()
        seeder.seed_cookbooks(users)
    elif args.command == "recipes":
        users = User.query.all()
        cookbooks = Cookbook.query.all()
        ingredients = Ingredient.query.all()
        tags = Tag.query.all()
        seeder.seed_recipes(users, cookbooks, ingredients, tags)


if __name__ == "__main__":
    main()
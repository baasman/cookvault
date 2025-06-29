#!/usr/bin/env python3
"""
Development Helpers - Quick utilities for active development

This module provides utilities for:
- Quick database resets during development
- Creating test users with specific roles
- Generating focused sample data
- Database snapshots for testing
- Performance testing data
"""

import sys
import os
import shutil
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
try:
    from .db_manager import DatabaseManager
    from .seed_data import DataSeeder
except ImportError:
    # Fallback for when running as standalone script
    from db_manager import DatabaseManager
    from seed_data import DataSeeder


class DevelopmentHelpers:
    """Development-focused database utilities"""
    
    def __init__(self, config_name: str = "development"):
        """Initialize with Flask app context"""
        self.app = create_app(config_name)
        self.config_name = config_name
        self.db_manager = DatabaseManager(config_name)
        self.seeder = DataSeeder(config_name)
    
    def quick_reset(self) -> bool:
        """Quick database reset optimized for development workflow"""
        print("🔄 Quick development reset...")
        
        try:
            # Use database manager for safe reset
            return self.db_manager.reset_database(confirm=True, seed_data=True)
        except Exception as e:
            print(f"❌ Error during quick reset: {e}")
            return False
    
    def create_test_user(self, username: str, role: UserRole = UserRole.USER,
                        password: str = "test123") -> Optional[User]:
        """Create a test user with specified role"""
        try:
            with self.app.app_context():
                # Check if user already exists
                existing = User.query.filter_by(username=username).first()
                if existing:
                    print(f"⚠️  User {username} already exists")
                    return existing
                
                user = User(
                    username=username,
                    email=f"{username}@test.com",
                    first_name=username.title(),
                    last_name="Test",
                    role=role,
                    status=UserStatus.ACTIVE,
                    is_verified=True
                )
                user.set_password(password)
                
                db.session.add(user)
                db.session.commit()
                
                print(f"✅ Created test user: {username} ({role.value})")
                return user
                
        except Exception as e:
            print(f"❌ Error creating test user: {e}")
            return None
    
    def create_minimal_dataset(self) -> bool:
        """Create minimal dataset for quick testing"""
        print("🎯 Creating minimal dataset for testing...")
        
        try:
            with self.app.app_context():
                # Create basic users
                admin = self.create_test_user("admin", UserRole.ADMIN, "admin123")
                user = self.create_test_user("testuser", UserRole.USER, "test123")
                
                if not admin or not user:
                    return False
                
                # Create minimal ingredients
                essential_ingredients = [
                    {"name": "salt", "category": "seasoning"},
                    {"name": "pepper", "category": "seasoning"},
                    {"name": "olive oil", "category": "oil"},
                    {"name": "garlic", "category": "vegetable"},
                    {"name": "onion", "category": "vegetable"}
                ]
                
                ingredients = []
                for ing_data in essential_ingredients:
                    existing = Ingredient.query.filter_by(name=ing_data["name"]).first()
                    if not existing:
                        ingredient = Ingredient(
                            name=ing_data["name"],
                            category=ing_data["category"]
                        )
                        db.session.add(ingredient)
                        ingredients.append(ingredient)
                    else:
                        ingredients.append(existing)
                
                # Create one test cookbook
                cookbook = Cookbook(
                    title="Test Cookbook",
                    author="Test Author",
                    description="A minimal cookbook for testing",
                    user_id=user.id
                )
                db.session.add(cookbook)
                db.session.flush()
                
                # Create one test recipe
                recipe = Recipe(
                    title="Test Recipe",
                    description="A simple test recipe",
                    prep_time=10,
                    cook_time=15,
                    servings=2,
                    difficulty="easy",
                    user_id=user.id,
                    cookbook_id=cookbook.id
                )
                db.session.add(recipe)
                db.session.flush()
                
                # Add one instruction
                instruction = Instruction(
                    recipe_id=recipe.id,
                    step_number=1,
                    text="This is a test instruction"
                )
                db.session.add(instruction)
                
                # Add one ingredient to recipe
                if ingredients:
                    stmt = recipe_ingredients.insert().values(
                        recipe_id=recipe.id,
                        ingredient_id=ingredients[0].id,
                        quantity=1,
                        unit="tsp",
                        optional=False,
                        order=1
                    )
                    db.session.execute(stmt)
                
                db.session.commit()
                
                print("✅ Minimal dataset created:")
                print("   - 2 users (admin, testuser)")
                print("   - 5 essential ingredients")
                print("   - 1 test cookbook")
                print("   - 1 test recipe with instruction")
                
                return True
                
        except Exception as e:
            print(f"❌ Error creating minimal dataset: {e}")
            db.session.rollback()
            return False
    
    def create_performance_dataset(self, recipe_count: int = 100) -> bool:
        """Create larger dataset for performance testing"""
        print(f"⚡ Creating performance dataset ({recipe_count} recipes)...")
        
        try:
            with self.app.app_context():
                # First create basic data
                if not self.create_minimal_dataset():
                    return False
                
                # Get existing data
                users = User.query.all()
                ingredients = Ingredient.query.all()
                
                if not users or not ingredients:
                    print("❌ Need basic data before creating performance dataset")
                    return False
                
                # Create multiple cookbooks
                cookbooks = []
                for i in range(10):
                    cookbook = Cookbook(
                        title=f"Performance Cookbook {i+1}",
                        author=f"Author {i+1}",
                        description=f"Performance testing cookbook number {i+1}",
                        user_id=users[i % len(users)].id
                    )
                    db.session.add(cookbook)
                    cookbooks.append(cookbook)
                
                db.session.flush()
                
                # Create many recipes
                import random
                difficulties = ["easy", "medium", "hard"]
                
                for i in range(recipe_count):
                    recipe = Recipe(
                        title=f"Performance Recipe {i+1}",
                        description=f"Recipe number {i+1} for performance testing",
                        prep_time=random.randint(5, 60),
                        cook_time=random.randint(10, 120),
                        servings=random.randint(1, 8),
                        difficulty=random.choice(difficulties),
                        user_id=users[i % len(users)].id,
                        cookbook_id=cookbooks[i % len(cookbooks)].id,
                        page_number=random.randint(1, 300)
                    )
                    db.session.add(recipe)
                    
                    # Flush periodically to get IDs
                    if i % 50 == 0:
                        db.session.flush()
                        
                        # Add instructions and ingredients for last batch
                        recent_recipes = Recipe.query.filter(
                            Recipe.title.like("Performance Recipe%")
                        ).offset(max(0, i-49)).limit(50).all()
                        
                        for r in recent_recipes:
                            # Add 2-3 instructions
                            for j in range(random.randint(2, 3)):
                                instruction = Instruction(
                                    recipe_id=r.id,
                                    step_number=j + 1,
                                    text=f"Step {j+1} for recipe {r.title}"
                                )
                                db.session.add(instruction)
                            
                            # Add 3-5 ingredients
                            recipe_ingredients_count = random.randint(3, 5)
                            selected_ingredients = random.sample(ingredients, 
                                                               min(recipe_ingredients_count, len(ingredients)))
                            
                            for k, ingredient in enumerate(selected_ingredients):
                                stmt = recipe_ingredients.insert().values(
                                    recipe_id=r.id,
                                    ingredient_id=ingredient.id,
                                    quantity=random.uniform(0.5, 3.0),
                                    unit=random.choice(["tsp", "tbsp", "cup", "oz"]),
                                    optional=random.choice([True, False]),
                                    order=k + 1
                                )
                                db.session.execute(stmt)
                
                # Final flush for remaining recipes
                db.session.flush()
                
                # Handle any remaining recipes
                remaining_recipes = Recipe.query.filter(
                    Recipe.title.like("Performance Recipe%"),
                    ~Recipe.id.in_(db.session.query(Instruction.recipe_id))
                ).all()
                
                for recipe in remaining_recipes:
                    instruction = Instruction(
                        recipe_id=recipe.id,
                        step_number=1,
                        text=f"Default instruction for {recipe.title}"
                    )
                    db.session.add(instruction)
                
                db.session.commit()
                
                print(f"✅ Performance dataset created:")
                print(f"   - {recipe_count} recipes")
                print(f"   - 10 cookbooks")
                print(f"   - ~{recipe_count * 2.5:.0f} instructions")
                print(f"   - ~{recipe_count * 4:.0f} recipe-ingredient relationships")
                
                return True
                
        except Exception as e:
            print(f"❌ Error creating performance dataset: {e}")
            db.session.rollback()
            return False
    
    def create_snapshot(self, name: str = None) -> bool:
        """Create a snapshot of the current database state"""
        if name is None:
            name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return self.db_manager.backup_database(f"{name}.db")
    
    def restore_snapshot(self, name: str) -> bool:
        """Restore from a snapshot"""
        snapshot_path = f"{name}.db"
        if not Path(snapshot_path).exists():
            print(f"❌ Snapshot not found: {snapshot_path}")
            return False
        
        return self.db_manager.restore_database(snapshot_path, confirm=True)
    
    def list_snapshots(self) -> List[str]:
        """List available snapshots"""
        snapshots = []
        current_dir = Path(".")
        
        for file in current_dir.glob("*.db"):
            if file.name.startswith("snapshot_") or file.name.endswith("_backup.db"):
                snapshots.append(file.stem)
        
        return sorted(snapshots)
    
    def setup_fresh_dev_environment(self) -> bool:
        """Set up a completely fresh development environment"""
        print("🏗️  Setting up fresh development environment...")
        
        try:
            # Reset database
            if not self.quick_reset():
                return False
            
            # Create test users
            self.create_test_user("dev", UserRole.ADMIN, "dev123")
            self.create_test_user("chef", UserRole.USER, "chef123")
            self.create_test_user("baker", UserRole.USER, "baker123")
            
            # Create snapshot
            self.create_snapshot("fresh_dev")
            
            print("✅ Fresh development environment ready!")
            print("   Login credentials:")
            print("   - dev/dev123 (admin)")
            print("   - chef/chef123 (user)")
            print("   - baker/baker123 (user)")
            print("   Snapshot 'fresh_dev' created for quick restore")
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up development environment: {e}")
            return False
    
    def show_quick_stats(self):
        """Show quick development statistics"""
        try:
            with self.app.app_context():
                users_count = User.query.count()
                recipes_count = Recipe.query.count()
                cookbooks_count = Cookbook.query.count()
                ingredients_count = Ingredient.query.count()
                
                print("📊 Quick Stats:")
                print(f"   Users: {users_count}")
                print(f"   Recipes: {recipes_count}")
                print(f"   Cookbooks: {cookbooks_count}")
                print(f"   Ingredients: {ingredients_count}")
                
                if users_count > 0:
                    print("\n👥 Users:")
                    users = User.query.all()
                    for user in users:
                        print(f"   {user.username} ({user.role.value})")
                
        except Exception as e:
            print(f"❌ Error getting stats: {e}")


def main():
    """Command line interface for development helpers"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cookbook Creator Development Helpers")
    parser.add_argument("--env", default="development",
                       choices=["development", "testing"],
                       help="Environment configuration")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Quick reset
    subparsers.add_parser("quick-reset", help="Quick database reset with sample data")
    
    # Create test user
    user_parser = subparsers.add_parser("create-user", help="Create test user")
    user_parser.add_argument("username", help="Username")
    user_parser.add_argument("--role", default="user", choices=["user", "admin"],
                           help="User role")
    user_parser.add_argument("--password", default="test123", help="Password")
    
    # Create datasets
    subparsers.add_parser("minimal", help="Create minimal dataset")
    
    perf_parser = subparsers.add_parser("performance", help="Create performance dataset")
    perf_parser.add_argument("--count", type=int, default=100, help="Number of recipes")
    
    # Snapshots
    snap_parser = subparsers.add_parser("snapshot", help="Create database snapshot")
    snap_parser.add_argument("name", nargs="?", help="Snapshot name")
    
    restore_parser = subparsers.add_parser("restore", help="Restore from snapshot")
    restore_parser.add_argument("name", help="Snapshot name")
    
    subparsers.add_parser("list-snapshots", help="List available snapshots")
    
    # Setup
    subparsers.add_parser("setup", help="Setup fresh development environment")
    
    # Stats
    subparsers.add_parser("stats", help="Show quick statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create development helpers
    dev_helpers = DevelopmentHelpers(args.env)
    
    # Execute command
    if args.command == "quick-reset":
        dev_helpers.quick_reset()
    elif args.command == "create-user":
        role = UserRole.ADMIN if args.role == "admin" else UserRole.USER
        dev_helpers.create_test_user(args.username, role, args.password)
    elif args.command == "minimal":
        dev_helpers.create_minimal_dataset()
    elif args.command == "performance":
        dev_helpers.create_performance_dataset(args.count)
    elif args.command == "snapshot":
        dev_helpers.create_snapshot(args.name)
    elif args.command == "restore":
        dev_helpers.restore_snapshot(args.name)
    elif args.command == "list-snapshots":
        snapshots = dev_helpers.list_snapshots()
        print(f"📸 Available snapshots ({len(snapshots)}):")
        for snapshot in snapshots:
            print(f"   {snapshot}")
    elif args.command == "setup":
        dev_helpers.setup_fresh_dev_environment()
    elif args.command == "stats":
        dev_helpers.show_quick_stats()


if __name__ == "__main__":
    main()
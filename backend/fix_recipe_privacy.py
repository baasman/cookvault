#!/usr/bin/env python3
"""
Fix recipe privacy settings - ensure all recipes have proper is_public values
"""

import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import from the app
sys.path.append(str(Path(__file__).parent))

from cookbook_db_utils.imports import create_app, db, Recipe

def fix_recipe_privacy():
    """Fix any recipes that might have incorrect privacy settings."""
    app = create_app('development')
    
    with app.app_context():
        try:
            # Count recipes that need fixing
            recipes_to_fix = Recipe.query.filter(Recipe.is_public.is_(None)).all()
            print(f"Found {len(recipes_to_fix)} recipes with NULL is_public values")
            
            # Fix NULL values to False (private by default)
            for recipe in recipes_to_fix:
                recipe.is_public = False
                print(f"Fixed recipe {recipe.id}: {recipe.title}")
            
            # Also check for any recipes that might have been incorrectly set to public
            # For safety, we'll list them but not auto-fix
            public_recipes = Recipe.query.filter(Recipe.is_public == True).all()
            print(f"\nCurrent public recipes ({len(public_recipes)}):")
            for recipe in public_recipes:
                print(f"  - Recipe {recipe.id}: {recipe.title} (user_id: {recipe.user_id})")
            
            # Commit the fixes
            db.session.commit()
            print(f"\n✅ Fixed {len(recipes_to_fix)} recipes")
            
        except Exception as e:
            print(f"❌ Error fixing recipes: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_recipe_privacy()
#!/usr/bin/env python3
"""
Fix user collections - ensure all user's own recipes are in their collection
"""

import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import from the app
sys.path.append(str(Path(__file__).parent))

from cookbook_db_utils.imports import create_app, db, Recipe, UserRecipeCollection

def fix_user_collections():
    """Add all user's own recipes to their collections if not already there."""
    app = create_app('development')
    
    with app.app_context():
        try:
            # Get all recipes that have a user_id (user's own recipes)
            user_recipes = Recipe.query.filter(Recipe.user_id.isnot(None)).all()
            print(f"Found {len(user_recipes)} user-owned recipes")
            
            added_count = 0
            
            for recipe in user_recipes:
                # Check if this recipe is already in the user's collection
                existing = UserRecipeCollection.query.filter_by(
                    user_id=recipe.user_id,
                    recipe_id=recipe.id
                ).first()
                
                if not existing:
                    # Add to collection
                    collection_item = UserRecipeCollection(
                        user_id=recipe.user_id,
                        recipe_id=recipe.id
                    )
                    db.session.add(collection_item)
                    added_count += 1
                    print(f"Added recipe '{recipe.title}' to user {recipe.user_id}'s collection")
            
            # Commit all changes
            db.session.commit()
            print(f"\n✅ Successfully added {added_count} recipes to user collections")
            
        except Exception as e:
            print(f"❌ Error fixing user collections: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_user_collections()
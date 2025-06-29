"""
Common imports module for cookbook database utilities

This module handles the import of Flask app components with fallback path handling.
"""

import sys
from pathlib import Path

def setup_app_imports():
    """Set up imports for Flask app components with fallback path handling"""
    try:
        from app import create_app, db
        from app.models import (
            User, UserSession, Password, Recipe, Cookbook, Ingredient,
            Tag, Instruction, RecipeImage, ProcessingJob,
            UserRole, UserStatus, ProcessingStatus, recipe_ingredients
        )
        return create_app, db, {
            'User': User,
            'UserSession': UserSession, 
            'Password': Password,
            'Recipe': Recipe,
            'Cookbook': Cookbook,
            'Ingredient': Ingredient,
            'Tag': Tag,
            'Instruction': Instruction,
            'RecipeImage': RecipeImage,
            'ProcessingJob': ProcessingJob,
            'UserRole': UserRole,
            'UserStatus': UserStatus,
            'ProcessingStatus': ProcessingStatus,
            'recipe_ingredients': recipe_ingredients,
        }
    except ImportError:
        # When running as standalone package, we need to set up the path
        current_dir = Path(__file__).parent
        app_dir = current_dir.parent
        if str(app_dir) not in sys.path:
            sys.path.insert(0, str(app_dir))
        
        try:
            from app import create_app, db
            from app.models import (
                User, UserSession, Password, Recipe, Cookbook, Ingredient,
                Tag, Instruction, RecipeImage, ProcessingJob,
                UserRole, UserStatus, ProcessingStatus, recipe_ingredients
            )
            return create_app, db, {
                'User': User,
                'UserSession': UserSession,
                'Password': Password, 
                'Recipe': Recipe,
                'Cookbook': Cookbook,
                'Ingredient': Ingredient,
                'Tag': Tag,
                'Instruction': Instruction,
                'RecipeImage': RecipeImage,
                'ProcessingJob': ProcessingJob,
                'UserRole': UserRole,
                'UserStatus': UserStatus,
                'ProcessingStatus': ProcessingStatus,
                'recipe_ingredients': recipe_ingredients,
            }
        except ImportError as e:
            raise ImportError(
                f"Cannot import Flask app components. Make sure you're running from the "
                f"correct directory or the app module is available. Error: {e}"
            ) from e

# Initialize imports when module is loaded
create_app, db, models = setup_app_imports()

# Export commonly used models
User = models['User']
UserSession = models['UserSession']
Password = models['Password']
Recipe = models['Recipe']
Cookbook = models['Cookbook']
Ingredient = models['Ingredient']
Tag = models['Tag']
Instruction = models['Instruction']
RecipeImage = models['RecipeImage']
ProcessingJob = models['ProcessingJob']
UserRole = models['UserRole']
UserStatus = models['UserStatus']
ProcessingStatus = models['ProcessingStatus']
recipe_ingredients = models['recipe_ingredients']

__all__ = [
    'create_app', 'db', 'models',
    'User', 'UserSession', 'Password', 'Recipe', 'Cookbook', 'Ingredient',
    'Tag', 'Instruction', 'RecipeImage', 'ProcessingJob',
    'UserRole', 'UserStatus', 'ProcessingStatus', 'recipe_ingredients'
]
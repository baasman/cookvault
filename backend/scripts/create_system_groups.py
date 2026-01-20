#!/usr/bin/env python
"""
Script to create system recipe groups for all existing users.

Run this script after applying the database migration that adds
is_system and system_type columns to the recipe_group table.

Usage:
    cd backend && uv run python scripts/create_system_groups.py
"""
import sys
import traceback
from pathlib import Path

# Add the parent directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import RecipeGroup
from app.models.user import User


SYSTEM_GROUPS = {
    'have_made': {
        'name': 'Have Made',
        'description': 'Recipes you have cooked before'
    },
    'want_to_make': {
        'name': 'Want to Make',
        'description': 'Recipes you want to try'
    }
}


def create_system_groups_for_user(user_id: int) -> dict:
    """Create system groups for a specific user."""
    created = {}

    for system_type, config in SYSTEM_GROUPS.items():
        # Check if system group already exists
        existing = RecipeGroup.query.filter_by(
            user_id=user_id,
            system_type=system_type,
            is_system=True
        ).first()

        if existing:
            print(f"  - '{config['name']}' already exists (id={existing.id})")
            created[system_type] = existing
        else:
            # Create the system group
            group = RecipeGroup(
                name=config['name'],
                description=config['description'],
                user_id=user_id,
                is_private=True,
                is_system=True,
                system_type=system_type
            )
            db.session.add(group)
            created[system_type] = group
            print(f"  - Created '{config['name']}'")

    return created


def main():
    """Main function to create system groups for all users."""
    app = create_app()

    with app.app_context():
        print("Creating system recipe groups for all users...")
        print("-" * 50)

        try:
            # Get all users
            users = User.query.all()
            total_users = len(users)
            created_count = 0
            skipped_count = 0

            print(f"Found {total_users} users")
            print()

            for i, user in enumerate(users, 1):
                print(f"[{i}/{total_users}] Processing user: {user.username} (id={user.id})")

                try:
                    created = create_system_groups_for_user(user.id)
                    db.session.commit()
                    created_count += 1
                except Exception as e:
                    db.session.rollback()
                    print(f"  ERROR: Failed to create groups for user {user.id}: {e}")
                    traceback.print_exc()
                    skipped_count += 1

            print()
            print("-" * 50)
            print(f"Done! Created system groups for {created_count} users.")
            if skipped_count > 0:
                print(f"Skipped {skipped_count} users due to errors.")

        except Exception as e:
            print(f"Fatal error: {e}")
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()

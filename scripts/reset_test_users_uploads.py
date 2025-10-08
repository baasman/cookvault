#!/usr/bin/env python3
"""
Reset upload counts for ONLY test users defined in test_users.json
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app import create_app, db
from app.models import User
from app.models.payment import Subscription


def reset_test_users_upload_counts():
    """Reset upload counts for test users only"""

    # Load test users from JSON
    test_users_file = Path(__file__).parent / "test_users.json"
    with open(test_users_file, 'r') as f:
        data = json.load(f)

    # Get all test usernames
    test_usernames = [user['username'] for user in data['users']]
    if 'admin_users' in data:
        test_usernames.extend([user['username'] for user in data['admin_users']])

    print(f"Found {len(test_usernames)} test users to reset")

    # Create Flask app context
    app = create_app()

    with app.app_context():
        reset_count = 0

        for username in test_usernames:
            # Find user
            user = User.query.filter_by(username=username).first()
            if not user:
                print(f"  ⚠️  User '{username}' not found in database")
                continue

            # Get subscription
            subscription = Subscription.query.filter_by(user_id=user.id).first()
            if not subscription:
                print(f"  ⚠️  No subscription for '{username}'")
                continue

            # Check current count
            current_count = subscription.monthly_upload_count

            if current_count > 0:
                # Reset the count
                subscription.reset_monthly_uploads()
                print(f"  ✅ Reset '{username}': {current_count} → 0")
                reset_count += 1
            else:
                print(f"  - '{username}' already at 0")

        # Commit all changes
        db.session.commit()

        print(f"\n✅ Successfully reset {reset_count} test user upload counts")
        print(f"📊 Total test users processed: {len(test_usernames)}")


if __name__ == "__main__":
    reset_test_users_upload_counts()
#!/usr/bin/env python3
"""
Check subscription status of test users and reset their upload counts
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app import create_app, db
from app.models import User
from app.models.payment import Subscription, SubscriptionTier, SubscriptionStatus


def check_and_reset_test_users():
    """Check subscription status and reset upload counts for test users"""

    # Load test users from JSON
    test_users_file = Path(__file__).parent / "test_users.json"
    with open(test_users_file, 'r') as f:
        data = json.load(f)

    # Get all test usernames
    test_usernames = [user['username'] for user in data['users']]
    if 'admin_users' in data:
        test_usernames.extend([user['username'] for user in data['admin_users']])

    print(f"Checking {len(test_usernames)} test users...")
    print("=" * 80)

    # Create Flask app context
    app = create_app()

    with app.app_context():
        for username in test_usernames:
            # Find user
            user = User.query.filter_by(username=username).first()
            if not user:
                print(f"❌ User '{username}' not found in database")
                continue

            # Get subscription
            subscription = Subscription.query.filter_by(user_id=user.id).first()
            if not subscription:
                print(f"⚠️  '{username}' has NO subscription")
                continue

            # Check status
            is_premium = subscription.is_premium()
            can_upload = subscription.can_upload_recipe()

            status_icon = "✅" if is_premium and can_upload else "❌"
            print(f"{status_icon} {username:20} | "
                  f"Tier: {subscription.tier.value:10} | "
                  f"Status: {subscription.status.value:15} | "
                  f"Uploads: {subscription.monthly_upload_count:3} | "
                  f"Can upload: {'YES' if can_upload else 'NO'}")

            # Reset upload count if needed
            if subscription.monthly_upload_count > 0:
                subscription.monthly_upload_count = 0
                print(f"    → Reset upload count to 0")

        # Commit changes
        db.session.commit()
        print("=" * 80)
        print("✅ Upload counts reset for all users")


if __name__ == "__main__":
    check_and_reset_test_users()

#!/usr/bin/env python3
"""
Upgrade all test users to premium tier for unlimited uploads during load testing
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app import create_app, db
from app.models import User
from app.models.payment import Subscription, SubscriptionTier, SubscriptionStatus


def upgrade_all_test_users_to_premium():
    """Upgrade all test users to premium tier"""

    # Load test users from JSON
    test_users_file = Path(__file__).parent / "test_users.json"
    with open(test_users_file, 'r') as f:
        data = json.load(f)

    # Get all test usernames
    test_usernames = [user['username'] for user in data['users']]
    if 'admin_users' in data:
        test_usernames.extend([user['username'] for user in data['admin_users']])

    print(f"Found {len(test_usernames)} test users to upgrade to premium")

    # Create Flask app context
    app = create_app()

    with app.app_context():
        upgraded_count = 0
        already_premium = 0

        for username in test_usernames:
            # Find user
            user = User.query.filter_by(username=username).first()
            if not user:
                print(f"  ⚠️  User '{username}' not found in database")
                continue

            # Get or create subscription
            subscription = Subscription.query.filter_by(user_id=user.id).first()
            if not subscription:
                # Create a new subscription
                subscription = Subscription(
                    user_id=user.id,
                    tier=SubscriptionTier.PREMIUM,
                    status=SubscriptionStatus.ACTIVE,  # Set to ACTIVE
                    stripe_subscription_id=f"test_sub_{user.id}",
                    stripe_customer_id=f"test_cust_{user.id}",
                    monthly_upload_count=0,
                    upload_count_reset_date=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year
                )
                db.session.add(subscription)
                print(f"  ✅ Created ACTIVE premium subscription for '{username}'")
                upgraded_count += 1
            elif subscription.tier != SubscriptionTier.PREMIUM or subscription.status != SubscriptionStatus.ACTIVE:
                # Upgrade existing subscription
                old_tier = subscription.tier
                old_status = subscription.status
                subscription.tier = SubscriptionTier.PREMIUM
                subscription.status = SubscriptionStatus.ACTIVE  # Set to ACTIVE
                subscription.monthly_upload_count = 0  # Reset count
                subscription.upload_count_reset_date = datetime.utcnow()
                subscription.expires_at = datetime.utcnow() + timedelta(days=365)
                print(f"  ✅ Upgraded '{username}': {old_tier.value}/{old_status.value} → PREMIUM/ACTIVE")
                upgraded_count += 1
            else:
                print(f"  - '{username}' already PREMIUM/ACTIVE")
                already_premium += 1
                # Still reset their upload count and ensure ACTIVE status
                subscription.monthly_upload_count = 0
                subscription.status = SubscriptionStatus.ACTIVE

        # Commit all changes
        db.session.commit()

        print(f"\n✅ Successfully upgraded {upgraded_count} test users to premium")
        print(f"📊 Already premium: {already_premium}")
        print(f"📊 Total test users processed: {len(test_usernames)}")
        print("\nAll test users now have unlimited uploads!")


if __name__ == "__main__":
    upgrade_all_test_users_to_premium()
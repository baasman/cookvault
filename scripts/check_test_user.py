#!/usr/bin/env python3
"""Debug script to check test user subscription status"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app import create_app, db
from app.models import User
from app.models.payment import Subscription

app = create_app()

with app.app_context():
    # Check specific user
    username = sys.argv[1] if len(sys.argv) > 1 else 'loadtest_burst2'

    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"User '{username}' not found!")
        exit(1)

    subscription = Subscription.query.filter_by(user_id=user.id).first()
    if not subscription:
        print(f"No subscription found for '{username}'!")
        exit(1)

    print(f"User: {user.username}")
    print(f"  User ID: {user.id}")
    print(f"  Subscription Tier: {subscription.tier}")
    print(f"  Subscription Status: {subscription.status}")
    print(f"  Monthly Upload Count: {subscription.monthly_upload_count}")
    print(f"  Is Premium (check): {subscription.is_premium()}")
    print(f"  Can Upload Recipe: {subscription.can_upload_recipe()}")
    print(f"  Remaining Uploads: {subscription.get_remaining_uploads()}")

    # Also check via user methods
    print(f"\nVia User methods:")
    print(f"  Is Premium: {user.is_premium()}")
    print(f"  Can Upload: {user.can_upload_recipe()}")
    print(f"  Remaining: {user.get_remaining_uploads()}")
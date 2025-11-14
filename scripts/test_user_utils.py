#!/usr/bin/env python3
"""
Consolidated test user utilities for load testing.

This module provides centralized functions for managing test users, subscriptions,
and upload counters. All test user management code should import from here to
avoid duplication and ensure consistency.

Functions:
    - load_test_users(): Load test user configuration from JSON
    - get_all_test_usernames(): Get list of all test user names
    - upgrade_test_users_to_premium(): Upgrade users to premium tier
    - reset_test_user_upload_counts(): Reset upload counters
    - print_test_user_status(): Display test user status information
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# Module-level configuration
BASE_DIR = Path(__file__).parent.parent
USERS_FILE = BASE_DIR / "scripts" / "test_users.json"


def load_test_users() -> Dict:
    """
    Load test user configuration from JSON file.

    Returns:
        Dictionary containing 'users' and 'admin_users' lists

    Raises:
        FileNotFoundError: If test_users.json doesn't exist
        json.JSONDecodeError: If JSON file is malformed
    """
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_test_usernames() -> List[str]:
    """
    Get list of all test usernames (regular + admin).

    Returns:
        List of username strings
    """
    config = load_test_users()
    usernames = []

    for user in config.get("users", []):
        usernames.append(user["username"])

    for user in config.get("admin_users", []):
        usernames.append(user["username"])

    return usernames


def upgrade_test_users_to_premium():
    """
    Upgrade all test users to premium tier with active subscriptions.

    This function requires direct database access and will:
    - Find all test users from test_users.json
    - Create or update their Subscription to PREMIUM tier
    - Set subscription as ACTIVE with 365-day validity

    Note: Requires backend modules to be importable.
          Run from project root for best results.

    Raises:
        ImportError: If backend modules cannot be imported
        Exception: If database operations fail
    """
    print("💎 Upgrading test users to premium tier...")

    # Add backend to path for imports
    sys.path.insert(0, str(BASE_DIR / 'backend'))

    try:
        from app import create_app, db
        from app.models.user import User
        from app.models.payment import Subscription, SubscriptionTier, SubscriptionStatus

        app = create_app()
        with app.app_context():
            config = load_test_users()
            all_test_users = config["users"] + config.get("admin_users", [])

            upgraded_count = 0
            for user_data in all_test_users:
                user = User.query.filter_by(username=user_data["username"]).first()

                if not user:
                    print(f"   ⚠️  User not found: {user_data['username']}")
                    continue

                subscription = Subscription.query.filter_by(user_id=user.id).first()

                if not subscription:
                    # Create new premium subscription
                    subscription = Subscription(
                        user_id=user.id,
                        tier=SubscriptionTier.PREMIUM,
                        status=SubscriptionStatus.ACTIVE,
                        current_period_start=datetime.utcnow(),
                        current_period_end=datetime.utcnow() + timedelta(days=365)
                    )
                    db.session.add(subscription)
                    print(f"   ✅ Created premium subscription: {user.username}")
                else:
                    # Update existing subscription to premium
                    subscription.tier = SubscriptionTier.PREMIUM
                    subscription.status = SubscriptionStatus.ACTIVE
                    subscription.current_period_end = datetime.utcnow() + timedelta(days=365)
                    print(f"   ✅ Updated to premium: {user.username}")

                upgraded_count += 1

            db.session.commit()
            print(f"\n   💎 Successfully upgraded {upgraded_count} users to premium")
            print("   ✓ All users now have unlimited upload capacity!")
            return upgraded_count

    except ImportError as e:
        print(f"❌ Could not import backend modules: {str(e)}")
        print("   Make sure to run from project root directory")
        raise
    except Exception as e:
        print(f"❌ Error upgrading users to premium: {str(e)}")
        raise


def reset_test_user_upload_counts():
    """
    Reset upload counters for all test users.

    Note: Since test users should be premium tier, they have unlimited uploads.
          This function is primarily for cleanup and ensuring consistent state.

    Raises:
        ImportError: If backend modules cannot be imported
        Exception: If database operations fail
    """
    print("🔄 Resetting test user upload counts...")

    # Add backend to path for imports
    sys.path.insert(0, str(BASE_DIR / 'backend'))

    try:
        from app import create_app, db
        from app.models.user import User

        app = create_app()
        with app.app_context():
            usernames = get_all_test_usernames()

            reset_count = 0
            for username in usernames:
                user = User.query.filter_by(username=username).first()
                if user:
                    old_count = user.upload_count
                    user.upload_count = 0

                    if old_count > 0:
                        print(f"   ✅ Reset upload count for {username}: {old_count} → 0")

                    reset_count += 1
                else:
                    print(f"   ⚠️  User not found: {username}")

            db.session.commit()
            print(f"\n   ✓ Reset upload counts for {reset_count} users")
            return reset_count

    except ImportError as e:
        print(f"❌ Could not import backend modules: {str(e)}")
        print("   Make sure to run from project root directory")
        raise
    except Exception as e:
        print(f"❌ Error resetting upload counts: {str(e)}")
        raise


def print_test_user_status():
    """
    Print status and summary information about test users.

    Displays:
    - Count of regular and admin users
    - Sample usernames with their tier
    - Quick verification that users are configured
    """
    print("\n📊 Test User Status:")

    try:
        config = load_test_users()
        regular_users = config.get('users', [])
        admin_users = config.get('admin_users', [])

        print(f"   Regular users: {len(regular_users)}")
        print(f"   Admin users: {len(admin_users)}")

        # Show sample users
        all_users = regular_users + admin_users
        if all_users:
            print(f"\n   Sample users:")
            for user in all_users[:3]:
                tier = user.get('tier', 'free')
                print(f"      - {user['username']} ({tier})")

            if len(all_users) > 3:
                print(f"      ... and {len(all_users) - 3} more")

        print(f"\n   ✓ Total: {len(all_users)} test users configured")

    except FileNotFoundError:
        print("   ❌ test_users.json not found!")
    except Exception as e:
        print(f"   ❌ Error loading user status: {str(e)}")


def verify_test_user_subscriptions():
    """
    Verify that all test users have active premium subscriptions.

    Returns:
        Tuple of (premium_count, total_count)
    """
    print("\n🔍 Verifying test user subscriptions...")

    # Add backend to path for imports
    sys.path.insert(0, str(BASE_DIR / 'backend'))

    try:
        from app import create_app, db
        from app.models.user import User
        from app.models.payment import Subscription, SubscriptionTier, SubscriptionStatus

        app = create_app()
        with app.app_context():
            usernames = get_all_test_usernames()

            premium_count = 0
            total_count = 0

            for username in usernames:
                user = User.query.filter_by(username=username).first()
                if not user:
                    print(f"   ⚠️  User not found: {username}")
                    continue

                total_count += 1
                subscription = Subscription.query.filter_by(user_id=user.id).first()

                if subscription and subscription.tier == SubscriptionTier.PREMIUM:
                    if subscription.status == SubscriptionStatus.ACTIVE:
                        premium_count += 1
                    else:
                        print(f"   ⚠️  {username}: Premium but status is {subscription.status}")
                else:
                    tier = subscription.tier if subscription else "None"
                    print(f"   ⚠️  {username}: Tier is {tier} (not PREMIUM)")

            print(f"\n   ✓ {premium_count}/{total_count} users have active premium subscriptions")

            if premium_count < total_count:
                print(f"   ⚠️  {total_count - premium_count} users need premium upgrade!")

            return (premium_count, total_count)

    except ImportError as e:
        print(f"❌ Could not import backend modules: {str(e)}")
        raise
    except Exception as e:
        print(f"❌ Error verifying subscriptions: {str(e)}")
        raise


if __name__ == "__main__":
    """
    Command-line interface for test user utilities.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Test user management utilities")
    parser.add_argument(
        "action",
        choices=["status", "upgrade", "reset", "verify"],
        help="Action to perform"
    )

    args = parser.parse_args()

    if args.action == "status":
        print_test_user_status()
    elif args.action == "upgrade":
        upgrade_test_users_to_premium()
    elif args.action == "reset":
        reset_test_user_upload_counts()
    elif args.action == "verify":
        verify_test_user_subscriptions()

#!/usr/bin/env python3
"""
Setup test users for load testing
Creates all test users defined in test_users.json
"""

import json
import sys
from pathlib import Path
import requests
from typing import Dict
import time


class TestUserSetup:
    """Setup test users for load testing"""

    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.base_dir = Path(__file__).parent.parent
        self.users_file = self.base_dir / "scripts" / "test_users.json"
        self.created_users = []
        self.failed_users = []

    def load_user_config(self) -> Dict:
        """Load user configuration from JSON file"""
        with open(self.users_file, 'r') as f:
            return json.load(f)

    def create_user(self, user_data: Dict) -> bool:
        """Create a single user"""
        try:
            # Register user
            response = requests.post(
                f"{self.api_url}/auth/register",
                json={
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "password": user_data["password"],
                    "confirm_password": user_data["password"]
                }
            )

            if response.status_code == 201:
                print(f"✅ Created user: {user_data['username']}")
                self.created_users.append(user_data["username"])

                # If premium user, would need to upgrade subscription
                # This would require additional API endpoints or database access
                if user_data.get("tier") == "premium":
                    print(f"   ℹ️  Note: {user_data['username']} needs premium subscription setup")

                return True
            elif response.status_code == 409:
                print(f"⚠️  User already exists: {user_data['username']}")
                return True
            else:
                print(f"❌ Failed to create user {user_data['username']}: {response.status_code}")
                print(f"   Response: {response.text}")
                self.failed_users.append(user_data["username"])
                return False

        except Exception as e:
            print(f"❌ Error creating user {user_data['username']}: {str(e)}")
            self.failed_users.append(user_data["username"])
            return False

    def verify_user_login(self, user_data: Dict) -> bool:
        """Verify that a user can login"""
        try:
            response = requests.post(
                f"{self.api_url}/auth/login",
                json={
                    "login": user_data["username"],
                    "password": user_data["password"]
                }
            )

            if response.status_code == 200:
                print(f"✅ Login verified for: {user_data['username']}")
                return True
            else:
                print(f"❌ Login failed for {user_data['username']}: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error verifying login for {user_data['username']}: {str(e)}")
            return False

    def upgrade_users_to_premium(self):
        """Upgrade all test users to premium tier for unlimited uploads"""
        print("\n💎 Upgrading test users to premium tier...")

        # This requires direct database access since there's no API endpoint
        # We'll use a simple Python script to update the database
        try:
            # Import database modules
            sys.path.append(str(self.base_dir / 'backend'))
            from app import create_app, db
            from app.models.user import User
            from app.models.payment import Subscription, SubscriptionTier, SubscriptionStatus
            from datetime import datetime, timedelta

            app = create_app()
            with app.app_context():
                # Get all test users
                config = self.load_user_config()
                all_test_users = config["users"] + config.get("admin_users", [])

                upgraded_count = 0
                for user_data in all_test_users:
                    user = User.query.filter_by(username=user_data["username"]).first()
                    if user:
                        # Check if user has a subscription
                        subscription = Subscription.query.filter_by(user_id=user.id).first()

                        if not subscription:
                            # Create premium subscription
                            subscription = Subscription(
                                user_id=user.id,
                                tier=SubscriptionTier.PREMIUM,
                                status=SubscriptionStatus.ACTIVE,
                                current_period_start=datetime.utcnow(),
                                current_period_end=datetime.utcnow() + timedelta(days=365)
                            )
                            db.session.add(subscription)
                            print(f"   ✅ Created premium subscription for: {user.username}")
                        else:
                            # Update existing subscription to premium
                            subscription.tier = SubscriptionTier.PREMIUM
                            subscription.status = SubscriptionStatus.ACTIVE
                            subscription.current_period_end = datetime.utcnow() + timedelta(days=365)
                            print(f"   ✅ Updated to premium: {user.username}")

                        upgraded_count += 1

                db.session.commit()
                print(f"\n   💎 Upgraded {upgraded_count} users to premium tier")
                print("   Users now have unlimited upload capacity!")

        except ImportError as e:
            print("⚠️  Could not import backend modules for direct DB access")
            print("   To upgrade users to premium, you'll need to:")
            print("   1. Run this script from the project root, OR")
            print("   2. Manually update subscriptions in the database")
            print(f"   Error: {str(e)}")
        except Exception as e:
            print(f"⚠️  Error upgrading users to premium: {str(e)}")

    def setup_all_users(self):
        """Create all test users"""
        print("=" * 60)
        print("🚀 Setting up test users for load testing")
        print(f"   Target: {self.base_url}")
        print("=" * 60)

        # Load user configuration
        config = self.load_user_config()

        # Create regular users
        print("\n📝 Creating regular test users...")
        for user in config["users"]:
            self.create_user(user)
            time.sleep(0.5)  # Small delay to avoid rate limiting

        # Create admin users
        print("\n👑 Creating admin test users...")
        for user in config["admin_users"]:
            self.create_user(user)
            time.sleep(0.5)

        # Summary
        print("\n" + "=" * 60)
        print("📊 Setup Summary:")
        print(f"   ✅ Successfully created: {len(self.created_users)} users")
        print(f"   ❌ Failed: {len(self.failed_users)} users")

        if self.failed_users:
            print(f"\n   Failed users: {', '.join(self.failed_users)}")

        # Verify logins for created users
        print("\n🔐 Verifying user logins...")
        config = self.load_user_config()
        verified = 0
        for user in config["users"][:5]:  # Test first 5 users
            if self.verify_user_login(user):
                verified += 1

        print(f"\n   Verified {verified}/5 test logins")

        # Upgrade all users to premium for unlimited uploads
        self.upgrade_users_to_premium()

        print("\n✨ Test user setup complete!")
        print("=" * 60)

    def cleanup_test_users(self):
        """Remove test users (requires admin access or direct DB access)"""
        print("\n🧹 Cleanup function placeholder")
        print("   Note: Implement user deletion if needed for cleanup")
        # This would require admin endpoints or direct database access


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Setup test users for load testing")
    parser.add_argument(
        "--url",
        default="http://localhost:5001",
        help="Base URL of the application (default: http://localhost:5001)"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove test users instead of creating them"
    )
    parser.add_argument(
        "--upgrade-premium",
        action="store_true",
        help="Only upgrade existing test users to premium tier"
    )

    args = parser.parse_args()

    setup = TestUserSetup(base_url=args.url)

    if args.cleanup:
        setup.cleanup_test_users()
    elif args.upgrade_premium:
        setup.upgrade_users_to_premium()
        print("\n✨ Premium upgrade complete!")
    else:
        setup.setup_all_users()


if __name__ == "__main__":
    main()

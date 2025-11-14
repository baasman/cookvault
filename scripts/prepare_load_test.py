#!/usr/bin/env python3
"""
Prepare test users for load testing.

This script ensures all test users are ready for load testing by:
1. Upgrading all users to premium tier (unlimited uploads)
2. Resetting upload counters to 0
3. Verifying subscription status

Run this before starting load tests to ensure consistent test state.
"""

import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import consolidated test user utilities
from test_user_utils import (
    upgrade_test_users_to_premium,
    reset_test_user_upload_counts,
    print_test_user_status,
    verify_test_user_subscriptions
)


def main():
    """Main entry point for load test preparation"""
    print("=" * 60)
    print("🚀 PREPARING FOR LOAD TEST")
    print("=" * 60)

    try:
        # Step 1: Upgrade all test users to premium
        print("\n📝 Step 1: Upgrading all test users to premium...")
        upgrade_test_users_to_premium()

        # Step 2: Reset upload counts
        print("\n📝 Step 2: Resetting upload counts...")
        reset_test_user_upload_counts()

        # Step 3: Verify subscription status
        print("\n📝 Step 3: Verifying subscription status...")
        premium_count, total_count = verify_test_user_subscriptions()

        # Step 4: Display status
        print_test_user_status()

        # Final summary
        print("\n" + "=" * 60)
        print("✅ LOAD TEST PREPARATION COMPLETE")
        print(f"   - {total_count} test users configured")
        print(f"   - {premium_count} users with active premium status")
        print("   - All upload counts reset to 0")
        print("   - Users ready for unlimited uploads")
        print("=" * 60)

        if premium_count < total_count:
            print("\n⚠️  WARNING: Not all users have premium status!")
            print("   Some users may hit upload limits during testing.")
            return 1

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ LOAD TEST PREPARATION FAILED")
        print(f"   Error: {str(e)}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

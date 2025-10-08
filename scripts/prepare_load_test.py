#!/usr/bin/env python3
"""
Prepare test users for load testing - reset counts and ensure premium status
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app import create_app, db

# Import the functions directly
import upgrade_test_users_to_premium
import reset_test_users_uploads

def main():
    print("=" * 60)
    print("PREPARING FOR LOAD TEST")
    print("=" * 60)

    print("\n1. Upgrading all test users to premium...")
    upgrade_test_users_to_premium.upgrade_all_test_users_to_premium()

    print("\n2. Resetting upload counts...")
    reset_test_users_uploads.reset_test_users_upload_counts()

    print("\n" + "=" * 60)
    print("✅ LOAD TEST PREPARATION COMPLETE")
    print("All test users are PREMIUM with ACTIVE status")
    print("All upload counts have been reset to 0")
    print("=" * 60)

if __name__ == "__main__":
    main()
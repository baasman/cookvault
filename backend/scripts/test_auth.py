#!/usr/bin/env python3
"""
Test script for authentication endpoints using the Flask debug instance.
This script demonstrates how to test user registration, login, and logout.
"""

import json
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import User, UserSession, UserRole, UserStatus


def test_user_registration():
    """Test user registration endpoint."""
    print("Testing user registration...")
    app = create_app("testing")

    with app.app_context():
        # Create all database tables
        db.create_all()
        client = app.test_client()

        # Test data for registration
        test_users = [
            {
                "username": "testuser1",
                "email": "test1@example.com",
                "password": "password123",
                "first_name": "Test",
                "last_name": "User",
            },
            {
                "username": "testuser2",
                "email": "test2@example.com",
                "password": "mypassword456",
            },
        ]

        for i, user_data in enumerate(test_users, 1):
            print(f"\nRegistering user {i}: {user_data['username']}")

            response = client.post(
                "/api/auth/register",
                data=json.dumps(user_data),
                content_type="application/json",
            )

            print(f"Registration response status: {response.status_code}")
            response_data = response.get_json()
            print(f"Response data: {json.dumps(response_data, indent=2)}")

            if response.status_code == 201:
                print(f"✅ User {user_data['username']} registered successfully!")
                print(f"   User ID: {response_data['user']['id']}")
                print(f"   Session token: {response_data['session_token'][:20]}...")
            else:
                print(
                    f"❌ Registration failed: {response_data.get('error', 'Unknown error')}"
                )

        # Test duplicate registration
        print(f"\nTesting duplicate registration...")
        response = client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "username": "testuser1",  # Duplicate username
                    "email": "duplicate@example.com",
                    "password": "password123",
                }
            ),
            content_type="application/json",
        )
        print(f"Duplicate username response: {response.status_code}")
        if response.status_code == 409:
            print("✅ Correctly rejected duplicate username")
        else:
            print("❌ Should have rejected duplicate username")

        # Test invalid data
        print(f"\nTesting invalid registration data...")
        invalid_tests = [
            {
                "username": "",
                "email": "test@example.com",
                "password": "password123",
            },  # Empty username
            {
                "username": "validuser",
                "email": "",
                "password": "password123",
            },  # Empty email
            {
                "username": "validuser",
                "email": "test@example.com",
                "password": "",
            },  # Empty password
            {
                "username": "validuser",
                "email": "test@example.com",
                "password": "123",
            },  # Short password
            {
                "username": "ab",
                "email": "test@example.com",
                "password": "password123",
            },  # Short username
        ]

        for test_data in invalid_tests:
            response = client.post(
                "/api/auth/register",
                data=json.dumps(test_data),
                content_type="application/json",
            )
            if response.status_code == 400:
                print(f"✅ Correctly rejected invalid data: {test_data}")
            else:
                print(f"❌ Should have rejected: {test_data}")


def test_user_login():
    """Test user login endpoint."""
    print("\n" + "=" * 50)
    print("Testing user login...")
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        client = app.test_client()

        # First register a user
        user_data = {
            "username": "logintest",
            "email": "logintest@example.com",
            "password": "mypassword123",
            "first_name": "Login",
            "last_name": "Test",
        }

        reg_response = client.post(
            "/api/auth/register",
            data=json.dumps(user_data),
            content_type="application/json",
        )

        if reg_response.status_code != 201:
            print("❌ Failed to register test user for login test")
            return

        print("✅ Test user registered for login testing")

        # Test login with username
        print("\nTesting login with username...")
        login_response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"login": user_data["username"], "password": user_data["password"]}
            ),
            content_type="application/json",
        )

        print(f"Login response status: {login_response.status_code}")
        login_data = login_response.get_json()
        print(f"Login response: {json.dumps(login_data, indent=2)}")

        if login_response.status_code == 200:
            print("✅ Login with username successful!")
            session_token = login_data.get("session_token")
            print(f"   Session token: {session_token[:20]}...")
        else:
            print(f"❌ Login failed: {login_data.get('error', 'Unknown error')}")
            return

        # Test login with email
        print("\nTesting login with email...")
        login_response2 = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"login": user_data["email"], "password": user_data["password"]}
            ),
            content_type="application/json",
        )

        if login_response2.status_code == 200:
            print("✅ Login with email successful!")
        else:
            print(f"❌ Login with email failed: {login_response2.get_json()}")

        # Test wrong password
        print("\nTesting login with wrong password...")
        wrong_pass_response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"login": user_data["username"], "password": "wrongpassword"}
            ),
            content_type="application/json",
        )

        if wrong_pass_response.status_code == 401:
            print("✅ Correctly rejected wrong password")
        else:
            print(
                f"❌ Should have rejected wrong password: {wrong_pass_response.get_json()}"
            )

        # Test non-existent user
        print("\nTesting login with non-existent user...")
        nonexist_response = client.post(
            "/api/auth/login",
            data=json.dumps({"login": "nonexistentuser", "password": "password123"}),
            content_type="application/json",
        )

        if nonexist_response.status_code == 401:
            print("✅ Correctly rejected non-existent user")
        else:
            print(
                f"❌ Should have rejected non-existent user: {nonexist_response.get_json()}"
            )


def test_authenticated_endpoints():
    """Test endpoints that require authentication."""
    print("\n" + "=" * 50)
    print("Testing authenticated endpoints...")
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        client = app.test_client()

        # Register and login a user
        user_data = {
            "username": "authtest",
            "email": "authtest@example.com",
            "password": "mypassword123",
        }

        # Register
        reg_response = client.post(
            "/api/auth/register",
            data=json.dumps(user_data),
            content_type="application/json",
        )

        if reg_response.status_code != 201:
            print("❌ Failed to register test user")
            return

        # Login to get session
        login_response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"login": user_data["username"], "password": user_data["password"]}
            ),
            content_type="application/json",
        )

        if login_response.status_code != 200:
            print("❌ Failed to login test user")
            return

        # Test /auth/me endpoint
        print("\nTesting /auth/me endpoint...")
        me_response = client.get("/api/auth/me")

        print(f"Auth/me response status: {me_response.status_code}")
        if me_response.status_code == 200:
            me_data = me_response.get_json()
            print("✅ Successfully got current user info:")
            print(f"   Username: {me_data['user']['username']}")
            print(f"   Email: {me_data['user']['email']}")
            print(f"   Role: {me_data['user']['role']}")
        else:
            print(f"❌ Failed to get user info: {me_response.get_json()}")

        # Test /auth/sessions endpoint
        print("\nTesting /auth/sessions endpoint...")
        sessions_response = client.get("/api/auth/sessions")

        if sessions_response.status_code == 200:
            sessions_data = sessions_response.get_json()
            print(
                f"✅ Got user sessions: {len(sessions_data['sessions'])} active sessions"
            )
            if sessions_data["sessions"]:
                session = sessions_data["sessions"][0]
                print(f"   Session ID: {session['id']}")
                print(f"   Created: {session['created_at']}")
        else:
            print(f"❌ Failed to get sessions: {sessions_response.get_json()}")

        # Test change password
        print("\nTesting password change...")
        change_pass_response = client.post(
            "/api/auth/change-password",
            data=json.dumps(
                {
                    "current_password": user_data["password"],
                    "new_password": "newpassword123",
                }
            ),
            content_type="application/json",
        )

        if change_pass_response.status_code == 200:
            print("✅ Password changed successfully")

            # Test login with new password
            new_login_response = client.post(
                "/api/auth/login",
                data=json.dumps(
                    {"login": user_data["username"], "password": "newpassword123"}
                ),
                content_type="application/json",
            )

            if new_login_response.status_code == 200:
                print("✅ Login with new password successful")
            else:
                print("❌ Login with new password failed")
        else:
            print(f"❌ Password change failed: {change_pass_response.get_json()}")


def test_logout():
    """Test user logout endpoint."""
    print("\n" + "=" * 50)
    print("Testing user logout...")
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        client = app.test_client()

        # Register and login a user
        user_data = {
            "username": "logouttest",
            "email": "logouttest@example.com",
            "password": "mypassword123",
        }

        # Register
        client.post(
            "/api/auth/register",
            data=json.dumps(user_data),
            content_type="application/json",
        )

        # Login
        login_response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"login": user_data["username"], "password": user_data["password"]}
            ),
            content_type="application/json",
        )

        if login_response.status_code != 200:
            print("❌ Failed to login for logout test")
            return

        # Verify we're logged in
        me_response = client.get("/api/auth/me")
        if me_response.status_code == 200:
            print("✅ User is logged in")
        else:
            print("❌ User not properly logged in")
            return

        # Test logout
        print("\nTesting logout...")
        logout_response = client.post("/api/auth/logout")

        print(f"Logout response status: {logout_response.status_code}")
        if logout_response.status_code == 200:
            print("✅ Logout successful")

            # Verify we're logged out
            me_response_after = client.get("/api/auth/me")
            if me_response_after.status_code == 401:
                print("✅ User is properly logged out")
            else:
                print("❌ User still appears to be logged in")
        else:
            logout_data = logout_response.get_json()
            print(f"❌ Logout failed: {logout_data.get('error', 'Unknown error')}")


def test_account_security():
    """Test account security features like failed login attempts."""
    print("\n" + "=" * 50)
    print("Testing account security features...")
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        client = app.test_client()

        # Register a user
        user_data = {
            "username": "securitytest",
            "email": "securitytest@example.com",
            "password": "mypassword123",
        }

        client.post(
            "/api/auth/register",
            data=json.dumps(user_data),
            content_type="application/json",
        )

        print("Testing failed login attempts...")

        # Try to login with wrong password multiple times
        for attempt in range(6):  # This should lock the account
            print(f"Failed login attempt {attempt + 1}")
            response = client.post(
                "/api/auth/login",
                data=json.dumps(
                    {"login": user_data["username"], "password": "wrongpassword"}
                ),
                content_type="application/json",
            )

            if attempt < 4:  # First 5 attempts should return 401
                if response.status_code == 401:
                    print(f"   ✅ Attempt {attempt + 1}: Correctly rejected")
                else:
                    print(
                        f"   ❌ Attempt {attempt + 1}: Unexpected status {response.status_code}"
                    )
            elif attempt == 4:  # 5th attempt might lock the account
                print(f"   Status: {response.status_code}")
            else:  # 6th attempt should return 423 (locked)
                if response.status_code == 423:
                    print("   ✅ Account locked after 5 failed attempts")
                else:
                    print(
                        f"   ❌ Expected account lock, got status {response.status_code}"
                    )

        # Try to login with correct password while locked
        print("\nTesting login with correct password while account is locked...")
        response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {
                    "login": user_data["username"],
                    "password": user_data["password"],  # Correct password
                }
            ),
            content_type="application/json",
        )

        if response.status_code == 423:
            print("✅ Correctly prevented login while account is locked")
        else:
            print(f"❌ Should have prevented login, got status {response.status_code}")


def main():
    """Main function to run all authentication tests."""
    print("Starting Flask authentication test script...")
    print("=" * 60)

    try:
        test_user_registration()
        test_user_login()
        test_authenticated_endpoints()
        test_logout()
        test_account_security()

        print("\n" + "=" * 60)
        print("🎉 Authentication test script completed successfully!")
        print("All authentication features are working correctly.")

    except Exception as e:
        print(f"\n❌ Test script failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

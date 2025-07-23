import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional, Tuple

from flask import Response, current_app, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from app import db
from app.api import bp

# Log that this module is being loaded
print(f"Loading auth.py - Blueprint: {bp}")
print("Auth blueprint loaded")
from app.models import User, UserSession, UserRole, UserStatus, Recipe, Cookbook
from sqlalchemy import func


def require_auth(f):
    """Decorator to require authentication for endpoints."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            current_app.logger.warning(f"Authentication failed for {request.endpoint} - No user found in session")
            return jsonify({"error": "Authentication required"}), 401

        if user.is_account_locked():
            return jsonify({"error": "Account is locked"}), 423

        if user.status != UserStatus.ACTIVE:
            return jsonify({"error": "Account is not active"}), 403

        return f(user, *args, **kwargs)

    return decorated_function


def require_admin(f):
    """Decorator to require admin role for endpoints."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401

        if user.role != UserRole.ADMIN:
            return jsonify({"error": "Admin access required"}), 403

        return f(user, *args, **kwargs)

    return decorated_function


def is_admin_user(user: User) -> bool:
    """Check if user has admin role."""
    return user.role == UserRole.ADMIN


def should_apply_user_filter(user: User) -> bool:
    """Determine if user filtering should be applied (False for admins)."""
    return not is_admin_user(user)


def get_current_user() -> Optional[User]:
    """Get the current authenticated user from session."""
    # Log all session data for debugging
    current_app.logger.debug(f"Session data: {dict(session)}")
    current_app.logger.debug(f"Session permanent: {session.permanent}")
    current_app.logger.debug(f"Request cookies: {dict(request.cookies)}")
    
    session_token = session.get("session_token")
    if not session_token:
        current_app.logger.warning("No session token found in session")
        current_app.logger.warning(f"Available session keys: {list(session.keys())}")
        return None

    user_session = UserSession.query.filter_by(
        session_token=session_token, is_active=True
    ).first()

    if not user_session or not user_session.is_valid():
        return None

    # Update last activity
    user_session.last_activity = datetime.utcnow()
    db.session.commit()

    return user_session.user


def create_user_session(user: User, request) -> UserSession:
    """Create a new user session."""
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=30)  # 30 day session

    user_session = UserSession(
        user_id=user.id,
        session_token=session_token,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        expires_at=expires_at,
    )

    current_app.logger.info(f"Adding user session to database for user {user.id}")
    db.session.add(user_session)
    
    current_app.logger.info(f"Committing user session to database")
    db.session.commit()
    
    current_app.logger.info(f"User session committed with ID: {user_session.id}")

    # Set session token in Flask session
    session["session_token"] = session_token
    session.permanent = True
    
    current_app.logger.info(f"Session token set in Flask session: {session_token[:10]}...")
    current_app.logger.info(f"Session permanent: {session.permanent}")
    current_app.logger.info(f"Session contents after setting: {dict(session)}")

    return user_session


@bp.route("/auth/test", methods=["GET", "POST"])
def test_auth() -> Response:
    """Simple test endpoint."""
    current_app.logger.info(f"Test endpoint called with method {request.method}")
    return jsonify({
        "message": "Auth blueprint is working",
        "method": request.method,
        "url": request.url,
        "blueprint": "api.auth"
    })


@bp.route("/auth/debug", methods=["GET"])
def debug_auth() -> Response:
    """Debug endpoint to test API connectivity and session state."""
    current_app.logger.info("Debug endpoint called")
    
    # Get session info
    session_data = dict(session)
    session_token = session.get("session_token")
    user = get_current_user()
    
    debug_info = {
        "message": "Auth API is working",
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "cookies": dict(request.cookies),
        "session_data": session_data,
        "session_permanent": session.permanent,
        "session_token_present": bool(session_token),
        "session_token_preview": session_token[:10] + "..." if session_token else None,
        "user_authenticated": user is not None,
        "user_info": user.to_dict() if user else None,
        "config": {
            "SESSION_COOKIE_SECURE": current_app.config.get("SESSION_COOKIE_SECURE"),
            "SESSION_COOKIE_HTTPONLY": current_app.config.get("SESSION_COOKIE_HTTPONLY"),
            "SESSION_COOKIE_SAMESITE": current_app.config.get("SESSION_COOKIE_SAMESITE"),
            "PERMANENT_SESSION_LIFETIME": current_app.config.get("PERMANENT_SESSION_LIFETIME"),
            "SECRET_KEY_SET": bool(current_app.config.get("SECRET_KEY"))
        }
    }
    
    current_app.logger.info(f"Debug info: {debug_info}")
    return jsonify(debug_info)


@bp.route("/auth/register", methods=["POST"])
def register() -> Tuple[Response, int]:
    """Register a new user account."""
    try:
        current_app.logger.info(f"Registration attempt - Request headers: {dict(request.headers)}")
        current_app.logger.info(f"Registration attempt - Request method: {request.method}")
        current_app.logger.info(f"Registration attempt - Request URL: {request.url}")
        
        data = request.get_json()
        current_app.logger.info(f"Registration attempt - Data received: {bool(data)}")
        
        if data:
            # Log data without password
            safe_data = {k: v for k, v in data.items() if k != 'password'}
            current_app.logger.info(f"Registration attempt - Safe data: {safe_data}")

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["username", "email", "password"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        username = data["username"].strip()
        email = data["email"].strip().lower()
        password = data["password"]

        # Validate username
        if len(username) < 3 or len(username) > 80:
            return (
                jsonify({"error": "Username must be between 3 and 80 characters"}),
                400,
            )

        # Validate email format (basic check)
        if "@" not in email or "." not in email:
            return jsonify({"error": "Invalid email format"}), 400

        # Validate password strength
        if len(password) < 8:
            return (
                jsonify({"error": "Password must be at least 8 characters long"}),
                400,
            )

        # Test database connection and log user count
        current_app.logger.info("Testing database connection before user creation")
        try:
            total_users = User.query.count()
            current_app.logger.info(f"Database connection OK - Total users in database: {total_users}")
        except Exception as db_error:
            current_app.logger.error(f"Database connection error: {str(db_error)}")
            raise

        # Check if user already exists
        current_app.logger.info(f"Checking for existing user with username '{username}' or email '{email}'")
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            if existing_user.username == username:
                return jsonify({"error": "Username already exists"}), 409
            else:
                return jsonify({"error": "Email already exists"}), 409

        # Create new user
        current_app.logger.info(f"Creating user object for: {username}")
        user = User(
            username=username,
            email=email,
            first_name=data.get("first_name", "").strip(),
            last_name=data.get("last_name", "").strip(),
            status=UserStatus.ACTIVE,  # Auto-activate for now
            is_verified=True,  # Skip email verification for now
        )

        current_app.logger.info(f"Setting password for user: {username}")
        user.set_password(password)

        current_app.logger.info(f"Adding user to database session: {username}")
        db.session.add(user)
        
        current_app.logger.info(f"Committing user to database: {username}")
        db.session.commit()
        
        current_app.logger.info(f"User committed with ID: {user.id}")
        
        # Verify user was actually saved by querying it back
        verification_user = User.query.filter_by(username=username).first()
        if verification_user:
            current_app.logger.info(f"✅ User verification successful - found user ID: {verification_user.id}")
        else:
            current_app.logger.error(f"❌ User verification FAILED - user not found in database after commit!")
            raise Exception("User was not saved to database despite successful commit")

        # Create session for the new user
        user_session = create_user_session(user, request)

        current_app.logger.info(f"New user registered successfully: {username} (ID: {user.id})")
        current_app.logger.info(f"Session after registration: {dict(session)}")

        response = jsonify({
            "message": "User registered successfully",
            "user": user.to_dict(),
            "session_token": user_session.session_token,
        })
        
        current_app.logger.info(f"Registration response created - session should be set in cookies")
        return response, 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username or email already exists"}), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration failed: {str(e)}")
        return jsonify({"error": "Registration failed"}), 500


@bp.route("/auth/login", methods=["POST"])
def login() -> Tuple[Response, int]:
    """Authenticate user and create session."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        login_field = data.get("login", "").strip()  # username or email
        password = data.get("password", "")

        if not login_field or not password:
            return jsonify({"error": "Login and password are required"}), 400

        # Find user by username or email
        user = User.query.filter(
            (User.username == login_field) | (User.email == login_field.lower())
        ).first()

        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        # Check if account is locked
        if user.is_account_locked():
            return (
                jsonify({"error": "Account is locked due to too many failed attempts"}),
                423,
            )

        # Check password
        if not user.check_password(password):
            user.increment_failed_login()
            db.session.commit()
            return jsonify({"error": "Invalid credentials"}), 401

        # Check account status
        if user.status != UserStatus.ACTIVE:
            return jsonify({"error": "Account is not active"}), 403

        # Successful login
        user.reset_failed_login()

        # Invalidate any existing sessions for this user
        UserSession.query.filter_by(user_id=user.id, is_active=True).update(
            {"is_active": False}
        )

        # Create new session
        user_session = create_user_session(user, request)
        
        # Store session token in Flask session for subsequent requests
        session["session_token"] = user_session.session_token
        
        current_app.logger.info(f"User logged in: {user.username}")
        current_app.logger.info(f"Session created with token: {user_session.session_token[:10]}...")
        current_app.logger.info(f"Session cookie secure setting: {current_app.config.get('SESSION_COOKIE_SECURE')}")
        current_app.logger.info(f"Session after login: {dict(session)}")

        response = jsonify({
            "message": "Login successful",
            "user": user.to_dict(),
            "session_token": user_session.session_token,
        })
        
        current_app.logger.info(f"Login response created - session should be set in cookies")
        return response, 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Login failed: {str(e)}")
        return jsonify({"error": "Login failed"}), 500


@bp.route("/auth/logout", methods=["POST"])
@require_auth
def logout(current_user: User) -> Tuple[Response, int]:
    """Logout user and invalidate session."""
    try:
        session_token = session.get("session_token")

        if session_token:
            # Invalidate the current session
            user_session = UserSession.query.filter_by(
                session_token=session_token, user_id=current_user.id
            ).first()

            if user_session:
                user_session.invalidate()
                db.session.commit()

        # Clear Flask session
        session.clear()

        current_app.logger.info(f"User logged out: {current_user.username}")

        return jsonify({"message": "Logout successful"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Logout failed: {str(e)}")
        return jsonify({"error": "Logout failed"}), 500


@bp.route("/auth/me", methods=["GET"])
@require_auth
def get_current_user_info(current_user: User) -> Response:
    """Get current user information."""
    return jsonify({"user": current_user.to_dict(include_sensitive=True)})


@bp.route("/auth/status", methods=["GET"])
def get_auth_status() -> Response:
    """Get authentication status without requiring auth (for debugging)."""
    user = get_current_user()
    
    # Also check database state
    try:
        total_users = User.query.count()
        all_usernames = [u.username for u in User.query.all()]
    except Exception as e:
        total_users = "ERROR"
        all_usernames = [f"DB_ERROR: {str(e)}"]
    
    return jsonify({
        "authenticated": user is not None,
        "user": user.to_dict() if user else None,
        "session_token_present": bool(session.get("session_token")),
        "session_keys": list(session.keys()),
        "cookies_present": len(request.cookies) > 0,
        "cookie_keys": list(request.cookies.keys()),
        "database_stats": {
            "total_users": total_users,
            "all_usernames": all_usernames
        }
    })


@bp.route("/auth/cookie-test", methods=["GET", "POST"])
def cookie_test() -> Response:
    """Test cookie setting and retrieval for debugging session issues."""
    if request.method == "POST":
        # Set test values in session
        session["test_value"] = "cookie_test_123"
        session["timestamp"] = datetime.utcnow().isoformat()
        session.permanent = True
        
        current_app.logger.info(f"Cookie test - Setting session values")
        current_app.logger.info(f"Session after setting: {dict(session)}")
        
        response = jsonify({
            "action": "set",
            "session_data": dict(session),
            "config": {
                "SESSION_COOKIE_SECURE": current_app.config.get("SESSION_COOKIE_SECURE"),
                "SESSION_COOKIE_HTTPONLY": current_app.config.get("SESSION_COOKIE_HTTPONLY"),
                "SESSION_COOKIE_SAMESITE": current_app.config.get("SESSION_COOKIE_SAMESITE"),
                "SESSION_COOKIE_DOMAIN": current_app.config.get("SESSION_COOKIE_DOMAIN"),
                "SESSION_COOKIE_PATH": current_app.config.get("SESSION_COOKIE_PATH"),
                "SESSION_COOKIE_NAME": current_app.config.get("SESSION_COOKIE_NAME"),
            }
        })
        
        # Log response headers to see what cookies are being sent
        current_app.logger.info(f"Response headers will include: Set-Cookie with session data")
        
        return response
    
    else:
        # GET - check what we can retrieve
        test_value = session.get("test_value")
        timestamp = session.get("timestamp")
        
        current_app.logger.info(f"Cookie test - Retrieved from session: test_value={test_value}, timestamp={timestamp}")
        current_app.logger.info(f"Current session data: {dict(session)}")
        current_app.logger.info(f"Request cookies: {dict(request.cookies)}")
        
        return jsonify({
            "action": "get",
            "test_value": test_value,
            "timestamp": timestamp,
            "session_data": dict(session),
            "request_cookies": dict(request.cookies),
            "headers": dict(request.headers),
            "success": test_value == "cookie_test_123"
        })


@bp.route("/auth/env-check", methods=["GET"])
def env_check() -> Response:
    """Check environment variables and runtime configuration for debugging."""
    import os
    
    env_vars = {
        "SESSION_COOKIE_SECURE": os.environ.get("SESSION_COOKIE_SECURE"),
        "SESSION_COOKIE_SAMESITE": os.environ.get("SESSION_COOKIE_SAMESITE"), 
        "SESSION_COOKIE_DOMAIN": os.environ.get("SESSION_COOKIE_DOMAIN"),
        "SECRET_KEY": "SET" if os.environ.get("SECRET_KEY") else "NOT_SET",
        "SECRET_KEY_LENGTH": len(os.environ.get("SECRET_KEY", "")),
        "FLASK_ENV": os.environ.get("FLASK_ENV"),
        "DATABASE_URL": "SET" if os.environ.get("DATABASE_URL") else "NOT_SET",
        "CORS_ORIGINS": os.environ.get("CORS_ORIGINS"),
    }
    
    runtime_config = {
        "SESSION_COOKIE_SECURE": current_app.config.get("SESSION_COOKIE_SECURE"),
        "SESSION_COOKIE_HTTPONLY": current_app.config.get("SESSION_COOKIE_HTTPONLY"),
        "SESSION_COOKIE_SAMESITE": current_app.config.get("SESSION_COOKIE_SAMESITE"),
        "SESSION_COOKIE_DOMAIN": current_app.config.get("SESSION_COOKIE_DOMAIN"),
        "SESSION_COOKIE_PATH": current_app.config.get("SESSION_COOKIE_PATH"),
        "SESSION_COOKIE_NAME": current_app.config.get("SESSION_COOKIE_NAME"),
        "PERMANENT_SESSION_LIFETIME": current_app.config.get("PERMANENT_SESSION_LIFETIME"),
        "SECRET_KEY_LENGTH": len(current_app.config.get("SECRET_KEY", "")),
        "DEBUG": current_app.debug,
        "TESTING": current_app.testing,
    }
    
    current_app.logger.info(f"Environment variables check: {env_vars}")
    current_app.logger.info(f"Runtime config check: {runtime_config}")
    
    return jsonify({
        "environment_variables": env_vars,
        "runtime_config": runtime_config,
        "config_class": current_app.config.__class__.__name__,
        "request_is_secure": request.is_secure,
        "request_scheme": request.scheme,
        "request_headers": dict(request.headers)
    })


@bp.route("/auth/secret-key-test", methods=["GET", "POST"])
def secret_key_test() -> Response:
    """Test SECRET_KEY consistency by manually validating session signatures."""
    if request.method == "POST":
        # Set a test session value and return details for signature analysis
        session["secret_test"] = "test_signature_consistency"
        session["created_at"] = datetime.utcnow().isoformat()
        session.permanent = True
        
        # Get the current secret key for logging (masked)
        secret_key = current_app.config.get("SECRET_KEY", "")
        secret_key_preview = secret_key[:8] + "..." + secret_key[-8:] if len(secret_key) > 16 else "TOO_SHORT"
        
        current_app.logger.info(f"SECRET_KEY test - Creating session with key preview: {secret_key_preview}")
        current_app.logger.info(f"SECRET_KEY test - Session data: {dict(session)}")
        
        return jsonify({
            "action": "create_test_session",
            "session_data": dict(session),
            "secret_key_length": len(secret_key),
            "secret_key_preview": secret_key_preview,
            "message": "Test session created. Now make a GET request to verify signature validation."
        })
    
    else:
        # GET - Try to decode session and check signature validity
        try:
            from flask.sessions import SecureCookieSessionInterface
            
            # Get the session cookie
            session_cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session")
            session_cookie_value = request.cookies.get(session_cookie_name)
            
            current_app.logger.info(f"SECRET_KEY test - Validating session cookie: {session_cookie_name}")
            current_app.logger.info(f"SECRET_KEY test - Cookie value present: {bool(session_cookie_value)}")
            
            if not session_cookie_value:
                return jsonify({
                    "action": "validate_session", 
                    "error": "No session cookie found",
                    "cookie_name": session_cookie_name,
                    "available_cookies": list(request.cookies.keys())
                })
            
            # Try to decode the session manually
            session_interface = SecureCookieSessionInterface()
            secret_key = current_app.config.get("SECRET_KEY")
            
            current_app.logger.info(f"SECRET_KEY test - Attempting manual session decode")
            current_app.logger.info(f"SECRET_KEY test - Using secret key length: {len(secret_key)}")
            
            # This will verify the signature
            try:
                decoded_session = session_interface.get_signing_serializer(current_app).loads(session_cookie_value)
                signature_valid = True
                current_app.logger.info(f"SECRET_KEY test - Signature validation: SUCCESS")
                current_app.logger.info(f"SECRET_KEY test - Decoded session: {decoded_session}")
            except Exception as decode_error:
                signature_valid = False
                current_app.logger.error(f"SECRET_KEY test - Signature validation: FAILED - {str(decode_error)}")
                decoded_session = None
            
            # Also check what Flask's session object contains
            flask_session_data = dict(session)
            secret_test_value = session.get("secret_test")
            
            return jsonify({
                "action": "validate_session",
                "signature_valid": signature_valid,
                "decoded_session": decoded_session,
                "flask_session_data": flask_session_data,
                "secret_test_value": secret_test_value,
                "expected_value": "test_signature_consistency",
                "values_match": secret_test_value == "test_signature_consistency",
                "secret_key_length": len(secret_key),
                "cookie_present": bool(session_cookie_value),
                "cookie_length": len(session_cookie_value) if session_cookie_value else 0
            })
            
        except Exception as e:
            current_app.logger.error(f"SECRET_KEY test failed: {str(e)}")
            import traceback
            current_app.logger.error(f"SECRET_KEY test traceback: {traceback.format_exc()}")
            
            return jsonify({
                "action": "validate_session",
                "error": str(e),
                "traceback": traceback.format_exc()
            }), 500


@bp.route("/auth/sessions", methods=["GET"])
@require_auth
def get_user_sessions(current_user: User) -> Response:
    """Get all active sessions for the current user."""
    sessions = UserSession.query.filter_by(
        user_id=current_user.id, is_active=True
    ).all()

    return jsonify({"sessions": [session.to_dict() for session in sessions]})


@bp.route("/auth/sessions/<int:session_id>", methods=["DELETE"])
@require_auth
def revoke_session(current_user: User, session_id: int) -> Tuple[Response, int]:
    """Revoke a specific user session."""
    try:
        user_session = UserSession.query.filter_by(
            id=session_id, user_id=current_user.id
        ).first()

        if not user_session:
            return jsonify({"error": "Session not found"}), 404

        user_session.invalidate()
        db.session.commit()

        return jsonify({"message": "Session revoked successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Session revocation failed: {str(e)}")
        return jsonify({"error": "Session revocation failed"}), 500


@bp.route("/auth/change-password", methods=["POST"])
@require_auth
def change_password(current_user: User) -> Tuple[Response, int]:
    """Change user password."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")

        if not current_password or not new_password:
            return (
                jsonify({"error": "Current password and new password are required"}),
                400,
            )

        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({"error": "Current password is incorrect"}), 401

        # Validate new password
        if len(new_password) < 8:
            return (
                jsonify({"error": "New password must be at least 8 characters long"}),
                400,
            )

        # Set new password
        current_user.set_password(new_password)
        db.session.commit()

        # Invalidate all other sessions except current one
        current_session_token = session.get("session_token")
        UserSession.query.filter(
            UserSession.user_id == current_user.id,
            UserSession.session_token != current_session_token,
            UserSession.is_active == True,
        ).update({"is_active": False})

        db.session.commit()

        current_app.logger.info(f"Password changed for user: {current_user.username}")

        return jsonify({"message": "Password changed successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Password change failed: {str(e)}")
        return jsonify({"error": "Password change failed"}), 500


@bp.route("/user/profile", methods=["GET"])
@require_auth
def get_user_profile(current_user: User) -> Response:
    """Get current user profile with statistics."""
    try:
        # Get basic user info
        user_info = current_user.to_dict(include_sensitive=True)
        
        # Calculate recipe statistics
        total_recipes = Recipe.query.filter_by(user_id=current_user.id).count()
        
        # Recipe difficulty breakdown
        difficulty_stats = db.session.query(
            Recipe.difficulty,
            func.count(Recipe.id).label('count')
        ).filter_by(user_id=current_user.id).group_by(Recipe.difficulty).all()
        
        difficulty_breakdown = {
            'easy': 0,
            'medium': 0, 
            'hard': 0,
            'unspecified': 0
        }
        
        for stat in difficulty_stats:
            if stat.difficulty:
                difficulty_breakdown[stat.difficulty.lower()] = stat.count
            else:
                difficulty_breakdown['unspecified'] = stat.count
        
        # Average cook time
        avg_cook_time_result = db.session.query(
            func.avg(Recipe.cook_time)
        ).filter(
            Recipe.user_id == current_user.id,
            Recipe.cook_time.isnot(None)
        ).scalar()
        
        avg_cook_time = round(avg_cook_time_result, 1) if avg_cook_time_result else 0
        
        # Cookbook statistics
        total_cookbooks = Cookbook.query.filter_by(user_id=current_user.id).count()
        
        # Recipes per cookbook
        cookbook_recipe_stats = db.session.query(
            Cookbook.id,
            Cookbook.title,
            func.count(Recipe.id).label('recipe_count')
        ).outerjoin(
            Recipe, Recipe.cookbook_id == Cookbook.id
        ).filter(
            Cookbook.user_id == current_user.id
        ).group_by(Cookbook.id, Cookbook.title).all()
        
        avg_recipes_per_cookbook = total_recipes / total_cookbooks if total_cookbooks > 0 else 0
        
        # Most popular cookbook
        most_popular_cookbook = None
        if cookbook_recipe_stats:
            top_cookbook = max(cookbook_recipe_stats, key=lambda x: x.recipe_count)
            if top_cookbook.recipe_count > 0:
                most_popular_cookbook = {
                    'id': top_cookbook.id,
                    'title': top_cookbook.title,
                    'recipe_count': top_cookbook.recipe_count
                }
        
        # Recent activity (last 10 recipes)
        recent_recipes = Recipe.query.filter_by(
            user_id=current_user.id
        ).order_by(Recipe.created_at.desc()).limit(10).all()
        
        recent_activity = [
            {
                'type': 'recipe',
                'id': recipe.id,
                'title': recipe.title,
                'created_at': recipe.created_at.isoformat() if recipe.created_at else None,
                'cookbook_title': recipe.cookbook.title if recipe.cookbook else None
            }
            for recipe in recent_recipes
        ]
        
        # Compile statistics
        statistics = {
            'total_recipes': total_recipes,
            'total_cookbooks': total_cookbooks,
            'difficulty_breakdown': difficulty_breakdown,
            'avg_cook_time_minutes': avg_cook_time,
            'avg_recipes_per_cookbook': round(avg_recipes_per_cookbook, 1),
            'most_popular_cookbook': most_popular_cookbook,
            'cookbooks_with_recipes': sum(1 for stat in cookbook_recipe_stats if stat.recipe_count > 0),
            'empty_cookbooks': sum(1 for stat in cookbook_recipe_stats if stat.recipe_count == 0)
        }
        
        return jsonify({
            'user': user_info,
            'statistics': statistics,
            'recent_activity': recent_activity
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get user profile: {str(e)}")
        return jsonify({"error": "Failed to retrieve profile"}), 500

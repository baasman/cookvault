import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Tuple

from flask import Response, current_app, jsonify, request, session, g
from sqlalchemy.exc import IntegrityError

from app.utils.jwt_utils import JWTTokenManager, extract_jwt_from_request
from app.utils.rate_limiting import rate_limit_auth
from app.services.email_service import get_email_service
from app.services.sms_service import get_sms_service

from app import db
from app.api import bp
from app.models import User, UserSession, UserRole, UserStatus, Recipe, Cookbook
from sqlalchemy import func


def require_auth(f):
    """Decorator to require authentication for endpoints."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            current_app.logger.warning(
                f"Authentication failed for {request.endpoint} - No user found in session"
            )
            return jsonify({"error": "Authentication required"}), 401

        if user.is_account_locked():
            return jsonify({"error": "Account is locked"}), 423

        # Allow users pending deletion to access account management endpoints
        # They have INACTIVE status but should still be able to cancel deletion
        if user.status != UserStatus.ACTIVE:
            if user.is_pending_deletion():
                # Allow access - user can cancel deletion or view their data
                pass
            else:
                return jsonify({"error": "Account is not active"}), 403

        # Store user in g for rate limiting
        g.current_user = user
        return f(user, *args, **kwargs)

    return decorated_function


def optional_auth(f):
    """Decorator that allows both authenticated and unauthenticated access.

    Passes the current user (or None) as the first argument to the decorated function.
    Used for endpoints that have different behavior for authenticated vs unauthenticated users,
    such as serving public recipe images.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()

        # If user is authenticated, check if account is active
        if user:
            if user.is_account_locked():
                return jsonify({"error": "Account is locked"}), 423

            if user.status != UserStatus.ACTIVE:
                return jsonify({"error": "Account is not active"}), 403

            # Store user in g for rate limiting
            g.current_user = user

        # Pass user (or None) to the function
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
    """Get the current authenticated user from JWT token or session."""
    # First try JWT authentication (preferred)
    user = get_current_user_jwt()
    if user:
        return user

    # Fallback to session authentication for backward compatibility
    return get_current_user_session()


def get_current_user_jwt() -> Optional[User]:
    """Get the current authenticated user from JWT token."""
    jwt_token = extract_jwt_from_request()
    if not jwt_token:
        return None

    user = JWTTokenManager.get_user_from_token(jwt_token)
    if not user:
        current_app.logger.warning("Invalid or expired JWT token")
        return None

    return user


def get_current_user_session() -> Optional[User]:
    """Get the current authenticated user from session (legacy)."""
    session_token = session.get("session_token")
    if not session_token:
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

    db.session.add(user_session)
    db.session.commit()

    # Set session token in Flask session
    session["session_token"] = session_token
    session.permanent = True

    return user_session


@bp.route("/auth/test", methods=["GET", "POST"])
def test_auth() -> Response:
    """Simple test endpoint. Development only."""
    if not current_app.debug:
        return jsonify({"error": "Not found"}), 404
    current_app.logger.info(f"Test endpoint called with method {request.method}")
    return jsonify(
        {
            "message": "Auth blueprint is working",
            "method": request.method,
            "url": request.url,
            "blueprint": "api.auth",
        }
    )


@bp.route("/auth/debug", methods=["GET"])
def debug_auth() -> Response:
    """Debug endpoint to test API connectivity and session state. Development only."""
    if not current_app.debug:
        return jsonify({"error": "Not found"}), 404
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
            "SESSION_COOKIE_HTTPONLY": current_app.config.get(
                "SESSION_COOKIE_HTTPONLY"
            ),
            "SESSION_COOKIE_SAMESITE": current_app.config.get(
                "SESSION_COOKIE_SAMESITE"
            ),
            "PERMANENT_SESSION_LIFETIME": current_app.config.get(
                "PERMANENT_SESSION_LIFETIME"
            ),
            "SECRET_KEY_SET": bool(current_app.config.get("SECRET_KEY")),
        },
    }

    current_app.logger.info(f"Debug info: {debug_info}")
    return jsonify(debug_info)


@bp.route("/auth/register", methods=["POST"])
@rate_limit_auth
def register() -> Tuple[Response, int]:
    """Register a new user account with email or SMS verification."""
    try:
        data = request.get_json()

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
        verification_method = data.get("verification_method", "email").lower()
        phone = data.get("phone", "").strip() if data.get("phone") else None

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

        # Validate verification method
        if verification_method not in ["email", "sms"]:
            return jsonify(
                {"error": "verification_method must be 'email' or 'sms'"}
            ), 400

        # If SMS verification chosen, phone is required
        if verification_method == "sms":
            if not phone:
                return jsonify({"error": "phone is required for SMS verification"}), 400

            # Validate phone number format using SMS service
            sms_service = get_sms_service()
            is_valid, formatted_phone_or_error = sms_service.validate_phone_number(
                phone
            )

            if not is_valid:
                return jsonify({"error": formatted_phone_or_error}), 400

            # Use the formatted phone number (E.164 format)
            phone = formatted_phone_or_error

        # Check if user already exists (email, username, or phone)
        filters = [(User.username == username), (User.email == email)]
        if phone:
            filters.append(User.phone_number == phone)

        existing_user = User.query.filter(db.or_(*filters)).first()

        if existing_user:
            if existing_user.username == username:
                return jsonify({"error": "Username already exists"}), 409
            elif existing_user.email == email:
                return jsonify({"error": "Email already exists"}), 409
            elif phone and existing_user.phone_number == phone:
                return jsonify({"error": "Phone number already exists"}), 409

        # Check if email verification is required
        require_verification = current_app.config.get(
            "REQUIRE_EMAIL_VERIFICATION", False
        )

        if require_verification:
            # Create new user with pending verification status
            user = User(
                username=username,
                email=email,
                phone_number=phone,
                first_name=data.get("first_name", "").strip(),
                last_name=data.get("last_name", "").strip(),
                status=UserStatus.PENDING_VERIFICATION,
                is_verified=False,
            )
            user.set_password(password)

            # Generate verification token based on method
            if verification_method == "email":
                verification_token = user.generate_verification_token()
            else:  # SMS
                verification_token = user.generate_phone_verification_token()

            db.session.add(user)
            db.session.commit()

            # Send verification based on method
            verification_sent = False
            if verification_method == "email":
                email_service = get_email_service()
                verification_sent = email_service.send_verification_email(
                    email=email, token=verification_token, username=username
                )
            else:  # SMS
                sms_service = get_sms_service()
                verification_sent = sms_service.send_verification_sms(
                    phone_number=phone, code=verification_token
                )

            if not verification_sent:
                current_app.logger.warning(
                    f"Verification {verification_method} failed to send for user {username}"
                )

            current_app.logger.info(f"New user registered: {username} (ID: {user.id})")

            # Build response without JWT token (user must verify first)
            response_data = {
                "message": "Registration successful. Please verify your account.",
                "requires_verification": True,
                "verification_method": verification_method,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            }

            if verification_method == "email":
                response_data["email"] = email
            else:
                response_data["phone"] = phone

            response = jsonify(response_data)

            return response, 201
        else:
            # Verification disabled - create user as already verified and active
            user = User(
                username=username,
                email=email,
                phone_number=phone,
                first_name=data.get("first_name", "").strip(),
                last_name=data.get("last_name", "").strip(),
                status=UserStatus.ACTIVE,
                is_verified=True,
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            current_app.logger.info(
                f"New user registered (verification disabled): {username} (ID: {user.id})"
            )

            # Generate JWT token for immediate login
            jwt_token = JWTTokenManager.generate_token(user)

            # Create session for the user
            user_session = create_user_session(user, request)

            response_data = {
                "message": "Registration successful.",
                "requires_verification": False,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role.value,
                },
                "access_token": jwt_token,
                "token_type": "Bearer",
                "session_token": user_session.session_token,
            }

            return jsonify(response_data), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username or email already exists"}), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration failed: {str(e)}")
        return jsonify({"error": "Registration failed"}), 500


@bp.route("/auth/verify-email", methods=["POST"])
@rate_limit_auth
def verify_email() -> Tuple[Response, int]:
    """Verify user email address with token."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        token = data.get("token", "").strip()

        if not token:
            return jsonify({"error": "Verification token is required"}), 400

        # Find user with this verification token
        user = User.query.filter_by(email_verification_token=token).first()

        if not user:
            current_app.logger.warning(
                f"Invalid email verification token: {token[:8]}..."
            )
            return jsonify({"error": "Invalid or expired verification token"}), 400

        # Check if token is valid
        if not user.is_email_verification_valid(token):
            current_app.logger.warning(
                f"Email verification failed for user {user.username}: token invalid or user already verified"
            )
            return jsonify({"error": "Invalid or expired verification token"}), 400

        # Mark user as verified
        user.is_verified = True
        user.status = UserStatus.ACTIVE
        user.email_verified_at = datetime.utcnow()
        user.clear_email_verification()

        db.session.commit()

        current_app.logger.info(
            f"Email verified successfully for user: {user.username} (ID: {user.id})"
        )

        # Generate JWT token for immediate login
        jwt_token = JWTTokenManager.generate_token(user)

        # Create session for the user
        user_session = create_user_session(user, request)

        return jsonify(
            {
                "message": "Email verified successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_verified": user.is_verified,
                    "role": user.role.value,
                },
                "access_token": jwt_token,
                "token_type": "Bearer",
                "session_token": user_session.session_token,
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Email verification failed: {str(e)}")
        return jsonify({"error": "Verification failed"}), 500


@bp.route("/auth/verify-phone", methods=["POST"])
@rate_limit_auth
def verify_phone() -> Tuple[Response, int]:
    """Verify user phone number with 6-digit code."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        phone = data.get("phone", "").strip()
        code = data.get("code", "").strip()

        if not phone or not code:
            return jsonify(
                {"error": "Phone number and verification code are required"}
            ), 400

        # Validate phone format
        sms_service = get_sms_service()
        is_valid, formatted_phone_or_error = sms_service.validate_phone_number(phone)

        if not is_valid:
            return jsonify({"error": formatted_phone_or_error}), 400

        phone = formatted_phone_or_error

        # Find user with this phone number
        user = User.query.filter_by(phone_number=phone).first()

        if not user:
            current_app.logger.warning(
                f"Phone verification attempt for unknown phone: {phone}"
            )
            return jsonify({"error": "Invalid phone number or verification code"}), 400

        # Check if code is valid and not expired
        if not user.is_phone_verification_valid():
            current_app.logger.warning(
                f"Phone verification failed for user {user.username}: token expired"
            )
            return jsonify(
                {"error": "Verification code has expired. Please request a new one."}
            ), 400

        # Check if code matches
        if user.phone_verification_token != code:
            current_app.logger.warning(
                f"Phone verification failed for user {user.username}: incorrect code"
            )
            return jsonify({"error": "Invalid verification code"}), 400

        # Mark user as verified
        user.is_verified = True
        user.phone_verified = True
        user.status = UserStatus.ACTIVE
        user.clear_phone_verification()

        db.session.commit()

        current_app.logger.info(
            f"Phone verified successfully for user: {user.username} (ID: {user.id})"
        )

        # Generate JWT token for immediate login
        jwt_token = JWTTokenManager.generate_token(user)

        # Create session for the user
        user_session = create_user_session(user, request)

        return jsonify(
            {
                "message": "Phone verified successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "phone_number": user.phone_number,
                    "is_verified": user.is_verified,
                    "phone_verified": user.phone_verified,
                    "role": user.role.value,
                },
                "access_token": jwt_token,
                "token_type": "Bearer",
                "session_token": user_session.session_token,
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Phone verification failed: {str(e)}")
        return jsonify({"error": "Verification failed"}), 500


@bp.route("/auth/resend-verification", methods=["POST"])
@rate_limit_auth
def resend_verification() -> Tuple[Response, int]:
    """Resend verification email or SMS to unverified user."""
    try:
        # Check if email verification is required
        require_verification = current_app.config.get(
            "REQUIRE_EMAIL_VERIFICATION", False
        )
        if not require_verification:
            return jsonify(
                {
                    "error": "Email verification is not required. You can log in directly."
                }
            ), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        email_or_phone = data.get("email_or_phone", "").strip()
        method = data.get("method", "").strip().lower()

        if not email_or_phone or not method:
            return jsonify({"error": "email_or_phone and method are required"}), 400

        if method not in ["email", "sms"]:
            return jsonify({"error": "method must be 'email' or 'sms'"}), 400

        # Find user by email or phone based on method
        user = None
        if method == "email":
            # Treat as email
            user = User.query.filter_by(email=email_or_phone.lower()).first()
        else:  # SMS
            # Validate and format phone number
            sms_service = get_sms_service()
            is_valid, formatted_phone_or_error = sms_service.validate_phone_number(
                email_or_phone
            )

            if not is_valid:
                return jsonify({"error": formatted_phone_or_error}), 400

            user = User.query.filter_by(phone_number=formatted_phone_or_error).first()

        if not user:
            current_app.logger.warning(
                f"Resend verification attempt for unknown {method}: {email_or_phone}"
            )
            # Return generic error to avoid user enumeration
            return jsonify(
                {"error": "If the account exists, verification will be resent"}
            ), 200

        # Check if user is already verified
        if user.is_verified:
            current_app.logger.info(
                f"Resend verification attempt for already verified user: {user.username}"
            )
            return jsonify({"error": "Account is already verified"}), 400

        # Rate limiting: Check last sent time (5 minutes for both email and SMS resend)
        if method == "email":
            # Check when email was last sent (we can use email_verified_at or a separate cache)
            # For now, we'll allow resend (rate limiting is handled by email_service internally)
            pass
        else:  # SMS
            # Check phone verification sent time
            if user.phone_verification_sent_at:
                time_since_last = datetime.utcnow() - user.phone_verification_sent_at
                if time_since_last < timedelta(minutes=2):
                    current_app.logger.warning(
                        f"Rate limit: SMS resend to {user.phone_number} too soon"
                    )
                    return jsonify(
                        {
                            "error": "Please wait 2 minutes before requesting another code"
                        }
                    ), 429

        # Regenerate verification token
        verification_sent = False
        if method == "email":
            verification_token = user.generate_verification_token()
            db.session.commit()

            email_service = get_email_service()
            verification_sent = email_service.send_verification_email(
                email=user.email, token=verification_token, username=user.username
            )
            current_app.logger.info(
                f"Resent email verification to {user.email}: {verification_sent}"
            )
        else:  # SMS
            verification_token = user.generate_phone_verification_token()
            db.session.commit()

            sms_service = get_sms_service()
            verification_sent = sms_service.send_verification_sms(
                phone_number=user.phone_number, code=verification_token
            )
            current_app.logger.info(
                f"Resent SMS verification to {user.phone_number}: {verification_sent}"
            )

        if not verification_sent:
            current_app.logger.error(
                f"Failed to resend verification {method} for user {user.username}"
            )
            return jsonify(
                {"error": "Failed to send verification. Please try again later."}
            ), 500

        return jsonify(
            {"message": f"Verification {method} sent successfully", "method": method}
        ), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Resend verification failed: {str(e)}")
        return jsonify({"error": "Failed to resend verification"}), 500


@bp.route("/auth/login", methods=["POST"])
@rate_limit_auth
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
            remaining_minutes = (
                int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
            )
            return (
                jsonify(
                    {
                        "error": f"Account is temporarily locked. Try again in {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}."
                    }
                ),
                423,
            )

        # Check password
        if not user.check_password(password):
            user.increment_failed_login()
            db.session.commit()
            max_attempts = 5
            remaining = max_attempts - user.failed_login_attempts
            if remaining <= 0:
                return (
                    jsonify(
                        {
                            "error": "Account locked due to too many failed attempts. Try again in 30 minutes."
                        }
                    ),
                    423,
                )
            elif remaining <= 2:
                return (
                    jsonify(
                        {
                            "error": f"Incorrect password. {remaining} attempt{'s' if remaining != 1 else ''} remaining before account is locked."
                        }
                    ),
                    401,
                )
            else:
                return jsonify({"error": "Incorrect username or password"}), 401

        # Check account status
        if user.status != UserStatus.ACTIVE:
            return jsonify({"error": "Account is not active"}), 403

        # Successful login
        user.reset_failed_login()

        # Generate JWT token instead of session
        jwt_token = JWTTokenManager.generate_token(user)

        # Still create session for backward compatibility and audit purposes
        # Invalidate any existing sessions for this user
        UserSession.query.filter_by(user_id=user.id, is_active=True).update(
            {"is_active": False}
        )

        # Create new session (for audit trail)
        create_user_session(user, request)

        current_app.logger.info(f"User logged in: {user.username}")

        return jsonify(
            {
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role.value,
                },
                "access_token": jwt_token,
                "token_type": "Bearer",
            }
        ), 200

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

    return jsonify(
        {
            "authenticated": user is not None,
            "user": user.to_dict() if user else None,
            "session_token_present": bool(session.get("session_token")),
            "session_keys": list(session.keys()),
            "cookies_present": len(request.cookies) > 0,
            "cookie_keys": list(request.cookies.keys()),
            "database_stats": {
                "total_users": total_users,
                "all_usernames": all_usernames,
            },
        }
    )


@bp.route("/auth/cookie-test", methods=["GET", "POST"])
def cookie_test() -> Response:
    """Test cookie setting and retrieval for debugging session issues. Development only."""
    if not current_app.debug:
        return jsonify({"error": "Not found"}), 404
    if request.method == "POST":
        # Set test values in session
        session["test_value"] = "cookie_test_123"
        session["timestamp"] = datetime.utcnow().isoformat()
        session.permanent = True

        current_app.logger.info("Cookie test - Setting session values")
        current_app.logger.info(f"Session after setting: {dict(session)}")

        response = jsonify(
            {
                "action": "set",
                "session_data": dict(session),
                "config": {
                    "SESSION_COOKIE_SECURE": current_app.config.get(
                        "SESSION_COOKIE_SECURE"
                    ),
                    "SESSION_COOKIE_HTTPONLY": current_app.config.get(
                        "SESSION_COOKIE_HTTPONLY"
                    ),
                    "SESSION_COOKIE_SAMESITE": current_app.config.get(
                        "SESSION_COOKIE_SAMESITE"
                    ),
                    "SESSION_COOKIE_DOMAIN": current_app.config.get(
                        "SESSION_COOKIE_DOMAIN"
                    ),
                    "SESSION_COOKIE_PATH": current_app.config.get(
                        "SESSION_COOKIE_PATH"
                    ),
                    "SESSION_COOKIE_NAME": current_app.config.get(
                        "SESSION_COOKIE_NAME"
                    ),
                },
            }
        )

        # Log response headers to see what cookies are being sent
        current_app.logger.info(
            "Response headers will include: Set-Cookie with session data"
        )

        return response

    else:
        # GET - check what we can retrieve
        test_value = session.get("test_value")
        timestamp = session.get("timestamp")

        current_app.logger.info(
            f"Cookie test - Retrieved from session: test_value={test_value}, timestamp={timestamp}"
        )
        current_app.logger.info(f"Current session data: {dict(session)}")
        current_app.logger.info(f"Request cookies: {dict(request.cookies)}")

        return jsonify(
            {
                "action": "get",
                "test_value": test_value,
                "timestamp": timestamp,
                "session_data": dict(session),
                "request_cookies": dict(request.cookies),
                "headers": dict(request.headers),
                "success": test_value == "cookie_test_123",
            }
        )


@bp.route("/auth/jwt-debug", methods=["GET"])
def jwt_debug() -> Response:
    """Debug JWT authentication flow. Development only."""
    if not current_app.debug:
        return jsonify({"error": "Not found"}), 404
    from flask import request
    from app.utils.jwt_utils import extract_jwt_from_request, JWTTokenManager

    debug_info = {
        "request_headers": dict(request.headers),
        "authorization_header": request.headers.get("Authorization"),
        "jwt_extraction_result": None,
        "jwt_validation_result": None,
        "current_user_result": None,
        "errors": [],
    }

    try:
        # Test JWT extraction
        jwt_token = extract_jwt_from_request()
        debug_info["jwt_extraction_result"] = {
            "token_found": jwt_token is not None,
            "token_preview": jwt_token[:20] + "..." if jwt_token else None,
        }

        if jwt_token:
            # Test JWT validation
            try:
                user = JWTTokenManager.get_user_from_token(jwt_token)
                debug_info["jwt_validation_result"] = {
                    "valid": user is not None,
                    "user_id": user.id if user else None,
                    "username": user.username if user else None,
                }
            except Exception as e:
                debug_info["jwt_validation_result"] = {"error": str(e)}
                debug_info["errors"].append(f"JWT validation error: {str(e)}")

        # Test overall current user function
        try:
            current_user = get_current_user()
            debug_info["current_user_result"] = {
                "user_found": current_user is not None,
                "user_id": current_user.id if current_user else None,
                "username": current_user.username if current_user else None,
                "auth_method": "JWT" if get_current_user_jwt() else "Session",
            }
        except Exception as e:
            debug_info["current_user_result"] = {"error": str(e)}
            debug_info["errors"].append(f"get_current_user error: {str(e)}")

    except Exception as e:
        debug_info["errors"].append(f"Debug function error: {str(e)}")

    current_app.logger.info(f"JWT Debug Info: {debug_info}")
    return jsonify(debug_info)


@bp.route("/auth/env-check", methods=["GET"])
def env_check() -> Response:
    """Check environment variables and runtime configuration for debugging. Development only."""
    if not current_app.debug:
        return jsonify({"error": "Not found"}), 404
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
        "PERMANENT_SESSION_LIFETIME": current_app.config.get(
            "PERMANENT_SESSION_LIFETIME"
        ),
        "SECRET_KEY_LENGTH": len(current_app.config.get("SECRET_KEY", "")),
        "DEBUG": current_app.debug,
        "TESTING": current_app.testing,
    }

    current_app.logger.info(f"Environment variables check: {env_vars}")
    current_app.logger.info(f"Runtime config check: {runtime_config}")

    return jsonify(
        {
            "environment_variables": env_vars,
            "runtime_config": runtime_config,
            "config_class": current_app.config.__class__.__name__,
            "config_module": current_app.config.__class__.__module__,
            "config_bases": [
                base.__name__ for base in current_app.config.__class__.__bases__
            ],
            "request_is_secure": request.is_secure,
            "request_scheme": request.scheme,
            "request_headers": dict(request.headers),
        }
    )


@bp.route("/auth/secret-key-test", methods=["GET", "POST"])
def secret_key_test() -> Response:
    """Test SECRET_KEY consistency by manually validating session signatures. Development only."""
    if not current_app.debug:
        return jsonify({"error": "Not found"}), 404
    if request.method == "POST":
        # Set a test session value and return details for signature analysis
        session["secret_test"] = "test_signature_consistency"
        session["created_at"] = datetime.utcnow().isoformat()
        session.permanent = True

        # Get the current secret key for logging (masked)
        secret_key = current_app.config.get("SECRET_KEY", "")
        secret_key_preview = (
            secret_key[:8] + "..." + secret_key[-8:]
            if len(secret_key) > 16
            else "TOO_SHORT"
        )

        current_app.logger.info(
            f"SECRET_KEY test - Creating session with key preview: {secret_key_preview}"
        )
        current_app.logger.info(f"SECRET_KEY test - Session data: {dict(session)}")

        return jsonify(
            {
                "action": "create_test_session",
                "session_data": dict(session),
                "secret_key_length": len(secret_key),
                "secret_key_preview": secret_key_preview,
                "message": "Test session created. Now make a GET request to verify signature validation.",
            }
        )

    else:
        # GET - Try to decode session and check signature validity
        try:
            from flask.sessions import SecureCookieSessionInterface

            # Get the session cookie
            session_cookie_name = current_app.config.get(
                "SESSION_COOKIE_NAME", "session"
            )
            session_cookie_value = request.cookies.get(session_cookie_name)

            current_app.logger.info(
                f"SECRET_KEY test - Validating session cookie: {session_cookie_name}"
            )
            current_app.logger.info(
                f"SECRET_KEY test - Cookie value present: {bool(session_cookie_value)}"
            )

            if not session_cookie_value:
                return jsonify(
                    {
                        "action": "validate_session",
                        "error": "No session cookie found",
                        "cookie_name": session_cookie_name,
                        "available_cookies": list(request.cookies.keys()),
                    }
                )

            # Try to decode the session manually
            session_interface = SecureCookieSessionInterface()
            secret_key = current_app.config.get("SECRET_KEY")

            current_app.logger.info(
                "SECRET_KEY test - Attempting manual session decode"
            )
            current_app.logger.info(
                f"SECRET_KEY test - Using secret key length: {len(secret_key)}"
            )

            # This will verify the signature
            try:
                decoded_session = session_interface.get_signing_serializer(
                    current_app
                ).loads(session_cookie_value)
                signature_valid = True
                current_app.logger.info(
                    "SECRET_KEY test - Signature validation: SUCCESS"
                )
                current_app.logger.info(
                    f"SECRET_KEY test - Decoded session: {decoded_session}"
                )
            except Exception as decode_error:
                signature_valid = False
                current_app.logger.error(
                    f"SECRET_KEY test - Signature validation: FAILED - {str(decode_error)}"
                )
                decoded_session = None

            # Also check what Flask's session object contains
            flask_session_data = dict(session)
            secret_test_value = session.get("secret_test")

            return jsonify(
                {
                    "action": "validate_session",
                    "signature_valid": signature_valid,
                    "decoded_session": decoded_session,
                    "flask_session_data": flask_session_data,
                    "secret_test_value": secret_test_value,
                    "expected_value": "test_signature_consistency",
                    "values_match": secret_test_value == "test_signature_consistency",
                    "secret_key_length": len(secret_key),
                    "cookie_present": bool(session_cookie_value),
                    "cookie_length": (
                        len(session_cookie_value) if session_cookie_value else 0
                    ),
                }
            )

        except Exception as e:
            current_app.logger.error(f"SECRET_KEY test failed: {str(e)}")
            import traceback

            current_app.logger.error(
                f"SECRET_KEY test traceback: {traceback.format_exc()}"
            )

            return (
                jsonify(
                    {
                        "action": "validate_session",
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }
                ),
                500,
            )


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


# =============================================================================
# Password Reset (Forgot Password) Endpoints
# =============================================================================


@bp.route("/auth/forgot-password", methods=["POST"])
@rate_limit_auth
def forgot_password() -> Tuple[Response, int]:
    """
    Request a password reset email.

    Always returns 200 to prevent email enumeration attacks.

    Request:  { "email": "user@example.com" }
    Response: { "message": "If an account exists with this email, you will receive a password reset link." }
    """
    import traceback

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        email = data.get("email", "").strip().lower()

        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Validate email format (basic check)
        if "@" not in email or "." not in email:
            return jsonify({"error": "Invalid email format"}), 400

        # Generic message to prevent email enumeration
        success_message = "If an account exists with this email, you will receive a password reset link."

        # Find user by email
        user = User.query.filter_by(email=email).first()

        if not user:
            # Don't reveal that the email doesn't exist
            current_app.logger.info(
                f"Password reset requested for non-existent email: {email}"
            )
            return jsonify({"message": success_message}), 200

        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            current_app.logger.info(
                f"Password reset requested for inactive user: {email}"
            )
            return jsonify({"message": success_message}), 200

        # Generate password reset token
        token = user.generate_password_reset_token()
        db.session.commit()

        # Send password reset email
        email_service = get_email_service()
        email_sent = email_service.send_password_reset_email(
            email=user.email, token=token, username=user.username
        )

        if email_sent:
            current_app.logger.info(f"Password reset email sent to {email}")
        else:
            current_app.logger.warning(
                f"Failed to send password reset email to {email}"
            )

        return jsonify({"message": success_message}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Password reset request failed: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        # Return generic message even on error to prevent info leakage
        return jsonify(
            {
                "message": "If an account exists with this email, you will receive a password reset link."
            }
        ), 200


@bp.route("/auth/validate-reset-token", methods=["POST"])
@rate_limit_auth
def validate_reset_token() -> Tuple[Response, int]:
    """
    Validate a password reset token before showing the reset form.

    Request:  { "token": "abc123..." }
    Response: { "valid": true, "email": "u***@example.com" }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        token = data.get("token", "").strip()

        if not token:
            return jsonify({"error": "Token is required"}), 400

        # Find user with this reset token
        user = User.query.filter_by(password_reset_token=token).first()

        if not user:
            current_app.logger.warning(f"Invalid password reset token: {token[:8]}...")
            return jsonify(
                {"valid": False, "error": "Invalid or expired reset token"}
            ), 400

        # Check if token is valid (not expired)
        if not user.is_password_reset_valid():
            current_app.logger.warning(
                f"Expired password reset token for user: {user.username}"
            )
            return jsonify({"valid": False, "error": "Reset token has expired"}), 400

        # Mask email for display (e.g., "t***@example.com")
        email = user.email
        at_index = email.find("@")
        if at_index > 1:
            masked_email = email[0] + "***" + email[at_index:]
        else:
            masked_email = "***" + email[at_index:]

        return jsonify({"valid": True, "email": masked_email}), 200

    except Exception as e:
        current_app.logger.error(f"Token validation failed: {str(e)}")
        return jsonify({"valid": False, "error": "Token validation failed"}), 400


@bp.route("/auth/reset-password", methods=["POST"])
@rate_limit_auth
def reset_password() -> Tuple[Response, int]:
    """
    Reset password using a valid reset token.

    Request:  { "token": "abc123...", "new_password": "newPassword123" }
    Response: { "message": "Password has been reset successfully." }
    """
    import traceback

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        token = data.get("token", "").strip()
        new_password = data.get("new_password", "")

        if not token:
            return jsonify({"error": "Token is required"}), 400

        if not new_password:
            return jsonify({"error": "New password is required"}), 400

        # Validate password strength
        if len(new_password) < 8:
            return jsonify(
                {"error": "Password must be at least 8 characters long"}
            ), 400

        # Find user with this reset token
        user = User.query.filter_by(password_reset_token=token).first()

        if not user:
            current_app.logger.warning(
                f"Password reset attempt with invalid token: {token[:8]}..."
            )
            return jsonify({"error": "Invalid or expired reset token"}), 400

        # Check if token is valid (not expired)
        if not user.is_password_reset_valid():
            current_app.logger.warning(
                f"Password reset attempt with expired token for user: {user.username}"
            )
            return jsonify(
                {
                    "error": "Reset token has expired. Please request a new password reset."
                }
            ), 400

        # Set new password
        user.set_password(new_password)

        # Clear the reset token
        user.clear_password_reset()

        # Invalidate all existing sessions for security
        UserSession.query.filter_by(user_id=user.id, is_active=True).update(
            {"is_active": False}
        )

        db.session.commit()

        current_app.logger.info(
            f"Password reset successful for user: {user.username} (ID: {user.id})"
        )

        return jsonify(
            {
                "message": "Password has been reset successfully. You can now log in with your new password."
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Password reset failed: {str(e)}\nTraceback: {traceback.format_exc()}"
        )
        return jsonify({"error": "Password reset failed. Please try again."}), 500


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
            UserSession.is_active,
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

        # Calculate recipe statistics (include both owned and uploaded recipes)
        total_recipes = (
            Recipe.query.filter(
                db.or_(
                    Recipe.user_id == current_user.id,
                    Recipe.uploaded_by_id == current_user.id,
                )
            )
            .distinct()
            .count()
        )

        # Recipe difficulty breakdown
        difficulty_stats = (
            db.session.query(Recipe.difficulty, func.count(Recipe.id).label("count"))
            .filter(
                db.or_(
                    Recipe.user_id == current_user.id,
                    Recipe.uploaded_by_id == current_user.id,
                )
            )
            .group_by(Recipe.difficulty)
            .all()
        )

        difficulty_breakdown = {"easy": 0, "medium": 0, "hard": 0, "unspecified": 0}

        for stat in difficulty_stats:
            if stat.difficulty:
                difficulty_breakdown[stat.difficulty.lower()] = stat.count
            else:
                difficulty_breakdown["unspecified"] = stat.count

        # Average cook time
        avg_cook_time_result = (
            db.session.query(func.avg(Recipe.cook_time))
            .filter(
                db.or_(
                    Recipe.user_id == current_user.id,
                    Recipe.uploaded_by_id == current_user.id,
                ),
                Recipe.cook_time.isnot(None),
            )
            .scalar()
        )

        avg_cook_time = round(avg_cook_time_result, 1) if avg_cook_time_result else 0

        # Cookbook statistics
        total_cookbooks = Cookbook.query.filter_by(user_id=current_user.id).count()

        # Recipes per cookbook
        cookbook_recipe_stats = (
            db.session.query(
                Cookbook.id, Cookbook.title, func.count(Recipe.id).label("recipe_count")
            )
            .outerjoin(Recipe, Recipe.cookbook_id == Cookbook.id)
            .filter(Cookbook.user_id == current_user.id)
            .group_by(Cookbook.id, Cookbook.title)
            .all()
        )

        avg_recipes_per_cookbook = (
            total_recipes / total_cookbooks if total_cookbooks > 0 else 0
        )

        # Most popular cookbook
        most_popular_cookbook = None
        if cookbook_recipe_stats:
            top_cookbook = max(cookbook_recipe_stats, key=lambda x: x.recipe_count)
            if top_cookbook.recipe_count > 0:
                most_popular_cookbook = {
                    "id": top_cookbook.id,
                    "title": top_cookbook.title,
                    "recipe_count": top_cookbook.recipe_count,
                }

        # Recent activity (last 10 recipes - include both owned and uploaded)
        recent_recipes = (
            Recipe.query.filter(
                db.or_(
                    Recipe.user_id == current_user.id,
                    Recipe.uploaded_by_id == current_user.id,
                )
            )
            .order_by(Recipe.created_at.desc())
            .limit(10)
            .all()
        )

        recent_activity = [
            {
                "type": "recipe",
                "id": recipe.id,
                "title": recipe.title,
                "created_at": (
                    recipe.created_at.isoformat() if recipe.created_at else None
                ),
                "cookbook_title": recipe.cookbook.title if recipe.cookbook else None,
            }
            for recipe in recent_recipes
        ]

        # Compile statistics
        statistics = {
            "total_recipes": total_recipes,
            "total_cookbooks": total_cookbooks,
            "difficulty_breakdown": difficulty_breakdown,
            "avg_cook_time_minutes": avg_cook_time,
            "avg_recipes_per_cookbook": round(avg_recipes_per_cookbook, 1),
            "most_popular_cookbook": most_popular_cookbook,
            "cookbooks_with_recipes": sum(
                1 for stat in cookbook_recipe_stats if stat.recipe_count > 0
            ),
            "empty_cookbooks": sum(
                1 for stat in cookbook_recipe_stats if stat.recipe_count == 0
            ),
        }

        return jsonify(
            {
                "user": user_info,
                "statistics": statistics,
                "recent_activity": recent_activity,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Failed to get user profile: {str(e)}")
        return jsonify({"error": "Failed to retrieve profile"}), 500


@bp.route("/user/profile", methods=["PUT"])
@require_auth
def update_user_profile(current_user: User) -> Response:
    """Update current user profile."""
    try:
        # Handle multipart/form-data for file uploads
        if request.content_type and request.content_type.startswith(
            "multipart/form-data"
        ):
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            bio = request.form.get("bio", "").strip()
            avatar_file = request.files.get("avatar")
        else:
            # Handle JSON data
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400

            first_name = data.get("first_name", "").strip()
            last_name = data.get("last_name", "").strip()
            bio = data.get("bio", "").strip()
            avatar_file = None

        # Validate bio length
        if bio and len(bio) > 500:
            return jsonify({"error": "Bio must be less than 500 characters"}), 400

        # Update user fields
        if first_name is not None:
            current_user.first_name = first_name if first_name else None
        if last_name is not None:
            current_user.last_name = last_name if last_name else None
        if bio is not None:
            current_user.bio = bio if bio else None

        # Handle avatar upload
        if avatar_file and avatar_file.filename:
            # Validate file type
            allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
            file_extension = (
                avatar_file.filename.rsplit(".", 1)[1].lower()
                if "." in avatar_file.filename
                else ""
            )

            if file_extension not in allowed_extensions:
                return jsonify(
                    {
                        "error": "Invalid file type. Only PNG, JPG, JPEG, GIF, and WebP files are allowed."
                    }
                ), 400

            # Validate file size (5MB limit)
            avatar_file.seek(0, 2)  # Seek to end
            file_size = avatar_file.tell()
            avatar_file.seek(0)  # Seek back to beginning

            if file_size > 5 * 1024 * 1024:  # 5MB
                return jsonify({"error": "File too large. Maximum size is 5MB."}), 400

            try:
                from app.services.cloudinary_service import cloudinary_service

                # Read the file data
                avatar_file.seek(0)
                image_data = avatar_file.read()

                # Upload to Cloudinary with avatar-specific settings
                upload_result = cloudinary_service.upload_image(
                    image_data=image_data,
                    filename=f"avatar_{current_user.id}_{avatar_file.filename}",
                    folder="avatars",
                    generate_thumbnail=True,
                )

                # Store the Cloudinary URL
                current_user.avatar_url = upload_result["url"]
                current_app.logger.info(
                    f"Successfully uploaded avatar for user {current_user.id}: {upload_result['public_id']}"
                )

            except Exception as e:
                current_app.logger.error(
                    f"Failed to upload avatar for user {current_user.id}: {str(e)}"
                )
                return jsonify({"error": "Failed to upload avatar"}), 500

        db.session.commit()
        current_app.logger.info(f"Profile updated for user: {current_user.username}")

        # Return updated user info
        return jsonify(
            {
                "message": "Profile updated successfully",
                "user": current_user.to_dict(include_sensitive=True),
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update user profile: {str(e)}")
        return jsonify({"error": "Failed to update profile"}), 500


@bp.route("/users/<int:user_id>", methods=["GET"])
def get_public_user_profile(user_id: int) -> Response:
    """Get public user profile by user ID (no authentication required)."""
    try:
        user = User.query.get(user_id)
        if not user or user.status != UserStatus.ACTIVE:
            return jsonify({"error": "User not found"}), 404

        # Get public user info (no sensitive data)
        user_info = user.to_dict(include_sensitive=False)

        # Calculate public recipe statistics (only public recipes)
        total_recipes = Recipe.query.filter_by(user_id=user.id, is_public=True).count()

        # Cookbook statistics
        total_cookbooks = Cookbook.query.filter_by(user_id=user.id).count()

        # Recent public activity (last 10 public recipes)
        recent_recipes = (
            Recipe.query.filter_by(user_id=user.id, is_public=True)
            .order_by(Recipe.created_at.desc())
            .limit(10)
            .all()
        )

        recent_activity = [
            {
                "type": "recipe",
                "id": recipe.id,
                "title": recipe.title,
                "created_at": (
                    recipe.created_at.isoformat() if recipe.created_at else None
                ),
                "cookbook_title": recipe.cookbook.title if recipe.cookbook else None,
            }
            for recipe in recent_recipes
        ]

        # Compile public statistics
        statistics = {
            "total_public_recipes": total_recipes,
            "total_cookbooks": total_cookbooks,
            "member_since": user.created_at.isoformat() if user.created_at else None,
        }

        return jsonify(
            {
                "user": user_info,
                "statistics": statistics,
                "recent_activity": recent_activity,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Failed to get public user profile: {str(e)}")
        return jsonify({"error": "Failed to retrieve user profile"}), 500


@bp.route("/users/by-username/<username>", methods=["GET"])
def get_public_user_profile_by_username(username: str) -> Response:
    """Get public user profile by username (no authentication required)."""
    try:
        user = User.query.filter_by(username=username).first()
        if not user or user.status != UserStatus.ACTIVE:
            return jsonify({"error": "User not found"}), 404

        # Redirect to the user ID endpoint with same logic
        return get_public_user_profile(user.id)

    except Exception as e:
        current_app.logger.error(
            f"Failed to get public user profile by username: {str(e)}"
        )
        return jsonify({"error": "Failed to retrieve user profile"}), 500


# =============================================================================
# Account Deletion Endpoints
# =============================================================================


@bp.route("/auth/account", methods=["DELETE"])
@require_auth
def request_account_deletion(user: User) -> Response:
    """
    Request account deletion with 7-day grace period.

    The account will be scheduled for deletion 7 days from now.
    During this period, the user can still log in and cancel the deletion.
    After 7 days, a background task will permanently delete all user data.

    Requires password confirmation in request body.

    Returns:
        JSON response with deletion scheduled date
    """
    import traceback

    try:
        data = request.get_json() or {}
        password = data.get("password")

        if not password:
            return jsonify({"error": "Password confirmation required"}), 400

        # Verify password
        if not user.check_password(password):
            return jsonify({"error": "Incorrect password"}), 401

        # Check if already pending deletion
        if user.is_pending_deletion():
            return jsonify(
                {
                    "error": "Account is already scheduled for deletion",
                    "deletion_scheduled_for": user.deletion_scheduled_for.isoformat(),
                }
            ), 400

        # Schedule deletion for 7 days from now
        deletion_date = user.schedule_deletion(days=7)
        db.session.commit()

        current_app.logger.info(
            f"Account deletion scheduled for user {user.id} ({user.email}) "
            f"on {deletion_date.isoformat()}"
        )

        # Send confirmation email
        try:
            from app.services.email_service import get_email_service

            email_service = get_email_service()
            _send_deletion_scheduled_email(email_service, user, deletion_date)
        except Exception as email_error:
            current_app.logger.warning(
                f"Failed to send deletion confirmation email to {user.email}: {email_error}"
            )

        return jsonify(
            {
                "message": "Account scheduled for deletion",
                "deletion_scheduled_for": deletion_date.isoformat(),
                "days_until_deletion": 7,
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to schedule account deletion for user {user.id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to schedule account deletion"}), 500


@bp.route("/auth/account/cancel-deletion", methods=["POST"])
@require_auth
def cancel_account_deletion(user: User) -> Response:
    """
    Cancel a pending account deletion.

    Can only be called during the 7-day grace period before permanent deletion.

    Returns:
        JSON response confirming cancellation
    """
    import traceback

    try:
        if not user.is_pending_deletion():
            return jsonify({"error": "No pending deletion to cancel"}), 400

        user.cancel_deletion()
        db.session.commit()

        current_app.logger.info(
            f"Account deletion cancelled for user {user.id} ({user.email})"
        )

        return jsonify(
            {"message": "Account deletion cancelled", "status": user.status.value}
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Failed to cancel account deletion for user {user.id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to cancel account deletion"}), 500


@bp.route("/auth/account/deletion-status", methods=["GET"])
@require_auth
def get_deletion_status(user: User) -> Response:
    """
    Get the current account deletion status.

    Returns:
        JSON response with deletion status information
    """
    try:
        if user.is_pending_deletion():
            return jsonify(
                {
                    "is_pending_deletion": True,
                    "deletion_scheduled_for": user.deletion_scheduled_for.isoformat(),
                    "can_cancel": True,
                }
            )
        else:
            return jsonify(
                {
                    "is_pending_deletion": False,
                    "deletion_scheduled_for": None,
                    "can_cancel": False,
                }
            )

    except Exception as e:
        current_app.logger.error(f"Failed to get deletion status: {str(e)}")
        return jsonify({"error": "Failed to get deletion status"}), 500


def _send_deletion_scheduled_email(
    email_service, user: User, deletion_date: datetime
) -> bool:
    """Send email notifying user that account deletion has been scheduled."""
    if not email_service.client:
        return False

    try:
        from sendgrid.helpers.mail import Mail, To, From, Content

        frontend_url = email_service._get_frontend_url()
        settings_url = f"{frontend_url}/settings"

        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #e74c3c;">Account Deletion Scheduled</h2>
              <p>Hello {user.username},</p>
              <p>Your Cookle account has been scheduled for deletion on <strong>{deletion_date.strftime("%B %d, %Y")}</strong>.</p>
              <p>After this date, all your data will be permanently deleted, including:</p>
              <ul>
                <li>Your recipes and images</li>
                <li>Your cookbooks</li>
                <li>Your profile information</li>
                <li>Your subscription (if any)</li>
              </ul>
              <p style="margin: 30px 0;">
                <strong>Changed your mind?</strong> You can cancel the deletion anytime before {deletion_date.strftime("%B %d, %Y")} by visiting your account settings:
              </p>
              <p>
                <a href="{settings_url}"
                   style="background-color: #3498db; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                  Cancel Deletion
                </a>
              </p>
              <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
              <p style="font-size: 12px; color: #7f8c8d;">
                If you didn't request this deletion, please contact support immediately at boudeyz@gmail.com
              </p>
            </div>
          </body>
        </html>
        """

        text_content = f"""
        Hello {user.username},

        Your Cookle account has been scheduled for deletion on {deletion_date.strftime("%B %d, %Y")}.

        After this date, all your data will be permanently deleted.

        Changed your mind? You can cancel the deletion by visiting: {settings_url}

        If you didn't request this deletion, please contact support immediately at boudeyz@gmail.com
        """

        # Get recipient (may be overridden in dev)
        recipient = email_service._get_recipient_email(user.email)

        message = Mail(
            from_email=From(
                email_service._get_from_email(), email_service._get_from_name()
            ),
            to_emails=To(recipient),
            subject="Your Cookle Account is Scheduled for Deletion",
            plain_text_content=Content("text/plain", text_content),
            html_content=Content("text/html", html_content),
        )

        response = email_service.client.send(message)
        return response.status_code in [200, 201, 202]

    except Exception as e:
        current_app.logger.error(f"Failed to send deletion email: {e}")
        return False


# =============================================================================
# Data Export Endpoints
# =============================================================================


@bp.route("/auth/export", methods=["GET"])
@require_auth
def export_user_data(user: User) -> Response:
    """
    Export all user data as a ZIP file.

    Generates a ZIP archive containing:
    - profile.json: User profile information
    - recipes.json: All user recipes with metadata
    - cookbooks.json: All user cookbooks
    - payments.json: Payment history
    - images/: Folder with all recipe images (as URLs, not actual files)

    Returns:
        ZIP file download
    """
    import json
    import zipfile
    import traceback
    from io import BytesIO
    from datetime import datetime
    from flask import send_file

    try:
        current_app.logger.info(f"Starting data export for user {user.id}")

        # Create in-memory ZIP file
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Export profile data
            profile_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "bio": user.bio,
                "avatar_url": user.avatar_url,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "is_verified": user.is_verified,
                "is_premium": user.is_premium(),
                "exported_at": datetime.utcnow().isoformat(),
            }
            zip_file.writestr(
                "profile.json", json.dumps(profile_data, indent=2, ensure_ascii=False)
            )

            # Export recipes
            recipes_data = []
            image_urls = []

            for recipe in user.recipes:
                recipe_dict = {
                    "id": recipe.id,
                    "title": recipe.title,
                    "description": recipe.description,
                    "prep_time": recipe.prep_time,
                    "cook_time": recipe.cook_time,
                    "total_time": recipe.total_time,
                    "servings": recipe.servings,
                    "difficulty": recipe.difficulty.value
                    if recipe.difficulty
                    else None,
                    "cuisine": recipe.cuisine,
                    "category": recipe.category,
                    "is_public": recipe.is_public,
                    "created_at": recipe.created_at.isoformat()
                    if recipe.created_at
                    else None,
                    "updated_at": recipe.updated_at.isoformat()
                    if recipe.updated_at
                    else None,
                    "ingredients": [],
                    "instructions": [],
                    "tags": [],
                    "images": [],
                    "notes": [],
                }

                # Add ingredients
                for ingredient in recipe.ingredients:
                    recipe_dict["ingredients"].append(
                        {
                            "name": ingredient.name,
                            "amount": ingredient.amount,
                            "unit": ingredient.unit,
                            "notes": ingredient.notes,
                            "order": ingredient.order,
                        }
                    )

                # Add instructions
                for instruction in recipe.instructions:
                    recipe_dict["instructions"].append(
                        {
                            "step_number": instruction.step_number,
                            "text": instruction.text,
                            "image_url": instruction.image_url,
                        }
                    )

                # Add tags
                for tag in recipe.tags:
                    recipe_dict["tags"].append(tag.name)

                # Add images
                for image in recipe.images:
                    image_info = {
                        "url": image.url,
                        "is_primary": image.is_primary,
                        "order": image.order,
                    }
                    recipe_dict["images"].append(image_info)
                    if image.url:
                        image_urls.append(
                            {
                                "recipe_id": recipe.id,
                                "recipe_title": recipe.title,
                                "url": image.url,
                            }
                        )

                # Add user's notes for this recipe
                for note in recipe.recipe_notes:
                    if note.user_id == user.id:
                        recipe_dict["notes"].append(
                            {
                                "content": note.content,
                                "created_at": note.created_at.isoformat()
                                if note.created_at
                                else None,
                            }
                        )

                recipes_data.append(recipe_dict)

            zip_file.writestr(
                "recipes.json", json.dumps(recipes_data, indent=2, ensure_ascii=False)
            )

            # Export cookbooks
            cookbooks_data = []
            for cookbook in user.cookbooks:
                cookbook_dict = {
                    "id": cookbook.id,
                    "title": cookbook.title,
                    "description": cookbook.description,
                    "cover_image_url": cookbook.cover_image_url,
                    "author": cookbook.author,
                    "publisher": cookbook.publisher,
                    "isbn": cookbook.isbn,
                    "published_year": cookbook.published_year,
                    "is_purchasable": cookbook.is_purchasable,
                    "price": str(cookbook.price) if cookbook.price else None,
                    "created_at": cookbook.created_at.isoformat()
                    if cookbook.created_at
                    else None,
                    "recipe_ids": [r.id for r in cookbook.recipes],
                }
                cookbooks_data.append(cookbook_dict)

            zip_file.writestr(
                "cookbooks.json",
                json.dumps(cookbooks_data, indent=2, ensure_ascii=False),
            )

            # Export payment history (anonymized payment methods)
            payments_data = []
            for payment in user.payments:
                payment_dict = {
                    "id": payment.id,
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                    "status": payment.status.value
                    if hasattr(payment.status, "value")
                    else str(payment.status),
                    "payment_type": payment.payment_type.value
                    if hasattr(payment.payment_type, "value")
                    else str(payment.payment_type),
                    "created_at": payment.created_at.isoformat()
                    if payment.created_at
                    else None,
                    "description": payment.description,
                }
                payments_data.append(payment_dict)

            zip_file.writestr(
                "payments.json", json.dumps(payments_data, indent=2, ensure_ascii=False)
            )

            # Export image URLs manifest (for reference)
            zip_file.writestr(
                "images/image_manifest.json",
                json.dumps(image_urls, indent=2, ensure_ascii=False),
            )

            # Add README
            readme_content = f"""# Cookle Data Export

Exported on: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
User: {user.username}

## Contents

- profile.json: Your account information
- recipes.json: All your recipes with ingredients, instructions, and tags
- cookbooks.json: Your cookbook collections
- payments.json: Your payment history
- images/image_manifest.json: List of all image URLs

## Note on Images

Images are stored on our CDN (Cloudinary). The image_manifest.json file contains
URLs to your images. You can download them directly from those URLs.

## Data Format

All files are in JSON format and can be opened with any text editor or
imported into other applications.

## Questions?

Contact us at boudeyz@gmail.com
"""
            zip_file.writestr("README.txt", readme_content)

        # Prepare response
        zip_buffer.seek(0)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"cookle_data_export_{timestamp}.zip"

        current_app.logger.info(
            f"Data export completed for user {user.id}. "
            f"Exported {len(recipes_data)} recipes, {len(cookbooks_data)} cookbooks"
        )

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        current_app.logger.error(
            f"Failed to export data for user {user.id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return jsonify({"error": "Failed to export data"}), 500

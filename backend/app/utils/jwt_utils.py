"""
JWT Token utilities for authentication
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import current_app
from app.models import User


class JWTTokenManager:
    """Handles JWT token generation, validation, and decoding"""
    
    @staticmethod
    def generate_token(user: User, expires_in_days: int = 30) -> str:
        """
        Generate a JWT token for the user
        
        Args:
            user: User object
            expires_in_days: Token expiration in days (default 30)
            
        Returns:
            JWT token string
        """
        payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'status': user.status.value,
            'iat': datetime.utcnow(),  # issued at
            'exp': datetime.utcnow() + timedelta(days=expires_in_days)  # expiration
        }
        
        secret_key = current_app.config.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY not configured")
            
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        current_app.logger.info(f"Generated JWT token for user {user.id} ({user.username})")
        
        return token
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload dictionary or None if invalid
        """
        try:
            secret_key = current_app.config.get('SECRET_KEY')
            if not secret_key:
                current_app.logger.error("SECRET_KEY not configured for JWT decoding")
                return None
                
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            current_app.logger.debug(f"Successfully decoded JWT token for user {payload.get('user_id')}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            current_app.logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            current_app.logger.warning(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            current_app.logger.error(f"Error decoding JWT token: {str(e)}")
            return None
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[User]:
        """
        Get user object from JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            User object or None if invalid token or user not found
        """
        payload = JWTTokenManager.decode_token(token)
        if not payload:
            return None
            
        user_id = payload.get('user_id')
        if not user_id:
            current_app.logger.warning("No user_id in JWT token payload")
            return None
            
        # Import here to avoid circular import
        from app.models import User
        
        user = User.query.get(user_id)
        if not user:
            current_app.logger.warning(f"User {user_id} not found in database")
            return None
            
        # Verify user status hasn't changed since token was issued
        if user.status.value != payload.get('status'):
            current_app.logger.warning(f"User {user_id} status changed since token issued")
            return None
            
        current_app.logger.debug(f"Successfully retrieved user {user.id} from JWT token")
        return user
    
    @staticmethod
    def refresh_token(old_token: str) -> Optional[str]:
        """
        Refresh an existing JWT token
        
        Args:
            old_token: Current JWT token
            
        Returns:
            New JWT token or None if old token invalid
        """
        user = JWTTokenManager.get_user_from_token(old_token)
        if not user:
            return None
            
        return JWTTokenManager.generate_token(user)


def extract_jwt_from_request() -> Optional[str]:
    """
    Extract JWT token from request headers
    
    Returns:
        JWT token string or None
    """
    from flask import request
    
    # Check Authorization header first (preferred)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove "Bearer " prefix
    
    # Fallback: check for token in custom header
    token = request.headers.get('X-Auth-Token')
    if token:
        return token
        
    return None
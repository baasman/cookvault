"""
Rate limiting utilities and decorators for selective endpoint protection.
"""

from functools import wraps
from flask import current_app


def apply_rate_limit(limit_string):
    """
    Decorator to apply rate limiting to specific endpoints.

    Args:
        limit_string: Rate limit string (e.g., "10/hour", "100/minute")
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Only apply if limiter is available
            if hasattr(current_app, "limiter"):
                limiter = current_app.limiter
                # Apply the limit dynamically
                limiter.limit(limit_string)(f)
            return f(*args, **kwargs)

        return wrapped

    return decorator


# Pre-configured rate limit decorators for common use cases
rate_limit_auth = apply_rate_limit("20/hour")  # For login/register
rate_limit_upload = apply_rate_limit("50/hour")  # For file uploads
rate_limit_api_write = apply_rate_limit("100/hour")  # For data modifications
rate_limit_api_read = apply_rate_limit("1000/hour")  # For read operations
rate_limit_job_status = apply_rate_limit("5000/hour")  # Very high limit for polling

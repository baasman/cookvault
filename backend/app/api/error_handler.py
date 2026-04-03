"""
Shared API error handling utilities.

Provides a decorator for consistent error handling across API endpoints,
ensuring all errors are logged with tracebacks and returned as JSON.
"""

import logging
import traceback
from functools import wraps

from flask import jsonify

logger = logging.getLogger(__name__)


def api_error_handler(error_message="An unexpected error occurred"):
    """
    Decorator for API endpoints that provides consistent error handling.

    Catches exceptions, logs them with full tracebacks, and returns
    a JSON error response.

    Usage:
        @bp.route("/example", methods=["GET"])
        @api_error_handler("Failed to fetch example")
        def get_example():
            ...
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except ValueError as e:
                logger.warning(f"{error_message}: {e}\n{traceback.format_exc()}")
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"{error_message}: {e}\n{traceback.format_exc()}")
                return jsonify({"error": error_message}), 500

        return wrapper

    return decorator

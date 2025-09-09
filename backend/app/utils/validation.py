"""
Utility functions for request validation.
"""

from flask import request, jsonify
from typing import List, Dict, Any, Union, Tuple


def validate_json_data(request_obj, required_fields: List[str]) -> Union[Dict[str, Any], Tuple[Dict[str, str], int]]:
    """
    Validate JSON request data for required fields.
    
    Args:
        request_obj: Flask request object
        required_fields: List of required field names
        
    Returns:
        Dict with validated data or tuple with error response and status code
    """
    if not request_obj.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request_obj.get_json()
    if not data:
        return jsonify({'error': 'Request body cannot be empty'}), 400
    
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            'error': 'Missing required fields',
            'missing_fields': missing_fields
        }), 400
    
    return data


def validate_email(email: str) -> bool:
    """Basic email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_positive_integer(value, field_name: str) -> Union[int, Tuple[Dict[str, str], int]]:
    """Validate that a value is a positive integer."""
    try:
        int_value = int(value)
        if int_value <= 0:
            return jsonify({'error': f'{field_name} must be a positive integer'}), 400
        return int_value
    except (ValueError, TypeError):
        return jsonify({'error': f'{field_name} must be a valid integer'}), 400
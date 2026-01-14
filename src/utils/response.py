import json
from typing import Any, Dict, Optional


def create_response(
    status_code: int, 
    body: Any, 
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create a standardized API Gateway response"""
    
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body, default=str)
    }


def create_error_response(status_code: int, error_message: str) -> Dict[str, Any]:
    """Create a standardized error response"""
    return create_response(status_code, {
        'error': error_message,
        'success': False
    })


def create_success_response(data: Any, message: str = None) -> Dict[str, Any]:
    """Create a standardized success response"""
    response_body = {
        'success': True,
        'data': data
    }
    
    if message:
        response_body['message'] = message
    
    return create_response(200, response_body)
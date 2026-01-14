import logging
from typing import Dict

from src.constants import DYNAMO_IMAGE_TABLE_NAME
from src.helpers.aws.dynamodb_service import DynamoDBService
from src.utils.response import create_success_response, create_error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for listing images with filters
    
    Query parameters:
    - user_id (optional): Filter by user ID
    - limit (optional): Number of images to return (1-100, default 20)
    - filename (optional): Search in filename (partial match)
    - description (optional): Search in description (partial match)
    """

    logger.info("List images handler started", extra={'request_id': context.aws_request_id})

    try:
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}

        # Extract optional user_id
        user_id = query_params.get('user_id')

        # Validate request parameters
        validation_result = validate_list_request(query_params)
        if not validation_result['valid']:
            logger.warning("List request validation failed",
                           extra={'error': validation_result['message'], 'request_id': context.aws_request_id})
            return create_error_response(400, validation_result['message'])

        # Extract parameters
        limit = int(query_params.get('limit', 20))
        filename_search = query_params.get('filename')
        description_search = query_params.get('description')

        logger.info("Processing list request", extra={
            'user_id': user_id,
            'limit': limit,
            'filename_search': filename_search,
            'description_search': description_search,
            'request_id': context.aws_request_id
        })

        # Prepare search filters
        search_filters = {}
        if user_id:
            search_filters['user_id'] = user_id.strip()
        if filename_search:
            search_filters['filename'] = filename_search.strip()
        if description_search:
            search_filters['description'] = description_search.strip()

        # Initialize service
        dynamodb_service = DynamoDBService(DYNAMO_IMAGE_TABLE_NAME)

        # Get images based on filters
        logger.info("Querying images with search filters",
                    extra={'search_filters': search_filters, 'request_id': context.aws_request_id})
        result = dynamodb_service.list_images_by_search(
            search_filters=search_filters,
            limit=limit
        )

        logger.info("Images retrieved successfully",
                    extra={'count': result['count'], 'request_id': context.aws_request_id})

        # Prepare response data
        response_data = {
            'images': result['images'],
            'count': result['count'],
            'filters_applied': {
                'limit': limit
            }
        }

        logger.info("List operation completed successfully",
                    extra={'count': result['count'], 'filters': search_filters, 'request_id': context.aws_request_id})

        return create_success_response(
            data=response_data,
            message=f"Retrieved {result['count']} images"
        )

    except ValueError as e:
        logger.warning("Invalid parameter value", extra={'error': str(e), 'request_id': context.aws_request_id})
        return create_error_response(400, f"Invalid parameter value: {str(e)}")

    except Exception as e:
        logger.error("Unexpected error in list handler", extra={'error': str(e), 'request_id': context.aws_request_id})
        return create_error_response(500, f"Internal server error: {str(e)}")


def validate_list_request(query_params: Dict) -> Dict[str, any]:
    """Validate list images request parameters"""

    # Validate limit parameter
    limit = query_params.get('limit')
    if limit:
        try:
            limit = int(limit)
            if limit < 1 or limit > 100:
                return {
                    'valid': False,
                    'message': 'limit must be between 1 and 100'
                }
        except ValueError:
            return {'valid': False, 'message': 'limit must be a valid integer'}

    # Validate date_from and date_to
    date_from = query_params.get('date_from')
    date_to = query_params.get('date_to')

    if date_from:
        try:
            date_from = int(date_from)
        except ValueError:
            return {'valid': False, 'message': 'date_from must be a valid timestamp'}

    if date_to:
        try:
            date_to = int(date_to)
        except ValueError:
            return {'valid': False, 'message': 'date_to must be a valid timestamp'}

    if date_from and date_to and date_from > date_to:
        return {'valid': False, 'message': 'date_from cannot be greater than date_to'}

    return {'valid': True}

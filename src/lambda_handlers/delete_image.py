import json
import logging

from src.constants import MONTY_CLOUD_IMAGES_BUCKET_NAME, DYNAMO_IMAGE_TABLE_NAME
from src.helpers.aws.s3_service import S3Service
from src.helpers.aws.dynamodb_service import DynamoDBService
from src.utils.response import create_success_response, create_error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for deleting an image
    
    Path parameters:
    - image_id (required): The image ID to delete
    
    """

    logger.info("Delete image handler started", extra={'request_id': context.aws_request_id})

    try:
        # Get path parameters
        path_params = event.get('pathParameters') or {}
        image_id = path_params.get('image_id')

        if not image_id:
            logger.warning("Missing image_id parameter", extra={'request_id': context.aws_request_id})
            return create_error_response(400, "image_id path parameter is required")

        # Validate image_id format
        if not validate_image_id(image_id):
            logger.warning("Invalid image_id format",
                           extra={'image_id': image_id, 'request_id': context.aws_request_id})
            return create_error_response(400, "Invalid image_id format")

        logger.info("Processing delete request", extra={'image_id': image_id, 'request_id': context.aws_request_id})

        # Initialize services
        s3_service = S3Service(MONTY_CLOUD_IMAGES_BUCKET_NAME)
        dynamodb_service = DynamoDBService(DYNAMO_IMAGE_TABLE_NAME)

        # Get image metadata first to verify it exists and get S3 key
        logger.info("Retrieving image metadata", extra={'image_id': image_id, 'request_id': context.aws_request_id})
        metadata_result = dynamodb_service.get_image_metadata(image_id)
        metadata = metadata_result['metadata']
        s3_key = metadata['s3_key']

        # Delete from S3 first
        logger.info("Deleting file from S3", extra={'s3_key': s3_key, 'request_id': context.aws_request_id})
        s3_service.delete_file(s3_key)
        logger.info("S3 deletion successful", extra={'s3_key': s3_key, 'request_id': context.aws_request_id})

        # Delete metadata from DynamoDB
        logger.info("Deleting metadata from DynamoDB",
                    extra={'image_id': image_id, 'request_id': context.aws_request_id})
        metadata_delete_result = dynamodb_service.delete_image_metadata(image_id)
        logger.info("Metadata deletion successful", extra={'image_id': image_id, 'request_id': context.aws_request_id})

        # Return success response
        logger.info("Delete operation completed successfully",
                    extra={'image_id': image_id, 'request_id': context.aws_request_id})
        response_data = {
            'image_id': image_id,
            'deleted_metadata': metadata_delete_result['deleted_metadata']
        }

        return create_success_response(
            data=response_data,
            message="Image deleted successfully"
        )

    except Exception as e:
        logger.error("Unexpected error in delete handler",
                     extra={'error': str(e), 'request_id': context.aws_request_id})
        return create_error_response(500, f"Internal server error: {str(e)}")


def validate_image_id(image_id: str) -> bool:
    """Validate image_id format (UUID)"""
    if not image_id:
        return False

    import uuid
    try:
        uuid.UUID(image_id)
        return True
    except ValueError:
        return False

import base64
import logging
from src.constants import MONTY_CLOUD_IMAGES_BUCKET_NAME, DYNAMO_IMAGE_TABLE_NAME
from src.helpers.aws.s3_service import S3Service
from src.helpers.aws.dynamodb_service import DynamoDBService
from src.utils.response import create_success_response, create_error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for getting/downloading an image
    
    Path parameters:
    - image_id (required): The image ID to retrieve
    
    Query parameters:
    - download (optional): If 'true', returns the image as a download attachment
    - presigned (optional): If 'true', returns a presigned URL instead of the file data
    - expires (optional): Expiration time for presigned URL in seconds (default 3600)
    """

    logger.info("Get image handler started", extra={'request_id': context.aws_request_id})
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

        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        download_mode = query_params.get('download', '').lower() == 'true'
        presigned_mode = query_params.get('presigned', '').lower() == 'true'
        expires_str = query_params.get('expires', '3600')

        logger.info("Processing get request", extra={
            'image_id': image_id, 'presigned_mode': presigned_mode,
            'download_mode': download_mode, 'request_id': context.aws_request_id
        })

        try:
            expires = int(expires_str)
            if expires < 1 or expires > 86400:  # 1 second to 24 hours
                expires = 3600
        except ValueError:
            expires = 3600

        # Initialize services
        dynamodb_service = DynamoDBService(DYNAMO_IMAGE_TABLE_NAME)
        s3_service = S3Service(MONTY_CLOUD_IMAGES_BUCKET_NAME)

        # Get image metadata from DynamoDB
        logger.info("Retrieving image metadata", extra={'image_id': image_id, 'request_id': context.aws_request_id})
        metadata_result = dynamodb_service.get_image_metadata(image_id)
        metadata = metadata_result['metadata']
        s3_key = metadata['s3_key']

        # If presigned URL requested, return that
        if presigned_mode:
            logger.info("Generating presigned URL",
                        extra={'s3_key': s3_key, 'expires': expires, 'request_id': context.aws_request_id})
            presigned_result = s3_service.generate_presigned_url(
                s3_key=s3_key,
                expiration=expires,
                http_method='GET'
            )

            logger.info("Presigned URL generated successfully", extra={'request_id': context.aws_request_id})

            response_data = {
                'image_id': image_id,
                'presigned_url': presigned_result['presigned_url'],
                'expires_in': expires,
                'metadata': metadata
            }

            return create_success_response(
                data=response_data,
                message="Presigned URL generated successfully"
            )

        # Else, Get the actual file from S3
        logger.info("Retrieving file from S3", extra={'s3_key': s3_key, 'request_id': context.aws_request_id})
        file_result = s3_service.get_file(s3_key)

        logger.info("File retrieved successfully from S3",
                    extra={'file_size': len(file_result['file_data']), 'request_id': context.aws_request_id})

        # Encode file data as base64
        file_data_base64 = base64.b64encode(file_result['file_data']).decode('utf-8')

        if download_mode:
            # Prepare response headers
            response_headers = {
                'Content-Type': file_result['content_type'] or metadata['content_type'],
                'Content-Length': str(len(file_result['file_data']))
            }

            # Force download with original filename
            filename = metadata['filename']
            response_headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            # For download mode, return the file directly
            return {
                'statusCode': 200,
                'headers': response_headers,
                'body': file_data_base64,
                'isBase64Encoded': True
            }
        else:
            # For API mode, return JSON with file data and metadata
            response_data = {
                'image_id': image_id,
                'file_data': file_data_base64,
                'filename': metadata['filename'],
                'content_type': metadata['content_type'],
                'file_size': metadata['file_size'],
                'metadata': metadata
            }

            logger.info("Get operation completed successfully",
                        extra={'image_id': image_id, 'download_mode': download_mode,
                               'request_id': context.aws_request_id})
            return create_success_response(
                data=response_data,
                message="Image retrieved successfully"
            )

    except Exception as e:
        logger.error("Unexpected error in get handler", extra={'error': str(e), 'request_id': context.aws_request_id})
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

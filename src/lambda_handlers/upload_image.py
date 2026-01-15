import json
import mimetypes
import os
import uuid
import logging
from typing import Dict

from botocore.exceptions import ValidationError

from src.constants import MONTY_CLOUD_IMAGES_BUCKET_NAME, DYNAMO_IMAGE_TABLE_NAME
from src.models.image_metadata import ImageMetadata
from src.helpers.aws.s3_service import S3Service
from src.helpers.aws.dynamodb_service import DynamoDBService
from src.utils.response import create_success_response, create_error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for image upload
    
    Expected request body:
    {
        "filename": "photo.jpg",
        "file_data": "base64_encoded_data",
        "user_id": "user123",
        "description": "A beautiful sunset"
    }
    """

    logger.info("Upload image handler started", extra={'request_id': context.aws_request_id})

    try:
        # Parse request body
        body = {}
        if event.get('body'):
            if event.get('isBase64Encoded'):
                import base64
                body = json.loads(base64.b64decode(event['body']).decode('utf-8'))
            else:
                body = json.loads(event['body'])

        headers = event.get('headers', {})

        # Validate request
        validate_upload_request(body)

        # Extract data from request
        filename = body['filename']
        file_data = body['file_data']
        user_id = body['user_id']
        description = body.get('description', '')

        logger.info("Processing upload", extra={
            'user_id': user_id,
            'filename': filename,
            'description': description,
            'request_id': context.aws_request_id
        })

        # Initialize services
        s3_service = S3Service(MONTY_CLOUD_IMAGES_BUCKET_NAME)
        dynamodb_service = DynamoDBService(DYNAMO_IMAGE_TABLE_NAME)

        # Generate unique image ID and S3 key
        image_id = str(uuid.uuid4())
        s3_key = f"{user_id}/{image_id}/{filename}"

        # Get content type and file size
        content_type = get_content_type_from_filename(filename)
        import base64
        file_size = len(base64.b64decode(file_data))

        # Create metadata object
        metadata = ImageMetadata(
            image_id=image_id,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            s3_bucket=MONTY_CLOUD_IMAGES_BUCKET_NAME,
            s3_key=s3_key,
            description=description
        )

        # Upload file to S3, upload will raise exception if any
        logger.info("Starting S3 upload", extra={'s3_key': s3_key, 'request_id': context.aws_request_id})
        upload_result = s3_service.upload_file(
            file_data=file_data,
            s3_key=s3_key,
            content_type=content_type,
            metadata={
                'user_id': user_id,
                'image_id': image_id,
                'original_filename': filename
            }
        )

        logger.info("S3 upload successful", extra={'s3_key': s3_key, 'request_id': context.aws_request_id})

        # Save metadata to DynamoDB
        logger.info("Saving metadata to DynamoDB", extra={'image_id': image_id, 'request_id': context.aws_request_id})
        save_result = dynamodb_service.save_image_metadata(metadata)
        logger.info("Metadata saved successfully", extra={'image_id': image_id, 'request_id': context.aws_request_id})

        # Generate presigned URL for immediate access
        presigned_result = s3_service.generate_presigned_url(s3_key)

        response_data = {
            'image_id': image_id,
            'filename': filename,
            'user_id': user_id,
            'file_size': file_size,
            'content_type': content_type,
            'description': description,
            'upload_timestamp': metadata.upload_timestamp,
            's3_key': s3_key,
            'download_url': presigned_result['presigned_url']
        }
        logger.info("Upload completed successfully",
                    extra={'image_id': image_id, 'user_id': user_id, 'request_id': context.aws_request_id})

        return create_success_response(
            data=response_data,
            message="Image uploaded successfully"
        )

    except ValueError as e:
        logger.warning("Upload validation failed",
                       extra={'error': str(e), 'request_id': context.aws_request_id})
        return create_error_response(400, str(e))

    except Exception as e:
        logger.error("Unexpected error in upload handler",
                     extra={'error': str(e), 'request_id': context.aws_request_id})
        return create_error_response(500, f"Something went wrong while uploading the image. Reason: {str(e)}")


def validate_upload_request(body: Dict):
    """Validate image upload request"""
    try:
        required_fields = ['filename', 'file_data', 'user_id']
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            raise Exception(f'Missing required fields: {", ".join(missing_fields)}')

        # Validate file data is base64 encoded
        file_data = body['file_data']
        import base64
        base64.b64decode(file_data, validate=True)

        # Validate file extension
        filename = body['filename']
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            raise Exception(f'File extension not allowed. Allowed: {", ".join(allowed_extensions)}')

        # Validate file size (approximate from base64)
        file_size = len(base64.b64decode(file_data))
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            raise Exception(f'File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)')

    except Exception as e:
        raise ValueError(f'{str(e)}')


def get_content_type_from_filename(filename: str) -> str:
    """Get content type from filename"""
    content_type, _ = mimetypes.guess_type(filename)

    # Default mappings for common image types
    if not content_type:
        extension = filename.lower().split('.')[-1]
        type_mappings = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'bmp': 'image/bmp'
        }
        content_type = type_mappings.get(extension, 'application/octet-stream')

    return content_type

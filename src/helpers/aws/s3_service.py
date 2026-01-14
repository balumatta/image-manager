import base64
import boto3
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError


class S3Service:
    def __init__(self, bucket_name):
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name

        if not self.bucket_name:
            raise ValueError("IMAGES_BUCKET environment variable not set")

    def upload_file(self, file_data: str, s3_key: str, content_type: str,
                    metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Upload base64 encoded file data to S3
        
        Args:
            file_data: Base64 encoded file data
            s3_key: S3 object key
            content_type: File content type
            metadata: Optional metadata to store with the file
        
        Returns:
            Dict with upload result
        """
        try:
            # Decode base64 file data
            file_bytes = base64.b64decode(file_data)

            # Prepare upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
                'Body': file_bytes,
                'ContentType': content_type
            }

            if metadata:
                upload_params['Metadata'] = metadata

            # Upload to S3
            response = self.s3_client.put_object(**upload_params)

            return {
                'success': True,
                'bucket': self.bucket_name,
                's3_key': s3_key,
                'etag': response.get('ETag'),
                'version_id': response.get('VersionId')
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f'S3 upload failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'S3 upload failed. Details - {str(e)}')

    def get_file(self, s3_key: str) -> Dict[str, Any]:
        """
        Get file from S3
        
        Args:
            s3_key: S3 object key
        
        Returns:
            Dict with file data and metadata
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            file_data = response['Body'].read()

            return {
                'success': True,
                'file_data': file_data,
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {}),
                'last_modified': response.get('LastModified'),
                'content_length': response.get('ContentLength')
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise Exception('File not found')
            raise Exception(f'S3 get failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'S3 get failed. Details - {str(e)}')

    def delete_file(self, s3_key: str) -> Dict[str, Any]:
        """
        Delete file from S3
        
        Args:
            s3_key: S3 object key
        
        Returns:
            Dict with deletion result
        """
        try:
            response = self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            return {
                'success': True,
                'deleted_marker': response.get('DeleteMarker', False),
                'version_id': response.get('VersionId')
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f'S3 delete failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'S3 delete failed. Details - {str(e)}')

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600, http_method: str = 'GET') -> Dict[str, Any]:
        """
        Generate presigned URL for direct S3 access
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration in seconds (default 1 hour)
            http_method: HTTP method (GET, PUT, etc.)
        
        Returns:
            Dict with presigned URL
        """
        try:
            method_mapping = {
                'GET': 'get_object',
                'PUT': 'put_object'
            }

            client_method = method_mapping.get(http_method, 'get_object')

            presigned_url = self.s3_client.generate_presigned_url(
                client_method,
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )

            return {
                'success': True,
                'presigned_url': presigned_url,
                'expires_in': expiration
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f'Presigned URL generation failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'Presigned URL generation failed. Details - {str(e)}')

    def file_exists(self, s3_key: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return False
            raise Exception(f'S3 head_object failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'S3 file_exists check failed. Details - {str(e)}')

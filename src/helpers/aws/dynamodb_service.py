import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from src.models.image_metadata import ImageMetadata


class DynamoDBService:
    def __init__(self, table_name):
        self.dynamodb_client = boto3.client('dynamodb')
        self.table_name = table_name

        if not self.table_name:
            raise ValueError("Table name is not mentioned")

    def save_image_metadata(self, metadata: ImageMetadata) -> Dict[str, Any]:
        """
        Save image metadata to DynamoDB
        
        Args:
            metadata: ImageMetadata object
        
        Returns:
            Dict with save result
        """
        try:
            item = metadata.to_dynamodb_item()

            response = self.dynamodb_client.put_item(
                TableName=self.table_name,
                Item=item,
                ConditionExpression='attribute_not_exists(image_id)'  # Prevent overwrites
            )

            return {
                'success': True,
                'image_id': metadata.image_id
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f'DynamoDB save failed due to client error {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'DynamoDB save failed. Details - {str(e)}')

    def get_image_metadata(self, image_id: str) -> Dict[str, Any]:
        """
        Get image metadata by ID
        
        Args:
            image_id: Image ID
        
        Returns:
            Dict with image metadata or error
        """
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.table_name,
                Key={'image_id': {'S': image_id}}
            )

            if 'Item' not in response:
                raise Exception('Image not found')

            metadata = ImageMetadata.from_dynamodb_item(response['Item'])

            return {
                'success': True,
                'metadata': metadata.dict()
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f'DynamoDB get failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'DynamoDB get failed. Details - {str(e)}')

    def list_images_by_user(
            self,
            user_id: str,
            limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        List images for a specific user
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of items to return
        
        Returns:
            Dict with list of images
        """
        try:
            query_params = {
                'TableName': self.table_name,
                'IndexName': 'UserIndex',
                'KeyConditionExpression': 'user_id = :user_id',
                'ExpressionAttributeValues': {
                    ':user_id': {'S': user_id}
                },
                'ScanIndexForward': False  # Sort by timestamp descending (newest first)
            }

            # Add limit
            if limit:
                query_params['Limit'] = limit

            response = self.dynamodb_client.query(**query_params)

            # Convert items to metadata objects
            images = []
            for item in response.get('Items', []):
                metadata = ImageMetadata.from_dynamodb_item(item)
                images.append(metadata.dict())

            return {
                'success': True,
                'images': images,
                'count': len(images)
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f'DynamoDB query failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'DynamoDB query failed. Details - {str(e)}')

    def list_images_by_search(
            self,
            search_filters: Dict[str, str],
            limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        List images filtered by search criteria
        
        Args:
            search_filters: Dict with search criteria (user_id, filename, description)
            limit: Maximum number of items to return
        
        Returns:
            Dict with filtered images
        """
        try:
            user_id = search_filters.get('user_id')
            filename_search = search_filters.get('filename')
            description_search = search_filters.get('description')
            
            # If user_id is specified, use efficient user query
            if user_id:
                all_images = self.list_images_by_user(user_id, limit=None)
            else:
                # Scan entire table if no user_id (less efficient)
                all_images = self._scan_all_images()

            # Apply filename and description filters
            filtered_images = []
            for image in all_images['images']:
                matches = True
                
                # Check filename filter
                if filename_search and filename_search.lower() not in image.get('filename', '').lower():
                    matches = False
                
                # Check description filter  
                if description_search and description_search.lower() not in image.get('description', '').lower():
                    matches = False
                
                if matches:
                    filtered_images.append(image)
                    
                # Apply limit
                if limit and len(filtered_images) >= limit:
                    break

            return {
                'success': True,
                'images': filtered_images,
                'count': len(filtered_images)
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f'DynamoDB search failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'DynamoDB search failed. Details - {str(e)}')

    def delete_image_metadata(self, image_id: str) -> Dict[str, Any]:
        """
        Delete image metadata from DynamoDB
        
        Args:
            image_id: Image ID to delete
        
        Returns:
            Dict with deletion result
        """
        try:
            response = self.dynamodb_client.delete_item(
                TableName=self.table_name,
                Key={'image_id': {'S': image_id}},
                ConditionExpression='attribute_exists(image_id)',  # Ensure item exists
                ReturnValues='ALL_OLD'
            )

            if 'Attributes' not in response:
                raise Exception('Image not found')

            # Return the deleted item data
            deleted_metadata = ImageMetadata.from_dynamodb_item(response['Attributes'])

            return {
                'success': True,
                'deleted_metadata': deleted_metadata.dict()
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                raise Exception('Image not found')
            raise Exception(f'DynamoDB delete failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'DynamoDB delete failed. Details - {str(e)}')

    def _scan_all_images(self) -> Dict[str, Any]:
        """
        Scan all images in the table (used when no user_id filter)
        
        Returns:
            Dict with all images
        """
        try:
            scan_params = {
                'TableName': self.table_name
            }

            response = self.dynamodb_client.scan(**scan_params)

            # Convert items to metadata objects
            images = []
            for item in response.get('Items', []):
                metadata = ImageMetadata.from_dynamodb_item(item)
                images.append(metadata.dict())

            return {
                'success': True,
                'images': images,
                'count': len(images)
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f'DynamoDB scan failed due to client error: {error_code}. Details - {str(e)}')
        except Exception as e:
            raise Exception(f'DynamoDB scan failed. Details - {str(e)}')

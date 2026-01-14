import uuid
import time
from typing import Optional
from pydantic import BaseModel, validator


class ImageMetadata(BaseModel):
    image_id: str
    user_id: str
    filename: str
    content_type: str
    file_size: int
    upload_timestamp: int
    s3_bucket: str
    s3_key: str
    description: Optional[str] = None

    @validator('image_id', pre=True, always=True)
    def set_image_id(cls, v):
        return v or str(uuid.uuid4())

    @validator('upload_timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or int(time.time())

    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = [
            'image/jpeg', 'image/jpg', 'image/png', 
            'image/gif', 'image/webp', 'image/bmp'
        ]
        if v not in allowed_types:
            raise ValueError(f'Content type {v} not allowed. Allowed types: {allowed_types}')
        return v

    @validator('file_size')
    def validate_file_size(cls, v):
        max_size = 10 * 1024 * 1024  # 10MB
        if v > max_size:
            raise ValueError(f'File size {v} exceeds maximum allowed size of {max_size} bytes')
        return v

    def to_dynamodb_item(self) -> dict:
        """Convert to DynamoDB item format"""
        return {
            'image_id': {'S': self.image_id},
            'user_id': {'S': self.user_id},
            'filename': {'S': self.filename},
            'content_type': {'S': self.content_type},
            'file_size': {'N': str(self.file_size)},
            'upload_timestamp': {'N': str(self.upload_timestamp)},
            's3_bucket': {'S': self.s3_bucket},
            's3_key': {'S': self.s3_key},
            'description': {'S': self.description or ''}
        }

    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'ImageMetadata':
        """Create from DynamoDB item"""
        return cls(
            image_id=item['image_id']['S'],
            user_id=item['user_id']['S'],
            filename=item['filename']['S'],
            content_type=item['content_type']['S'],
            file_size=int(item['file_size']['N']),
            upload_timestamp=int(item['upload_timestamp']['N']),
            s3_bucket=item['s3_bucket']['S'],
            s3_key=item['s3_key']['S'],
            description=item.get('description', {}).get('S', '')
        )
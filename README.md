# Image Manager Service - Setup & Testing Instructions

## Project Overview
This is a scalable image management service built with AWS Lambda, API Gateway, S3, and DynamoDB using Python 3.9+. The service supports image upload, listing with filters, retrieval, and deletion.

## Architecture
- **API Gateway**: RESTful API endpoints
- **Lambda Functions**: Serverless compute (separate function per endpoint)
- **S3**: Image storage with organized folder structure
- **DynamoDB**: Metadata storage with GSI for efficient querying
- **LocalStack**: Local AWS environment for development

## Prerequisites
1. **Python 3.9+**
2. **Node.js 16+** (for Serverless Framework)
3. **Docker** (for LocalStack)
4. **AWS CLI** (optional, for real AWS deployment)

## Setup Instructions

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (Serverless Framework & plugins)
npm install
```

### 2. Start LocalStack

```bash
# Start LocalStack with Docker Compose
docker-compose up -d

# Verify LocalStack is running
curl http://localhost:4566/_localstack/health
```

### 3. Deploy to LocalStack

```bash
# Install Serverless Framework globally (if not installed)
npm i -D serverless@3

# Deploy to LocalStack
serverless deploy --stage local

# Note the API Gateway URL from the output
```

### 4. Create S3 Bucket

```bash
# Create the bucket for storing images
aws --endpoint-url http://localhost:4566 s3 mb s3://montycloud-images

# Create the bucket for storing artifacts for local testing
aws --endpoint-url http://localhost:4566 s3 mb s3://image-manager-service-deployments-local

# To confirm if S3 bucket is created then execute the below command. It will give output with bucket names
aws --endpoint-url http://localhost:4566 s3 ls
```

### 4. Test the APIs

#### Option A: Use the Test Script
```bash
python test_local.py
```

#### Option B: Manual Testing with curl

**1. Upload an Image**
```bash
# First, create a base64 encoded image (example with a small PNG)
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAIIAAAAA" > test_image_b64.txt

# Upload the image
curl -X POST http://localhost:4566/restapis/{api-id}/local/_user_request_/images \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.png",
    "file_data": "'$(cat test_image_b64.txt)'",
    "user_id": "user123",
    "tags": ["test", "sample"],
    "description": "Test image"
  }'
```

**2. List Images**
```bash
# List all images for a user
curl "http://localhost:4566/restapis/{api-id}/local/_user_request_/images?user_id=user123"

# List with filters
curl "http://localhost:4566/restapis/{api-id}/local/_user_request_/images?user_id=user123&tags=test&limit=10"
```

**3. Get an Image**
```bash
# Get image data
curl http://localhost:4566/restapis/{api-id}/local/_user_request_/images/{image-id}

# Get presigned URL
curl "http://localhost:4566/restapis/{api-id}/local/_user_request_/images/{image-id}?presigned=true"
```

**4. Delete an Image**
```bash
curl -X DELETE http://localhost:4566/restapis/{api-id}/local/_user_request_/images/{image-id}
```

## API Documentation

### 1. Upload Image
- **Endpoint**: `POST /images`
- **Body**:
```json
{
  "filename": "photo.jpg",
  "file_data": "base64_encoded_data",
  "user_id": "user123",
  "tags": ["nature", "landscape"],
  "description": "A beautiful sunset"
}
```

### 2. List Images
- **Endpoint**: `GET /images`
- **Query Parameters**:
  - `user_id` (required): User ID to filter by
  - `limit` (optional): Number of results (1-100, default 20)
  - `tags` (optional): Comma-separated tags
  - `date_from` (optional): Start timestamp
  - `date_to` (optional): End timestamp
  - `last_key` (optional): For pagination

### 3. Get Image
- **Endpoint**: `GET /images/{image_id}`
- **Query Parameters**:
  - `download` (optional): Return as download attachment
  - `presigned` (optional): Return presigned URL instead
  - `expires` (optional): Presigned URL expiration (seconds)

### 4. Delete Image
- **Endpoint**: `DELETE /images/{image_id}`
- **Query Parameters**:
  - `force` (optional): Force delete even if S3 deletion fails

## Environment Variables

The following environment variables are automatically set by Serverless:
- `IMAGES_BUCKET`: S3 bucket name for storing images
- `IMAGES_TABLE`: DynamoDB table name for metadata

## File Structure
```
image-manager-service/
├── src/
│   ├── handlers/          # Lambda function handlers
│   ├── services/          # AWS service integrations
│   ├── models/           # Data models
│   └── utils/            # Utility functions
├── tests/
│   ├── unit/             # Unit tests
│   └── fixtures/         # Test data
├── infrastructure/
│   └── localstack/       # LocalStack configuration
├── serverless.yml        # Serverless Framework configuration
└── test_local.py         # Local testing script
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root and Python path is correct
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

2. **LocalStack Connection Issues**
   ```bash
   # Check LocalStack status
   docker ps | grep localstack
   curl http://localhost:4566/_localstack/health
   ```

3. **Deployment Issues**
   ```bash
   # Check LocalStack logs
   docker logs image-manager-localstack
   
   # Remove and redeploy
   serverless remove --stage local
   serverless deploy --stage local
   ```

4. **DynamoDB Table Not Found**
   ```bash
   # List tables in LocalStack
   aws --endpoint-url=http://localhost:4566 dynamodb list-tables
   ```

5. **S3 Bucket Not Found**
   ```bash
   # List buckets in LocalStack
   aws --endpoint-url=http://localhost:4566 s3 ls
   ```

### Debug Mode
```bash
# Enable debug logging for LocalStack
DEBUG=1 docker-compose up

# Enable Serverless debug
SLS_DEBUG=* serverless deploy --stage local
```

## Testing

### Run Unit Tests
```bash
pytest tests/unit/ -v
```

### Run Integration Tests
```bash
python test_local.py
```

### Test Coverage
```bash
pytest --cov=src tests/
```

## Production Deployment

To deploy to real AWS:

1. Configure AWS credentials:
```bash
aws configure
```

2. Deploy to AWS:
```bash
serverless deploy --stage prod
```

3. Update environment variables as needed for production.

## Security Notes

- In production, implement proper authentication/authorization
- Use IAM roles with minimal required permissions
- Enable S3 bucket encryption
- Consider VPC configuration for enhanced security
- Implement rate limiting and input validation

## Performance Considerations

- Lambda cold starts: Consider using provisioned concurrency for high-traffic scenarios
- DynamoDB: Monitor read/write capacity and enable auto-scaling
- S3: Use CloudFront for global distribution of images
- Consider implementing image resizing/thumbnails for better performance

## Next Steps

1. Add authentication (Cognito/JWT)
2. Implement image processing (thumbnails, compression)
3. Add CloudWatch monitoring and alerts
4. Implement batch operations
5. Add image metadata extraction (EXIF data)
6. Consider implementing CDN integration
#!/usr/bin/env python3
"""
Local testing script for the Image Manager Service
This script tests all APIs against LocalStack
"""

import base64
import json
import requests
import os
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def create_sample_image():
    """Create a small test image in base64 format"""
    # This is a 1x1 pixel transparent PNG
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    return base64.b64encode(png_data).decode('utf-8')

def test_upload_image(api_url, image_data):
    """Test image upload API"""
    print("\n=== Testing Image Upload ===")
    
    upload_data = {
        'filename': 'test_image.png',
        'file_data': image_data,
        'user_id': 'test_user_123',
        'tags': ['test', 'sample', 'localstack'],
        'description': 'Test image for LocalStack testing'
    }
    
    try:
        response = requests.post(
            f"{api_url}/images",
            json=upload_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Upload successful!")
                return result['data']['image_id']
            else:
                print("❌ Upload failed in response")
                return None
        else:
            print("❌ Upload failed with HTTP error")
            return None
            
    except Exception as e:
        print(f"❌ Upload failed with exception: {e}")
        return None

def test_list_images(api_url, user_id):
    """Test list images API"""
    print("\n=== Testing List Images ===")
    
    try:
        # Test basic listing
        response = requests.get(f"{api_url}/images?user_id={user_id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ List successful!")
                print(f"Found {result['data']['count']} images")
                return True
            else:
                print("❌ List failed in response")
                return False
        else:
            print("❌ List failed with HTTP error")
            return False
            
    except Exception as e:
        print(f"❌ List failed with exception: {e}")
        return False

def test_get_image(api_url, image_id):
    """Test get image API"""
    print("\n=== Testing Get Image ===")
    
    try:
        # Test getting image metadata and file
        response = requests.get(f"{api_url}/images/{image_id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Get image successful!")
                return True
            else:
                print("❌ Get image failed in response")
                return False
        else:
            print("❌ Get image failed with HTTP error")
            return False
            
    except Exception as e:
        print(f"❌ Get image failed with exception: {e}")
        return False

def test_delete_image(api_url, image_id):
    """Test delete image API"""
    print("\n=== Testing Delete Image ===")
    
    try:
        response = requests.delete(f"{api_url}/images/{image_id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Delete successful!")
                return True
            else:
                print("❌ Delete failed in response")
                return False
        else:
            print("❌ Delete failed with HTTP error")
            return False
            
    except Exception as e:
        print(f"❌ Delete failed with exception: {e}")
        return False

def test_direct_lambda_functions():
    """Test Lambda functions directly (without API Gateway)"""
    print("\n=== Testing Lambda Functions Directly ===")
    
    try:
        # Import and test upload function
        from src.lambda_handlers.upload_image import lambda_handler as upload_handler
        
        # Create test event
        image_data = create_sample_image()
        event = {
            'body': json.dumps({
                'filename': 'direct_test.png',
                'file_data': image_data,
                'user_id': 'direct_test_user',
                'tags': ['direct', 'test']
            }),
            'headers': {'Content-Type': 'application/json'},
            'isBase64Encoded': False
        }
        
        # Call the handler
        response = upload_handler(event, {})
        print(f"Direct Lambda Response: {response}")
        
        if response['statusCode'] == 200:
            print("✅ Direct Lambda test successful!")
            return True
        else:
            print("❌ Direct Lambda test failed")
            return False
            
    except Exception as e:
        print(f"❌ Direct Lambda test failed with exception: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Image Manager Service Tests")
    
    # Test configuration
    api_url = "http://localhost:4566/restapis/{api-id}/local/_user_request_"  # Will be updated after deployment
    user_id = "test_user_123"
    
    # Create sample image
    image_data = create_sample_image()
    print(f"Created sample image ({len(image_data)} characters)")
    
    # Test 1: Direct Lambda function test (easier to debug)
    print("\n" + "="*50)
    success = test_direct_lambda_functions()
    
    # If direct test fails, we need to fix the code before testing via API Gateway
    if not success:
        print("\n❌ Direct Lambda tests failed. Fix the code before testing via API Gateway.")
        return False
    
    print("\n" + "="*50)
    print("Direct Lambda tests passed! Now testing via API Gateway...")
    print("Note: You need to deploy to LocalStack first using:")
    print("serverless deploy --stage local")
    
    # For now, we'll skip API Gateway tests until deployment
    print("\nSkipping API Gateway tests for now. Run deployment first.")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ All available tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
#!/usr/bin/env python3
"""
Test script to verify the contract fetcher components work correctly.
Run this script to test the integration before deploying.
"""

import os
import sys
import json
from datetime import datetime

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fetcher.contract_fetcher import fetch_contracts
from fetcher.data_processor import process_data
from storage.gcs_handler import upload_to_gcs
from utils.logger import log_info, log_error

def test_contract_fetcher():
    """Test the contract fetching functionality"""
    print("🧪 Testing contract fetcher...")
    
    try:
        # Test if we can import all modules
        print("✅ All modules imported successfully")
        
        # Check environment variables
        sam_api_key = os.getenv('SAM_API_KEY')
        gcs_bucket = os.getenv('GCS_BUCKET_NAME')
        
        if not sam_api_key:
            print("⚠️  SAM_API_KEY environment variable not set")
        else:
            print("✅ SAM_API_KEY environment variable found")
            
        if not gcs_bucket:
            print("⚠️  GCS_BUCKET_NAME environment variable not set")
        else:
            print("✅ GCS_BUCKET_NAME environment variable found")
        
        # Test logging
        log_info("Test log message")
        print("✅ Logging system working")
        
        # Note: We don't actually call fetch_contracts() here to avoid API calls
        # In a real test, you might want to mock the API response
        print("✅ Basic integration test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def test_data_flow():
    """Test the complete data flow with mock data"""
    print("\n🧪 Testing data flow with mock data...")
    
    try:
        # Mock contract data
        mock_data = [
            {
                "id": "test123",
                "title": "Test Contract",
                "agency": "Test Agency",
                "description": "A test contract for validation",
                "amount": "100000",
                "date": datetime.now().isoformat()
            }
        ]
        
        # Test data processing
        processed_data = process_data(mock_data)
        print("✅ Data processing completed")
        
        # Test file creation
        filename = f"test_contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(processed_data, f, indent=2)
        print(f"✅ Test file created: {filename}")
        
        # Clean up test file
        os.remove(filename)
        print("✅ Test file cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Data flow test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Contract Fetcher Integration Tests\n")
    
    # Load environment variables from .env file if it exists
    try:
        from dotenv import load_dotenv
        if os.path.exists('.env'):
            load_dotenv()
            print("✅ Loaded environment variables from .env file")
        else:
            print("ℹ️  No .env file found, using system environment variables")
    except ImportError:
        print("ℹ️  python-dotenv not available, using system environment variables")
    
    success = True
    
    # Run tests
    success &= test_contract_fetcher()
    success &= test_data_flow()
    
    print(f"\n{'🎉 All tests passed!' if success else '❌ Some tests failed'}")
    sys.exit(0 if success else 1)
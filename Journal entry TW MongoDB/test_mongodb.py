#!/usr/bin/env python
"""
MongoDB Connection Test Script
Run this script to verify your MongoDB connection is working correctly.
"""

import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_mongodb_connection():
    """Test MongoDB connection and database operations"""
    
    print("=" * 60)
    print("MongoDB Connection Test")
    print("=" * 60)
    print()
    
    # Get connection details from environment
    mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.environ.get("MONGODB_DB_NAME", "journal_entry_audit")
    
    print(f"Connection URI: {mongodb_uri}")
    print(f"Database Name: {db_name}")
    print()
    
    try:
        # Step 1: Connect to MongoDB
        print("Step 1: Connecting to MongoDB...")
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        
        # Step 2: Ping the server
        print("Step 2: Pinging MongoDB server...")
        client.admin.command('ping')
        print("✓ Successfully connected to MongoDB!")
        print()
        
        # Step 3: Access database
        print("Step 3: Accessing database...")
        db = client[db_name]
        print(f"✓ Database '{db_name}' accessed successfully!")
        print()
        
        # Step 4: List collections
        print("Step 4: Listing existing collections...")
        collections = db.list_collection_names()
        if collections:
            print(f"✓ Found {len(collections)} collection(s):")
            for col in collections:
                count = db[col].count_documents({})
                print(f"  - {col}: {count} document(s)")
        else:
            print("  No collections found (this is normal for a new database)")
        print()
        
        # Step 5: Test write operation
        print("Step 5: Testing write operation...")
        test_collection = db.test_connection
        test_doc = {
            "test": True,
            "message": "MongoDB connection test successful",
            "timestamp": "2025-09-29T10:00:00Z"
        }
        result = test_collection.insert_one(test_doc)
        print(f"✓ Test document inserted with ID: {result.inserted_id}")
        print()
        
        # Step 6: Test read operation
        print("Step 6: Testing read operation...")
        retrieved_doc = test_collection.find_one({"_id": result.inserted_id})
        if retrieved_doc:
            print("✓ Test document retrieved successfully:")
            print(f"  Message: {retrieved_doc.get('message')}")
        print()
        
        # Step 7: Clean up test data
        print("Step 7: Cleaning up test data...")
        test_collection.delete_one({"_id": result.inserted_id})
        print("✓ Test document deleted")
        print()
        
        # Step 8: Get server info
        print("Step 8: MongoDB Server Information...")
        server_info = client.server_info()
        print(f"  MongoDB Version: {server_info.get('version')}")
        print(f"  Max BSON Size: {server_info.get('maxBsonObjectSize', 0) / (1024*1024):.1f} MB")
        print()
        
        # Success summary
        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Your MongoDB connection is configured correctly.")
        print("You can now run the application with: python app.py")
        print()
        
        # Close connection
        client.close()
        return True
        
    except ConnectionFailure as e:
        print()
        print("✗ CONNECTION FAILED!")
        print(f"Error: {str(e)}")
        print()
        print("Troubleshooting steps:")
        print("1. Check if MongoDB is running")
        print("2. Verify connection URI in .env file")
        print("3. Check firewall settings")
        print("4. For MongoDB Atlas: Verify IP whitelist")
        print()
        return False
        
    except ServerSelectionTimeoutError as e:
        print()
        print("✗ SERVER TIMEOUT!")
        print(f"Error: Could not connect to MongoDB server")
        print()
        print("Troubleshooting steps:")
        print("1. Check if MongoDB service is running:")
        print("   - Windows: net start MongoDB")
        print("   - macOS: brew services start mongodb-community")
        print("   - Linux: sudo systemctl start mongod")
        print("2. Verify connection string is correct")
        print("3. Check network connectivity")
        print()
        return False
        
    except Exception as e:
        print()
        print("✗ UNEXPECTED ERROR!")
        print(f"Error: {str(e)}")
        print()
        print("Please check your configuration and try again.")
        print()
        return False

def check_environment():
    """Check if environment variables are set"""
    print("Checking environment variables...")
    print()
    
    env_vars = {
        'MONGODB_URI': os.environ.get('MONGODB_URI'),
        'MONGODB_DB_NAME': os.environ.get('MONGODB_DB_NAME'),
        'SESSION_SECRET': os.environ.get('SESSION_SECRET')
    }
    
    all_set = True
    for var, value in env_vars.items():
        if value:
            # Mask sensitive values
            if 'SECRET' in var or 'PASSWORD' in var or 'mongodb+srv' in value:
                display_value = '*' * 8
            else:
                display_value = value
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET (will use default)")
            if var == 'SESSION_SECRET':
                print("  Warning: Using default session secret is not secure for production!")
            all_set = False
    
    print()
    
    if not all_set:
        print("Note: Some environment variables are not set.")
        print("Create a .env file to configure these settings.")
        print("See .env.example for reference.")
        print()

if __name__ == "__main__":
    print()
    check_environment()
    
    # Run connection test
    success = test_mongodb_connection()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
MongoDB Database Initialization Script
Creates database, collections, and indexes for Accufund Formatter
"""

import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime

# Configuration - UPDATED DATABASE NAME
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'new_accufund')

def init_database():
    """Initialize MongoDB database with collections and indexes"""
    
    print("🚀 Initializing MongoDB Database...\n")
    
    try:
        # Connect to MongoDB
        print(f"📡 Connecting to MongoDB at: {MONGO_URI}")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB!\n")
        
        # Get database
        db = client[MONGO_DB_NAME]
        print(f"📊 Using database: {MONGO_DB_NAME}")
        
        # Create collections by inserting a dummy document (MongoDB creates collections lazily)
        print("\n📁 Creating collections...")
        
        # Create 'files' collection
        if 'files' not in db.list_collection_names():
            # Insert and immediately delete a dummy document to create collection
            dummy_file = {
                'original_filename': '_init_',
                'unique_filename': '_init_',
                'file_size': 0,
                'upload_date': datetime.utcnow(),
                'status': 'init',
                'processed_date': None,
                'download_count': 0,
                'error_message': None
            }
            result = db.files.insert_one(dummy_file)
            db.files.delete_one({'_id': result.inserted_id})
            print("  ✅ Created 'files' collection")
        else:
            print("  ℹ️ 'files' collection already exists")
        
        # Create 'processing_logs' collection
        if 'processing_logs' not in db.list_collection_names():
            dummy_log = {
                'file_id': None,
                'original_filename': '_init_',
                'timestamp': datetime.utcnow(),
                'success': True,
                'rows_processed': 0,
                'rows_removed': 0,
                'error_message': None
            }
            result = db.processing_logs.insert_one(dummy_log)
            db.processing_logs.delete_one({'_id': result.inserted_id})
            print("  ✅ Created 'processing_logs' collection")
        else:
            print("  ℹ️ 'processing_logs' collection already exists")
        
        # Create indexes
        print("\n🔑 Creating indexes...")
        
        # Indexes for 'files' collection
        db.files.create_index([('upload_date', DESCENDING)], name='idx_upload_date')
        print("  ✅ Created index on files.upload_date")
        
        db.files.create_index([('status', ASCENDING)], name='idx_status')
        print("  ✅ Created index on files.status")
        
        db.files.create_index([('unique_filename', ASCENDING)], unique=True, name='idx_unique_filename')
        print("  ✅ Created unique index on files.unique_filename")
        
        # Indexes for 'processing_logs' collection
        db.processing_logs.create_index([('file_id', ASCENDING)], name='idx_file_id')
        print("  ✅ Created index on processing_logs.file_id")
        
        db.processing_logs.create_index([('timestamp', DESCENDING)], name='idx_timestamp')
        print("  ✅ Created index on processing_logs.timestamp")
        
        db.processing_logs.create_index([('success', ASCENDING)], name='idx_success')
        print("  ✅ Created index on processing_logs.success")
        
        # Verify database and collections
        print("\n📋 Database Summary:")
        print(f"  Database: {MONGO_DB_NAME}")
        print(f"  Collections: {db.list_collection_names()}")
        
        # Show indexes
        print("\n🔐 Indexes created:")
        print("  files collection:")
        for index in db.files.list_indexes():
            print(f"    - {index['name']}")
        
        print("  processing_logs collection:")
        for index in db.processing_logs.list_indexes():
            print(f"    - {index['name']}")
        
        # Show counts
        print("\n📊 Current counts:")
        print(f"  Files: {db.files.count_documents({})}")
        print(f"  Processing logs: {db.processing_logs.count_documents({})}")
        
        print("\n✅ Database initialization complete!")
        print(f"🎉 Database '{MONGO_DB_NAME}' is ready to use!")
        print("\n💡 You can now run your Flask application: python app.py")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("  1. Check if MongoDB is running: sudo systemctl status mongod")
        print("  2. Start MongoDB: sudo systemctl start mongod")
        print("  3. Check connection string in MONGO_URI")
        print(f"     Current: {MONGO_URI}")
        return False
    
    return True


if __name__ == '__main__':
    init_database()
#!/usr/bin/env python3
"""
MongoDB Database Initialization for GL Comparison
Creates database, collections, and indexes
"""

import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'gl_comparison')

def init_database():
    """Initialize MongoDB database with collections and indexes"""
    
    print("🚀 Initializing GL Comparison MongoDB Database...\n")
    
    try:
        print(f"📡 Connecting to MongoDB at: {MONGO_URI}")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        client.admin.command('ping')
        print("✓ Successfully connected to MongoDB!\n")
        
        db = client[MONGO_DB_NAME]
        print(f"📊 Using database: {MONGO_DB_NAME}")
        
        # Create collections
        print("\n📁 Creating collections...")
        
        collections_to_create = [
            'comparisons',
            'vendors', 
            'ai_analysis',
            'processing_logs'
        ]
        
        for coll_name in collections_to_create:
            if coll_name not in db.list_collection_names():
                dummy_doc = {'_init_': True, 'created_at': datetime.utcnow()}
                result = db[coll_name].insert_one(dummy_doc)
                db[coll_name].delete_one({'_id': result.inserted_id})
                print(f"  ✓ Created '{coll_name}' collection")
            else:
                print(f"  ℹ '{coll_name}' collection already exists")
        
        # Create indexes
        print("\n🔍 Creating indexes...")
        
        # Comparisons collection indexes
        db.comparisons.create_index([('timestamp', DESCENDING)], name='idx_timestamp')
        print("  ✓ Created index on comparisons.timestamp")
        
        db.comparisons.create_index([('ap_filename', ASCENDING)], name='idx_ap_filename')
        print("  ✓ Created index on comparisons.ap_filename")
        
        db.comparisons.create_index([('gl_filename', ASCENDING)], name='idx_gl_filename')
        print("  ✓ Created index on comparisons.gl_filename")
        
        # Vendors collection indexes
        db.vendors.create_index([('vendor_name', ASCENDING)], unique=True, name='idx_vendor_name')
        print("  ✓ Created unique index on vendors.vendor_name")
        
        db.vendors.create_index([('reconciliation_status', ASCENDING)], name='idx_reconciliation_status')
        print("  ✓ Created index on vendors.reconciliation_status")
        
        db.vendors.create_index([('last_comparison_date', DESCENDING)], name='idx_last_comparison_date')
        print("  ✓ Created index on vendors.last_comparison_date")
        
        db.vendors.create_index([('difference', DESCENDING)], name='idx_difference')
        print("  ✓ Created index on vendors.difference")
        
        # AI Analysis collection indexes
        db.ai_analysis.create_index([('comparison_id', ASCENDING)], name='idx_comparison_id')
        print("  ✓ Created index on ai_analysis.comparison_id")
        
        db.ai_analysis.create_index([('timestamp', DESCENDING)], name='idx_ai_timestamp')
        print("  ✓ Created index on ai_analysis.timestamp")
        
        # Processing logs collection indexes
        db.processing_logs.create_index([('timestamp', DESCENDING)], name='idx_log_timestamp')
        print("  ✓ Created index on processing_logs.timestamp")
        
        db.processing_logs.create_index([('success', ASCENDING)], name='idx_success')
        print("  ✓ Created index on processing_logs.success")
        
        # Verify setup
        print("\n📋 Database Summary:")
        print(f"  Database: {MONGO_DB_NAME}")
        print(f"  Collections: {db.list_collection_names()}")
        
        # Show indexes for each collection
        print("\n📑 Indexes created:")
        for coll_name in collections_to_create:
            print(f"  {coll_name} collection:")
            for index in db[coll_name].list_indexes():
                print(f"    - {index['name']}")
        
        # Show counts
        print("\n📊 Current document counts:")
        for coll_name in collections_to_create:
            count = db[coll_name].count_documents({})
            print(f"  {coll_name}: {count}")
        
        print("\n✅ Database initialization complete!")
        print("🎉 You can now run your Flask application: python app.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("  1. Check if MongoDB is running:")
        print("     Windows: net start MongoDB")
        print("     Linux/Mac: sudo systemctl status mongod")
        print("  2. Verify connection string:")
        print(f"     Current: {MONGO_URI}")
        return False

if __name__ == '__main__':
    init_database()
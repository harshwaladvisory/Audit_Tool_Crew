# database.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from datetime import datetime

class MongoDB:
    """Singleton MongoDB connection handler"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
            
        # Get configuration
        from config import Config
        self.mongo_uri = Config.MONGODB_URI
        self.db_name = Config.MONGODB_NAME
         
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            
            # Test connection
            self.client.admin.command('ping')
            print(f"✓ Connected to MongoDB: {self.db_name}")
            
            # Create indexes for better performance
            self._create_indexes()
            
            self.initialized = True
            
        except ConnectionFailure as e:
            print(f"✗ Failed to connect to MongoDB: {e}")
            print(f"✗ Make sure MongoDB is running and accessible at: {self.mongo_uri}")
            raise
    
    def _create_indexes(self):
        """Create indexes for collections"""
        try:
            # Documents collection indexes
            self.db.documents.create_index([("filename", 1)])
            self.db.documents.create_index([("upload_date", -1)])
            self.db.documents.create_index([("file_type", 1)])
            self.db.documents.create_index([("status", 1)])
            
            # Processing sessions indexes
            self.db.processing_sessions.create_index([("session_id", 1)], unique=True)
            self.db.processing_sessions.create_index([("created_at", -1)])
            self.db.processing_sessions.create_index([("status", 1)])
            
            # Processed results indexes
            self.db.processed_results.create_index([("document_id", 1)])
            self.db.processed_results.create_index([("session_id", 1)])
            self.db.processed_results.create_index([("created_at", -1)])
            
            # Audit logs indexes
            self.db.audit_logs.create_index([("timestamp", -1)])
            self.db.audit_logs.create_index([("action_type", 1)])
            
            print("✓ Database indexes created successfully")
        except Exception as e:
            print(f"Warning: Could not create indexes: {e}")
    
    def get_collection(self, collection_name):
        """Get a collection from the database"""
        return self.db[collection_name]
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'client'):
            self.client.close()
            print("MongoDB connection closed")

# Initialize MongoDB connection
try:
    mongo_db = MongoDB()
except Exception as e:
    print(f"Warning: MongoDB initialization failed: {e}")
    print("Application will continue but database features will be unavailable")
    mongo_db = None
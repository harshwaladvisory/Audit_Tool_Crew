import os
from pymongo import MongoClient
import gridfs

# MongoDB connection settings
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.environ.get('MONGODB_DATABASE', 'budget_preparation_db')

# Global MongoDB client
_client = None
_db = None
_fs = None

def get_mongo_client():
    """Get or create MongoDB client"""
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI)
    return _client

def get_database():
    """Get database instance"""
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client[DATABASE_NAME]
    return _db

def get_gridfs():
    """Get GridFS instance for file storage"""
    global _fs
    if _fs is None:
        db = get_database()
        _fs = gridfs.GridFS(db)
    return _fs

def close_connection():
    """Close MongoDB connection"""
    global _client, _db, _fs
    if _client:
        _client.close()
        _client = None
        _db = None
        _fs = None

def init_database():
    """Initialize database with indexes"""
    db = get_database()
    
    # Create indexes for better query performance
    
    # Budgets collection indexes
    db.budgets.create_index([('client_name', 1)])
    db.budgets.create_index([('budget_period', 1)])
    db.budgets.create_index([('status', 1)])
    db.budgets.create_index([('created_at', -1)])
    db.budgets.create_index([('prepared_by', 1)])
    
    # Clients collection indexes
    db.clients.create_index([('name', 1)], unique=True)
    db.clients.create_index([('created_at', -1)])
    
    # Users collection indexes
    db.users.create_index([('email', 1)], unique=True)
    db.users.create_index([('name', 1)])
    
    # Audit log indexes
    db.audit_log.create_index([('budget_id', 1)])
    db.audit_log.create_index([('timestamp', -1)])
    db.audit_log.create_index([('user', 1)])
    db.audit_log.create_index([('action', 1)])
    
    print("Database initialized with indexes")

def test_connection():
    """Test MongoDB connection"""
    try:
        client = get_mongo_client()
        # Ping the database
        client.admin.command('ping')
        print(f"✓ Successfully connected to MongoDB at {MONGODB_URI}")
        print(f"✓ Using database: {DATABASE_NAME}")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {e}")
        return False

if __name__ == '__main__':
    # Test connection when run directly
    if test_connection():
        print("\nInitializing database...")
        init_database()
        print("✓ Database setup complete!")
    else:
        print("\n✗ Database setup failed!")
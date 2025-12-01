from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    """MongoDB database manager"""
    
    def __init__(self, mongo_uri: str, db_name: str):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        
        # Collections
        self.sessions = self.db.sessions
        self.vendors = self.db.vendors
        
        # Create indexes for performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Session indexes
            self.sessions.create_index([("session_id", ASCENDING)], unique=True)
            self.sessions.create_index([("created_at", DESCENDING)])
            self.sessions.create_index([("updated_at", DESCENDING)])
            
            # Vendor indexes
            self.vendors.create_index([("session_id", ASCENDING)])
            self.vendors.create_index([("global_index", ASCENDING)])
            self.vendors.create_index([("classification", ASCENDING)])
            self.vendors.create_index([("total_paid", DESCENDING)])
            self.vendors.create_index([("vendor_name", ASCENDING)])
            
            # Compound index for session + global_index (for fast lookups)
            self.vendors.create_index([("session_id", ASCENDING), ("global_index", ASCENDING)])
            
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.warning(f"Index creation warning (may already exist): {e}")
    
    def close(self):
        """Close database connection"""
        self.client.close()


class VendorSession:
    """Vendor session model for managing user data"""
    
    def __init__(self, db: Database):
        self.db = db
        self.collection = db.sessions
    
    def create_session(self, session_id: str) -> Dict[str, Any]:
        """Create a new vendor session"""
        session_doc = {
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "vendor_count": 0,
            "total_amount": 0.0,
            "file_name": None,
            "file_uploaded_at": None
        }
        
        result = self.collection.insert_one(session_doc)
        session_doc['_id'] = result.inserted_id
        return session_doc
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        return self.collection.find_one({"session_id": session_id})
    
    def update_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        """Update session information"""
        update_data['updated_at'] = datetime.utcnow()
        result = self.collection.update_one(
            {"session_id": session_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its vendors"""
        # Delete all vendors for this session
        vendor_model = Vendor(self.db)
        vendor_model.delete_by_session(session_id)
        
        # Delete the session
        result = self.collection.delete_one({"session_id": session_id})
        return result.deleted_count > 0
    
    def cleanup_old_sessions(self, hours: int = 24) -> int:
        """Clean up sessions older than specified hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Find old sessions
        old_sessions = self.collection.find(
            {"updated_at": {"$lt": cutoff_time}}
        )
        
        deleted_count = 0
        for session in old_sessions:
            if self.delete_session(session['session_id']):
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old sessions")
        return deleted_count


class Vendor:
    """Vendor model for managing vendor data"""
    
    def __init__(self, db: Database):
        self.db = db
        self.collection = db.vendors
    
    def create_vendor(self, session_id: str, vendor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vendor"""
        vendor_doc = {
            "session_id": session_id,
            "vendor_name": vendor_data.get('vendor_name', ''),
            "vendor_id": vendor_data.get('vendor_id', ''),
            "total_paid": vendor_data.get('total_paid', 0.0),
            "transaction_count": vendor_data.get('transaction_count', 1),
            "accounts": vendor_data.get('accounts', ''),
            "memo": vendor_data.get('memo', ''),
            "classification": vendor_data.get('classification', ''),
            "form": vendor_data.get('form', ''),
            "reason": vendor_data.get('reason', ''),
            "notes": vendor_data.get('notes', ''),
            "global_index": vendor_data.get('global_index', 0),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = self.collection.insert_one(vendor_doc)
        vendor_doc['_id'] = result.inserted_id
        return vendor_doc
    
    def bulk_create_vendors(self, session_id: str, vendors_data: List[Dict[str, Any]]) -> bool:
        """Bulk insert vendors for a session"""
        if not vendors_data:
            return True
        
        vendor_docs = []
        for vendor_data in vendors_data:
            vendor_doc = {
                "session_id": session_id,
                "vendor_name": vendor_data.get('vendor_name', ''),
                "vendor_id": vendor_data.get('vendor_id', ''),
                "total_paid": vendor_data.get('total_paid', 0.0),
                "transaction_count": vendor_data.get('transaction_count', 1),
                "accounts": vendor_data.get('accounts', ''),
                "memo": vendor_data.get('memo', ''),
                "classification": vendor_data.get('classification', ''),
                "form": vendor_data.get('form', ''),
                "reason": vendor_data.get('reason', ''),
                "notes": vendor_data.get('notes', ''),
                "global_index": vendor_data.get('global_index', 0),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            vendor_docs.append(vendor_doc)
        
        try:
            self.collection.insert_many(vendor_docs)
            return True
        except Exception as e:
            logger.error(f"Error bulk creating vendors: {e}")
            return False
    
    def get_vendors_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all vendors for a session, sorted by global_index"""
        vendors = list(self.collection.find(
            {"session_id": session_id}
        ).sort("global_index", ASCENDING))
        
        # Convert ObjectId to string for JSON serialization
        for vendor in vendors:
            vendor['_id'] = str(vendor['_id'])
        
        return vendors
    
    def get_vendor_by_index(self, session_id: str, global_index: int) -> Optional[Dict[str, Any]]:
        """Get a specific vendor by session and global index"""
        vendor = self.collection.find_one({
            "session_id": session_id,
            "global_index": global_index
        })
        
        if vendor:
            vendor['_id'] = str(vendor['_id'])
        
        return vendor
    
    def update_vendor(self, session_id: str, global_index: int, update_data: Dict[str, Any]) -> bool:
        """Update vendor information"""
        update_data['updated_at'] = datetime.utcnow()
        
        result = self.collection.update_one(
            {"session_id": session_id, "global_index": global_index},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    
    def delete_by_session(self, session_id: str) -> int:
        """Delete all vendors for a session"""
        result = self.collection.delete_many({"session_id": session_id})
        return result.deleted_count
    
    def get_vendor_count(self, session_id: str) -> int:
        """Get total vendor count for a session"""
        return self.collection.count_documents({"session_id": session_id})
    
    def get_total_amount(self, session_id: str) -> float:
        """Calculate total amount paid for all vendors in a session"""
        pipeline = [
            {"$match": {"session_id": session_id}},
            {"$group": {"_id": None, "total": {"$sum": "$total_paid"}}}
        ]
        
        result = list(self.collection.aggregate(pipeline))
        return result[0]['total'] if result else 0.0
    
    def replace_all_vendors(self, session_id: str, vendors_data: List[Dict[str, Any]]) -> bool:
        """Replace all vendors for a session (used during file upload)"""
        try:
            # Delete existing vendors
            self.delete_by_session(session_id)
            
            # Insert new vendors
            if vendors_data:
                return self.bulk_create_vendors(session_id, vendors_data)
            
            return True
        except Exception as e:
            logger.error(f"Error replacing vendors: {e}")
            return False
        
    def bulk_update_vendors(self, session_id: str, updates: List[Dict[str, Any]]) -> bool:
        """Bulk update multiple vendors efficiently
        
        Args:
            session_id: Session identifier
            updates: List of dicts with 'global_index' and update fields
        """
        if not updates:
            return True
        
        try:
            from pymongo import UpdateOne
            
            bulk_operations = []
            update_time = datetime.utcnow()
            
            for update_item in updates:
                global_index = update_item.pop('global_index')
                update_item['updated_at'] = update_time
                
                operation = UpdateOne(
                    {'session_id': session_id, 'global_index': global_index},
                    {'$set': update_item}
                )
                bulk_operations.append(operation)
            
            if bulk_operations:
                result = self.collection.bulk_write(bulk_operations, ordered=False)
                logger.info(f"Bulk updated {result.modified_count} vendors")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error in bulk update: {e}")
            return False
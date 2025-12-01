# db_operations.py
from database import mongo_db
from models import DocumentModel, ProcessingSessionModel, ProcessedResultModel, AuditLogModel
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Optional

class DocumentOperations:
    """CRUD operations for documents"""
    
    def __init__(self):
        if mongo_db is None:
            self.collection = None
        else:
            self.collection = mongo_db.get_collection('documents')
    
    def create_document(self, filename: str, file_type: str, file_size: int,
                       raw_text: str, extracted_data: List[Dict]) -> Optional[str]:
        """Create a new document record"""
        if self.collection is None:
            return None
            
        try:
            document = DocumentModel.create_document(
                filename, file_type, file_size, raw_text, extracted_data
            )
            result = self.collection.insert_one(document)
            
            # Log the action
            AuditOperations().log_action(
                "document_uploaded",
                details={"document_id": str(result.inserted_id), "filename": filename}
            )
            
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error creating document: {e}")
            return None
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """Get document by ID"""
        if self.collection is None:
            return None
            
        try:
            return self.collection.find_one({"_id": ObjectId(document_id)})
        except Exception as e:
            print(f"Error getting document: {e}")
            return None
    
    def get_all_documents(self, limit: int = 100, skip: int = 0) -> List[Dict]:
        """Get all documents with pagination"""
        if self.collection is None:
            return []
            
        try:
            return list(self.collection.find().sort("upload_date", -1).skip(skip).limit(limit))
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []
    
    def update_document_status(self, document_id: str, status: str) -> bool:
        """Update document status"""
        if self.collection is None:
            return False
            
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating document status: {e}")
            return False
    
    def count_documents(self) -> int:
        """Count total documents"""
        if self.collection is None:
            return 0
        try:
            return self.collection.count_documents({})
        except Exception as e:
            print(f"Error counting documents: {e}")
            return 0

class SessionOperations:
    """CRUD operations for processing sessions"""
    
    def __init__(self):
        if mongo_db is None:
            self.collection = None
        else:
            self.collection = mongo_db.get_collection('processing_sessions')
    
    def create_session(self, session_id: str, document_id: str, 
                      filename: str, file_path: str = None) -> Optional[str]:
        """Create a new processing session"""
        if self.collection is None:
            return None
            
        try:
            session = ProcessingSessionModel.create_session(
                session_id, ObjectId(document_id), filename, file_path
            )
            result = self.collection.insert_one(session)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error creating session: {e}")
            return None
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by session_id"""
        if self.collection is None:
            return None
            
        try:
            return self.collection.find_one({"session_id": session_id})
        except Exception as e:
            print(f"Error getting session: {e}")
            return None
    
    def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status"""
        if self.collection is None:
            return False
            
        try:
            result = self.collection.update_one(
                {"session_id": session_id},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating session status: {e}")
            return False
    
    def add_processing_step(self, session_id: str, step_name: str, 
                           status: str, data: Dict = None) -> bool:
        """Add a processing step to session"""
        if self.collection is None:
            return False
            
        try:
            step = ProcessingSessionModel.add_processing_step(step_name, status, data)
            result = self.collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"processing_steps": step},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error adding processing step: {e}")
            return False
    
    def update_repeat_count(self, session_id: str, count: int) -> bool:
        """Update repeat count"""
        if self.collection is None:
            return False
            
        try:
            result = self.collection.update_one(
                {"session_id": session_id},
                {"$set": {"repeat_count": count, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating repeat count: {e}")
            return False

class ProcessedResultOperations:
    """CRUD operations for processed results"""
    
    def __init__(self):
        if mongo_db is None:
            self.collection = None
        else:
            self.collection = mongo_db.get_collection('processed_results')
    
    def bulk_create_results(self, document_id: str, session_id: str, 
                           results_data: List[Dict]) -> List[str]:
        """Bulk create processed results"""
        if self.collection is None:
            return []
            
        try:
            documents = []
            for item in results_data:
                process_name = item.get("Process", "Unknown Process")
                doc = ProcessedResultModel.create_result(
                    ObjectId(document_id), session_id, process_name, item
                )
                documents.append(doc)
            
            if documents:
                result = self.collection.insert_many(documents)
                return [str(id) for id in result.inserted_ids]
            return []
        except Exception as e:
            print(f"Error bulk creating results: {e}")
            return []
    
    def get_results_by_session(self, session_id: str) -> List[Dict]:
        """Get all results for a session"""
        if self.collection is None:
            return []
            
        try:
            return list(self.collection.find({"session_id": session_id}))
        except Exception as e:
            print(f"Error getting results by session: {e}")
            return []
    
    def mark_as_excel_exported(self, result_ids: List[str]) -> int:
        """Mark multiple results as exported to Excel"""
        if self.collection is None or not result_ids:
            return 0
            
        try:
            object_ids = [ObjectId(id) for id in result_ids]
            result = self.collection.update_many(
                {"_id": {"$in": object_ids}},
                {"$set": {"excel_exported": True, "excel_exported_at": datetime.utcnow()}}
            )
            return result.modified_count
        except Exception as e:
            print(f"Error marking as exported: {e}")
            return 0
    
    def count_results(self) -> int:
        """Count total results"""
        if self.collection is None:
            return 0
        try:
            return self.collection.count_documents({})
        except Exception as e:
            print(f"Error counting results: {e}")
            return 0

class AuditOperations:
    """CRUD operations for audit logs"""
    
    def __init__(self):
        if mongo_db is None:
            self.collection = None
        else:
            self.collection = mongo_db.get_collection('audit_logs')
    
    def log_action(self, action_type: str, user_id: str = "system",
                  details: Dict = None, status: str = "success") -> Optional[str]:
        """Create an audit log entry"""
        if self.collection is None:
            return None
            
        try:
            log = AuditLogModel.create_log(action_type, user_id, details, status)
            result = self.collection.insert_one(log)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error logging action: {e}")
            return None
    
    def get_logs(self, limit: int = 100, skip: int = 0) -> List[Dict]:
        """Get audit logs with pagination"""
        if self.collection is None:
            return []
            
        try:
            return list(self.collection.find().sort("timestamp", -1).skip(skip).limit(limit))
        except Exception as e:
            print(f"Error getting logs: {e}")
            return []

# Initialize operations
doc_ops = DocumentOperations()
session_ops = SessionOperations()
result_ops = ProcessedResultOperations()
audit_ops = AuditOperations()
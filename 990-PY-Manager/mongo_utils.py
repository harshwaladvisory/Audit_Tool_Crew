"""
MongoDB Utility Module for 990 PY Manager
Handles all database operations including connection, CRUD operations, and analytics
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, timedelta
import streamlit as st
from typing import Optional, Dict, List, Any
import os
from bson import ObjectId
import hashlib


class MongoDBManager:
    """Manager class for MongoDB operations"""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB connection string (defaults to env variable)
        """
        self.connection_string = connection_string or os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.client = None
        self.db = None
        self.connected = False
        
        # Collection names
        self.PROCESSING_JOBS = 'processing_jobs'
        self.FILE_METADATA = 'file_metadata'
        self.USER_SESSIONS = 'user_sessions'
        self.ANALYTICS = 'analytics'
        self.AUDIT_LOGS = 'audit_logs'
    
    def connect(self, db_name: str = '990_py_manager_db') -> bool:
        """
        Establish connection to MongoDB
        
        Args:
            db_name: Name of the database to use
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self.connected = True
            self._create_indexes()
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            st.warning(f"Could not connect to MongoDB: {str(e)}")
            self.connected = False
            return False
        except Exception as e:
            st.error(f"Unexpected error connecting to MongoDB: {str(e)}")
            self.connected = False
            return False
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        if not self.connected:
            return
        
        try:
            # Processing jobs indexes
            self.db[self.PROCESSING_JOBS].create_index([('created_at', DESCENDING)])
            self.db[self.PROCESSING_JOBS].create_index([('session_id', ASCENDING)])
            self.db[self.PROCESSING_JOBS].create_index([('status', ASCENDING)])
            
            # File metadata indexes
            self.db[self.FILE_METADATA].create_index([('file_hash', ASCENDING)], unique=True)
            self.db[self.FILE_METADATA].create_index([('upload_date', DESCENDING)])
            
            # User sessions indexes
            self.db[self.USER_SESSIONS].create_index([('session_id', ASCENDING)], unique=True)
            self.db[self.USER_SESSIONS].create_index([('created_at', DESCENDING)])
            
            # Analytics indexes
            self.db[self.ANALYTICS].create_index([('date', DESCENDING)])
            self.db[self.ANALYTICS].create_index([('metric_type', ASCENDING)])
            
            # Audit logs indexes
            self.db[self.AUDIT_LOGS].create_index([('timestamp', DESCENDING)])
            self.db[self.AUDIT_LOGS].create_index([('action', ASCENDING)])
            
        except Exception as e:
            st.warning(f"Could not create indexes: {str(e)}")
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.connected = False
    
    def is_connected(self) -> bool:
        """Check if MongoDB connection is active"""
        return self.connected
    
    # ==================== PROCESSING JOBS ====================
    
    def create_processing_job(self, session_id: str, input_files: List[str], 
                            template_file: str, metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Create a new processing job record
        
        Args:
            session_id: Streamlit session ID
            input_files: List of input filenames
            template_file: Template filename
            metadata: Additional metadata
            
        Returns:
            str: Job ID if successful, None otherwise
        """
        if not self.connected:
            return None
        
        try:
            job_doc = {
                'session_id': session_id,
                'input_files': input_files,
                'template_file': template_file,
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'total_files': len(input_files),
                'processed_files': 0,
                'failed_files': 0,
                'success_rate': 0.0,
                'metadata': metadata or {}
            }
            
            result = self.db[self.PROCESSING_JOBS].insert_one(job_doc)
            return str(result.inserted_id)
        except Exception as e:
            st.warning(f"Could not create processing job: {str(e)}")
            return None
    
    def update_processing_job(self, job_id: str, updates: Dict) -> bool:
        """
        Update a processing job
        
        Args:
            job_id: Job ID to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if successful
        """
        if not self.connected:
            return False
        
        try:
            updates['updated_at'] = datetime.utcnow()
            result = self.db[self.PROCESSING_JOBS].update_one(
                {'_id': ObjectId(job_id)},
                {'$set': updates}
            )
            return result.modified_count > 0
        except Exception as e:
            st.warning(f"Could not update processing job: {str(e)}")
            return False
    
    def complete_processing_job(self, job_id: str, processed_count: int, 
                              failed_count: int, output_files: List[str]) -> bool:
        """
        Mark a processing job as complete
        
        Args:
            job_id: Job ID to complete
            processed_count: Number of successfully processed files
            failed_count: Number of failed files
            output_files: List of output filenames
            
        Returns:
            bool: True if successful
        """
        if not self.connected:
            return False
        
        total = processed_count + failed_count
        success_rate = (processed_count / total * 100) if total > 0 else 0
        
        updates = {
            'status': 'completed',
            'processed_files': processed_count,
            'failed_files': failed_count,
            'success_rate': round(success_rate, 2),
            'output_files': output_files,
            'completed_at': datetime.utcnow()
        }
        
        return self.update_processing_job(job_id, updates)
    
    def get_processing_job(self, job_id: str) -> Optional[Dict]:
        """Get a processing job by ID"""
        if not self.connected:
            return None
        
        try:
            return self.db[self.PROCESSING_JOBS].find_one({'_id': ObjectId(job_id)})
        except Exception as e:
            st.warning(f"Could not get processing job: {str(e)}")
            return None
    
    def get_recent_jobs(self, limit: int = 10, session_id: Optional[str] = None) -> List[Dict]:
        """
        Get recent processing jobs
        
        Args:
            limit: Maximum number of jobs to return
            session_id: Filter by session ID (optional)
            
        Returns:
            List of job documents
        """
        if not self.connected:
            return []
        
        try:
            query = {'session_id': session_id} if session_id else {}
            jobs = self.db[self.PROCESSING_JOBS].find(query).sort('created_at', DESCENDING).limit(limit)
            return list(jobs)
        except Exception as e:
            st.warning(f"Could not get recent jobs: {str(e)}")
            return []
    
    # ==================== FILE METADATA ====================
    
    def _calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    def store_file_metadata(self, filename: str, file_content: bytes, 
                          file_type: str, metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Store file metadata (not the actual file, just metadata)
        
        Args:
            filename: Name of the file
            file_content: File content (for hash calculation)
            file_type: Type of file (input/template/output)
            metadata: Additional metadata
            
        Returns:
            str: File metadata ID if successful
        """
        if not self.connected:
            return None
        
        try:
            file_hash = self._calculate_file_hash(file_content)
            file_size = len(file_content)
            
            # Check if file already exists
            existing = self.db[self.FILE_METADATA].find_one({'file_hash': file_hash})
            if existing:
                return str(existing['_id'])
            
            file_doc = {
                'filename': filename,
                'file_hash': file_hash,
                'file_size': file_size,
                'file_type': file_type,
                'upload_date': datetime.utcnow(),
                'metadata': metadata or {}
            }
            
            result = self.db[self.FILE_METADATA].insert_one(file_doc)
            return str(result.inserted_id)
        except Exception as e:
            st.warning(f"Could not store file metadata: {str(e)}")
            return None
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict]:
        """Get file metadata by ID"""
        if not self.connected:
            return None
        
        try:
            return self.db[self.FILE_METADATA].find_one({'_id': ObjectId(file_id)})
        except Exception as e:
            st.warning(f"Could not get file metadata: {str(e)}")
            return None
    
    # ==================== USER SESSIONS ====================
    
    def create_or_update_session(self, session_id: str, metadata: Optional[Dict] = None) -> bool:
        """
        Create or update a user session
        
        Args:
            session_id: Streamlit session ID
            metadata: Session metadata
            
        Returns:
            bool: True if successful
        """
        if not self.connected:
            return False
        
        try:
            now = datetime.utcnow()
            session_doc = {
                'session_id': session_id,
                'last_activity': now,
                'metadata': metadata or {}
            }
            
            self.db[self.USER_SESSIONS].update_one(
                {'session_id': session_id},
                {
                    '$set': session_doc,
                    '$setOnInsert': {'created_at': now}
                },
                upsert=True
            )
            return True
        except Exception as e:
            st.warning(f"Could not create/update session: {str(e)}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        if not self.connected:
            return None
        
        try:
            return self.db[self.USER_SESSIONS].find_one({'session_id': session_id})
        except Exception as e:
            st.warning(f"Could not get session: {str(e)}")
            return None
    
    # ==================== ANALYTICS ====================
    
    def update_daily_analytics(self, metric_type: str, value: Any, date: Optional[datetime] = None):
        """
        Update daily analytics metrics
        
        Args:
            metric_type: Type of metric (e.g., 'files_processed', 'jobs_completed')
            value: Metric value
            date: Date for the metric (defaults to today)
        """
        if not self.connected:
            return
        
        try:
            target_date = date or datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            self.db[self.ANALYTICS].update_one(
                {
                    'date': target_date,
                    'metric_type': metric_type
                },
                {
                    '$inc': {'value': value},
                    '$set': {'updated_at': datetime.utcnow()}
                },
                upsert=True
            )
        except Exception as e:
            st.warning(f"Could not update analytics: {str(e)}")
    
    def get_analytics_summary(self, days: int = 30) -> Dict:
        """
        Get analytics summary for the last N days
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with analytics summary
        """
        if not self.connected:
            return {}
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get total jobs
            total_jobs = self.db[self.PROCESSING_JOBS].count_documents({
                'created_at': {'$gte': start_date}
            })
            
            # Get completed jobs
            completed_jobs = self.db[self.PROCESSING_JOBS].count_documents({
                'created_at': {'$gte': start_date},
                'status': 'completed'
            })
            
            # Get total files processed
            pipeline = [
                {'$match': {'created_at': {'$gte': start_date}, 'status': 'completed'}},
                {'$group': {'_id': None, 'total': {'$sum': '$processed_files'}}}
            ]
            files_result = list(self.db[self.PROCESSING_JOBS].aggregate(pipeline))
            total_files = files_result[0]['total'] if files_result else 0
            
            # Get average success rate
            avg_pipeline = [
                {'$match': {'created_at': {'$gte': start_date}, 'status': 'completed'}},
                {'$group': {'_id': None, 'avg_success_rate': {'$avg': '$success_rate'}}}
            ]
            avg_result = list(self.db[self.PROCESSING_JOBS].aggregate(avg_pipeline))
            avg_success_rate = round(avg_result[0]['avg_success_rate'], 2) if avg_result else 0
            
            return {
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'total_files_processed': total_files,
                'average_success_rate': avg_success_rate,
                'period_days': days
            }
        except Exception as e:
            st.warning(f"Could not get analytics summary: {str(e)}")
            return {}
    
    # ==================== AUDIT LOGS ====================
    
    def log_action(self, action: str, details: Optional[Dict] = None, 
                   session_id: Optional[str] = None):
        """
        Log an action to audit logs
        
        Args:
            action: Action description
            details: Additional details
            session_id: Session ID (optional)
        """
        if not self.connected:
            return
        
        try:
            log_doc = {
                'action': action,
                'timestamp': datetime.utcnow(),
                'session_id': session_id,
                'details': details or {}
            }
            
            self.db[self.AUDIT_LOGS].insert_one(log_doc)
        except Exception as e:
            st.warning(f"Could not log action: {str(e)}")
    
    def get_recent_logs(self, limit: int = 50, action_filter: Optional[str] = None) -> List[Dict]:
        """
        Get recent audit logs
        
        Args:
            limit: Maximum number of logs to return
            action_filter: Filter by action type (optional)
            
        Returns:
            List of log documents
        """
        if not self.connected:
            return []
        
        try:
            query = {'action': action_filter} if action_filter else {}
            logs = self.db[self.AUDIT_LOGS].find(query).sort('timestamp', DESCENDING).limit(limit)
            return list(logs)
        except Exception as e:
            st.warning(f"Could not get recent logs: {str(e)}")
            return []


# Singleton instance
_db_manager = None


def get_db_manager() -> MongoDBManager:
    """Get or create MongoDB manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = MongoDBManager()
    return _db_manager
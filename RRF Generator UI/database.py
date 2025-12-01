from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging
from datetime import datetime
import base64

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all MongoDB operations"""
    
    def __init__(self, mongo_uri, db_name):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        
    def connect(self):
        """Establish MongoDB connection with error handling"""
        try:
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self._create_indexes()
            logger.info(f"Successfully connected to MongoDB: {self.db_name}")
            return self.db
        except (ConnectionFailure, ServerSelectionTimeoutError) as err:
            logger.error(f"MongoDB connection failed: {err}")
            raise
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        collection = self.db.processing_records
        
        # Create indexes
        collection.create_index([("job_id", ASCENDING)], unique=True)
        collection.create_index([("run_timestamp", DESCENDING)])
        collection.create_index([("status", ASCENDING)])
        collection.create_index([("input_pdf_name", ASCENDING)])
        
        logger.info("Database indexes created successfully")
    
    def save_processing_record(self, record_data):
        """
        Save a processing record to MongoDB
        
        Args:
            record_data (dict): Dictionary containing all record fields
        
        Returns:
            str: Inserted document ID
        """
        collection = self.db.processing_records
        
        try:
            # Add timestamp if not present
            if 'run_timestamp' not in record_data:
                record_data['run_timestamp'] = datetime.now()
            
            result = collection.insert_one(record_data)
            logger.info(f"Record saved with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as err:
            logger.error(f"Failed to save record: {err}")
            raise
    
    def get_record_by_job_id(self, job_id):
        """
        Retrieve a record by job_id
        
        Args:
            job_id (str): Unique job identifier
        
        Returns:
            dict: Record data or None
        """
        collection = self.db.processing_records
        return collection.find_one({'job_id': job_id})
    
    def get_dashboard_statistics(self):
        """
        Calculate dashboard statistics
        
        Returns:
            dict: Statistics including total documents, success rate, etc.
        """
        collection = self.db.processing_records
        
        # Total successful documents
        total_success = collection.count_documents({'status': 'SUCCESS'})
        
        # Total documents
        total_documents = collection.count_documents({})
        
        # Success rate
        success_rate = round((total_success / total_documents * 100) if total_documents > 0 else 0, 1)
        
        # Count unique templates
        pipeline = [
            {'$match': {'status': 'SUCCESS'}},
            {'$group': {'_id': '$input_word_name'}}
        ]
        active_templates = len(list(collection.aggregate(pipeline)))
        if active_templates == 0:
            active_templates = 1
        
        # Average processing time (placeholder - can be enhanced)
        avg_processing_time = 2.3
        
        return {
            'total_documents': total_success,
            'active_templates': active_templates,
            'avg_processing_time': avg_processing_time,
            'success_rate': success_rate,
            'total_jobs': total_documents
        }
    
    def get_recent_records(self, limit=10, status=None):
        """
        Get recent processing records
        
        Args:
            limit (int): Number of records to return
            status (str): Filter by status (optional)
        
        Returns:
            list: List of records
        """
        collection = self.db.processing_records
        
        query = {}
        if status:
            query['status'] = status
        
        return list(collection.find(query).sort('run_timestamp', DESCENDING).limit(limit))
    
    def update_record_status(self, job_id, status, log_message=None):
        """
        Update the status of a record
        
        Args:
            job_id (str): Job identifier
            status (str): New status
            log_message (str): Optional log message
        """
        collection = self.db.processing_records
        
        update_data = {
            'status': status,
            'updated_at': datetime.now()
        }
        
        if log_message:
            update_data['log_message'] = log_message
        
        collection.update_one(
            {'job_id': job_id},
            {'$set': update_data}
        )
        logger.info(f"Updated status for job_id {job_id} to {status}")
    
    def delete_old_records(self, days=30):
        """
        Delete records older than specified days
        
        Args:
            days (int): Number of days to keep records
        
        Returns:
            int: Number of deleted records
        """
        from datetime import timedelta
        
        collection = self.db.processing_records
        cutoff_date = datetime.now() - timedelta(days=days)
        
        result = collection.delete_many({'run_timestamp': {'$lt': cutoff_date}})
        logger.info(f"Deleted {result.deleted_count} old records")
        return result.deleted_count
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
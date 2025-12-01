from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
import logging
import pandas as pd
from bson import ObjectId

logger = logging.getLogger(__name__)

class Database:
    """MongoDB database connection and operations"""
    
    def __init__(self, uri, db_name):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(
                uri, 
                serverSelectionTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=45000,
                connectTimeoutMS=10000,
                socketTimeoutMS=45000
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self._create_indexes()
            logger.info(f"Connected to MongoDB database: {db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    def is_connected(self):
        """Check if MongoDB connection is alive"""
        try:
            self.client.admin.command('ping', maxTimeMS=1000)
            return True
        except:
            return False
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        try:
            # GL Entries indexes
            self.db.gl_entries.create_index([("analysis_id", ASCENDING)])
            self.db.gl_entries.create_index([("date", ASCENDING)])
            self.db.gl_entries.create_index([("je_id", ASCENDING)])
            
            # Populations indexes
            self.db.populations.create_index([("analysis_id", ASCENDING)])
            self.db.populations.create_index([("risk_category", ASCENDING)])
            
            # Samples indexes
            self.db.samples.create_index([("analysis_id", ASCENDING)])
            self.db.samples.create_index([("sample_id", ASCENDING)])
            
            # Analyses indexes
            self.db.analyses.create_index([("created_at", DESCENDING)])
            self.db.analyses.create_index([("status", ASCENDING)])
            
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.warning(f"Error creating indexes: {str(e)}")
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


class GLEntryModel:
    """Model for General Ledger entries"""
    
    def __init__(self, db):
        self.collection = db.gl_entries
    
    def insert_entries(self, df, analysis_id):
        """Insert GL entries from DataFrame"""
        try:
            records = df.to_dict('records')
            # Add metadata
            for record in records:
                record['analysis_id'] = analysis_id
                record['created_at'] = datetime.utcnow()
                # Convert pandas/numpy types to native Python types
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
                        record[key] = value.to_pydatetime() if hasattr(value, 'to_pydatetime') else value
                    elif hasattr(value, 'item'):  # numpy types
                        record[key] = value.item()
            
            result = self.collection.insert_many(records)
            logger.info(f"Inserted {len(result.inserted_ids)} GL entries")
            return result.inserted_ids
        except Exception as e:
            logger.error(f"Error inserting GL entries: {str(e)}")
            raise
    
    def get_entries_by_analysis(self, analysis_id):
        """Get all GL entries for an analysis"""
        try:
            cursor = self.collection.find({"analysis_id": analysis_id})
            df = pd.DataFrame(list(cursor))
            if not df.empty and '_id' in df.columns:
                df['_id'] = df['_id'].astype(str)
            return df
        except Exception as e:
            logger.error(f"Error retrieving GL entries: {str(e)}")
            return pd.DataFrame()
    
    def get_entry_by_je_id(self, je_id, analysis_id):
        """Get specific entry by JE ID"""
        return self.collection.find_one({"je_id": je_id, "analysis_id": analysis_id})


class PopulationModel:
    """Model for risk-analyzed populations"""
    
    def __init__(self, db):
        self.collection = db.populations
    
    def insert_population(self, df, analysis_id):
        """Insert population data from DataFrame"""
        try:
            records = df.to_dict('records')
            for record in records:
                record['analysis_id'] = analysis_id
                record['created_at'] = datetime.utcnow()
                # Convert pandas/numpy types
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
                        record[key] = value.to_pydatetime() if hasattr(value, 'to_pydatetime') else value
                    elif hasattr(value, 'item'):
                        record[key] = value.item()
            
            result = self.collection.insert_many(records)
            logger.info(f"Inserted {len(result.inserted_ids)} population records")
            return result.inserted_ids
        except Exception as e:
            logger.error(f"Error inserting population: {str(e)}")
            raise
    
    def get_population_by_analysis(self, analysis_id):
        """Get population for an analysis"""
        try:
            cursor = self.collection.find({"analysis_id": analysis_id})
            df = pd.DataFrame(list(cursor))
            if not df.empty and '_id' in df.columns:
                df['_id'] = df['_id'].astype(str)
            return df
        except Exception as e:
            logger.error(f"Error retrieving population: {str(e)}")
            return pd.DataFrame()
    
    def get_risk_summary(self, analysis_id):
        """Get risk category summary"""
        pipeline = [
            {"$match": {"analysis_id": analysis_id}},
            {"$group": {
                "_id": "$risk_category",
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$net"}
            }}
        ]
        return list(self.collection.aggregate(pipeline))


class SampleModel:
    """Model for selected samples"""
    
    def __init__(self, db):
        self.collection = db.samples
    
    def insert_samples(self, df, analysis_id):
        """Insert selected samples from DataFrame"""
        try:
            records = df.to_dict('records')
            for record in records:
                record['analysis_id'] = analysis_id
                record['created_at'] = datetime.utcnow()
                record['test_status'] = 'Pending'
                # Convert pandas/numpy types
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
                        record[key] = value.to_pydatetime() if hasattr(value, 'to_pydatetime') else value
                    elif hasattr(value, 'item'):
                        record[key] = value.item()
            
            result = self.collection.insert_many(records)
            logger.info(f"Inserted {len(result.inserted_ids)} samples")
            return result.inserted_ids
        except Exception as e:
            logger.error(f"Error inserting samples: {str(e)}")
            raise
    
    def get_samples_by_analysis(self, analysis_id):
        """Get all samples for an analysis"""
        try:
            cursor = self.collection.find({"analysis_id": analysis_id})
            df = pd.DataFrame(list(cursor))
            if not df.empty and '_id' in df.columns:
                df['_id'] = df['_id'].astype(str)
            return df
        except Exception as e:
            logger.error(f"Error retrieving samples: {str(e)}")
            return pd.DataFrame()
    
    def update_test_result(self, sample_id, test_results):
        """Update test results for a sample"""
        try:
            self.collection.update_one(
                {"sample_id": sample_id},
                {"$set": {
                    "test_results": test_results,
                    "test_status": test_results.get('overall_result', 'Completed'),
                    "tested_at": datetime.utcnow()
                }}
            )
            logger.info(f"Updated test results for sample {sample_id}")
        except Exception as e:
            logger.error(f"Error updating test results: {str(e)}")
            raise


class AnalysisModel:
    """Model for analysis metadata"""
    
    def __init__(self, db):
        self.collection = db.analyses
    
    def create_analysis(self, parameters):
        """Create new analysis record"""
        try:
            analysis = {
                "created_at": datetime.utcnow(),
                "status": "In Progress",
                "parameters": parameters,
                "metrics": {},
                "output_files": []
            }
            result = self.collection.insert_one(analysis)
            logger.info(f"Created analysis: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating analysis: {str(e)}")
            raise
    
    def update_analysis(self, analysis_id, updates):
        """Update analysis record"""
        try:
            self.collection.update_one(
                {"_id": ObjectId(analysis_id)},
                {"$set": updates}
            )
            logger.info(f"Updated analysis: {analysis_id}")
        except Exception as e:
            logger.error(f"Error updating analysis: {str(e)}")
            raise
    
    def complete_analysis(self, analysis_id, metrics, output_files):
        """Mark analysis as complete"""
        try:
            self.collection.update_one(
                {"_id": ObjectId(analysis_id)},
                {"$set": {
                    "status": "Completed",
                    "completed_at": datetime.utcnow(),
                    "metrics": metrics,
                    "output_files": output_files
                }}
            )
            logger.info(f"Completed analysis: {analysis_id}")
        except Exception as e:
            logger.error(f"Error completing analysis: {str(e)}")
            raise
    
    def get_analysis(self, analysis_id):
        """Get analysis by ID"""
        try:
            return self.collection.find_one({"_id": ObjectId(analysis_id)})
        except Exception as e:
            logger.error(f"Error retrieving analysis: {str(e)}")
            return None
    
    def get_recent_analyses(self, limit=10):
        """Get recent analyses"""
        try:
            cursor = self.collection.find().sort("created_at", DESCENDING).limit(limit)
            analyses = list(cursor)
            for analysis in analyses:
                analysis['_id'] = str(analysis['_id'])
            return analyses
        except Exception as e:
            logger.error(f"Error retrieving recent analyses: {str(e)}")
            return []
    
    def delete_analysis(self, analysis_id):
        """Delete analysis and all related data"""
        try:
            # Delete from all collections
            self.collection.delete_one({"_id": ObjectId(analysis_id)})
            logger.info(f"Deleted analysis: {analysis_id}")
        except Exception as e:
            logger.error(f"Error deleting analysis: {str(e)}")
            raise


class TestResultModel:
    """Model for test results"""
    
    def __init__(self, db):
        self.collection = db.test_results
    
    def insert_test_result(self, sample_id, analysis_id, test_data):
        """Insert test result"""
        try:
            test_result = {
                "sample_id": sample_id,
                "analysis_id": analysis_id,
                "test_data": test_data,
                "created_at": datetime.utcnow(),
                "status": test_data.get('overall_result', 'Pending')
            }
            result = self.collection.insert_one(test_result)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error inserting test result: {str(e)}")
            raise
    
    def get_test_results_by_analysis(self, analysis_id):
        """Get all test results for an analysis"""
        cursor = self.collection.find({"analysis_id": analysis_id})
        return list(cursor)


class ExceptionModel:
    """Model for exceptions tracking"""
    
    def __init__(self, db):
        self.collection = db.exceptions
    
    def insert_exception(self, exception_data):
        """Insert exception"""
        try:
            exception_data['created_at'] = datetime.utcnow()
            exception_data['status'] = exception_data.get('status', 'Open')
            result = self.collection.insert_one(exception_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error inserting exception: {str(e)}")
            raise
    
    def update_exception(self, exception_id, updates):
        """Update exception"""
        try:
            self.collection.update_one(
                {"_id": ObjectId(exception_id)},
                {"$set": updates}
            )
        except Exception as e:
            logger.error(f"Error updating exception: {str(e)}")
            raise
    
    def get_exceptions_by_analysis(self, analysis_id):
        """Get all exceptions for an analysis"""
        cursor = self.collection.find({"analysis_id": analysis_id})
        return list(cursor)
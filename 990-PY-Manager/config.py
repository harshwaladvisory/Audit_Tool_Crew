"""
Configuration Module for 990 PY Manager
Handles all configuration settings including MongoDB connection
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', '990_py_manager_db')
    MONGODB_ENABLED = os.getenv('MONGODB_ENABLED', 'true').lower() == 'true'
    
    # Application Settings
    APP_NAME = "990 PY Mapper"
    APP_VERSION = "2.0.0"
    
    # File Upload Settings
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '50'))
    ALLOWED_EXTENSIONS = ['.xlsx', '.xls']
    
    # Session Settings
    SESSION_TIMEOUT_MINUTES = int(os.getenv('SESSION_TIMEOUT_MINUTES', '60'))
    
    # Analytics Settings
    ANALYTICS_RETENTION_DAYS = int(os.getenv('ANALYTICS_RETENTION_DAYS', '90'))
    
    # Debug Mode
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    @classmethod
    def get_config_dict(cls) -> dict:
        """Get all configuration as dictionary"""
        return {
            'mongodb_uri': cls.MONGODB_URI,
            'mongodb_db_name': cls.MONGODB_DB_NAME,
            'mongodb_enabled': cls.MONGODB_ENABLED,
            'app_name': cls.APP_NAME,
            'app_version': cls.APP_VERSION,
            'max_file_size_mb': cls.MAX_FILE_SIZE_MB,
            'session_timeout_minutes': cls.SESSION_TIMEOUT_MINUTES,
            'analytics_retention_days': cls.ANALYTICS_RETENTION_DAYS,
            'debug': cls.DEBUG
        }
    
    @classmethod
    def validate_config(cls) -> tuple[bool, list]:
        """
        Validate configuration settings
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check MongoDB URI format
        if cls.MONGODB_ENABLED:
            if not cls.MONGODB_URI:
                errors.append("MONGODB_URI is required when MongoDB is enabled")
            elif not cls.MONGODB_URI.startswith(('mongodb://', 'mongodb+srv://')):
                errors.append("MONGODB_URI must start with 'mongodb://' or 'mongodb+srv://'")
        
        # Check file size limit
        if cls.MAX_FILE_SIZE_MB <= 0:
            errors.append("MAX_FILE_SIZE_MB must be greater than 0")
        
        # Check session timeout
        if cls.SESSION_TIMEOUT_MINUTES <= 0:
            errors.append("SESSION_TIMEOUT_MINUTES must be greater than 0")
        
        return (len(errors) == 0, errors)


# Create a global config instance
config = Config()
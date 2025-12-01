import mongoengine
from flask import current_app


class MongoDB:
    """MongoDB connection manager for Flask"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize MongoDB connection"""
        mongodb_settings = app.config.get('MONGODB_SETTINGS', {})
        
        # Extract connection parameters
        host = mongodb_settings.get('host', 'mongodb://localhost:27017/prepaid_expense_db')
        
        # Connect to MongoDB
        try:
            mongoengine.connect(host=host, connect=False)
            app.logger.info(f"MongoDB connected successfully to: {host}")
        except Exception as e:
            app.logger.error(f"MongoDB connection error: {e}")
            raise

# Create database instance
db = MongoDB()
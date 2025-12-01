import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    if not SECRET_KEY:
        raise ValueError("SESSION_SECRET environment variable is required")
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # MongoDB configuration
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'vendor_tracker')
    
    # Optional: MongoDB Atlas connection
    # MONGO_URI = 'mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority'
    
    # File upload configuration
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # Session configuration
    SESSION_TIMEOUT_HOURS = 24  # Auto-cleanup old sessions after 24 hours
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
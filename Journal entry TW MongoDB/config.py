import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get("SESSION_SECRET", "audit-je-secret-key")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    
    # MongoDB Configuration
    MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "journal_entry_audit")
    
    # File Upload Configuration
    UPLOAD_FOLDER = './uploads'
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'pdf', 'txt'}
    
    # Analysis Parameters Defaults
    DEFAULT_INVESTIGATE_THRESHOLD = 1000
    DEFAULT_COVERAGE_TARGET = 0.8
    DEFAULT_MATERIALITY = 10000
    DEFAULT_PERIOD_END_WINDOW = 7
    
    # Gemini API
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        pass
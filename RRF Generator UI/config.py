import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('FLASK_SECRET', 'supersecret-change-in-production')
    UPLOAD_FOLDER = 'Uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # MongoDB Configuration
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'rrf_processing_db')
    
    # N8N Webhook Configuration
    N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL', 
                                      'http://sara-tech.info/webhook/acb4a2e4-3043-47c8-86d9-2d30d9a06382')
    N8N_TIMEOUT = int(os.environ.get('N8N_TIMEOUT', 2000))
    
    # File Upload Configuration
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
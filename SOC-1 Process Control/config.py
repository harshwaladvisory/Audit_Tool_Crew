# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask Config
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # MongoDB Config
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_NAME = os.getenv('MONGODB_NAME', 'soc1_process_control')
    
    # N8N Webhook URLs
    WEBHOOK_URLS = {
        '.pdf': os.getenv('WEBHOOK_PDF', "http://sara-tech.info/webhook/83b73abd-95ae-468d-a930-883181f46b78"),
        '.docx': os.getenv('WEBHOOK_DOCX', "http://sara-tech.info/webhook/a5350f42-6e00-4773-ba83-6c8f00ce31c0"),
        '.xlsx': os.getenv('WEBHOOK_EXCEL', "http://sara-tech.info/webhook/f36079f0-2b20-45e3-97a6-925f3b92e29e"),
        '.xls': os.getenv('WEBHOOK_EXCEL', "http://sara-tech.info/webhook/f36079f0-2b20-45e3-97a6-925f3b92e29e")
    }
    
    CONTROL_WEBHOOK_URL = os.getenv('WEBHOOK_CONTROL', 
                                     "http://sara-tech.info/webhook/79f09e53-b0cd-4d13-a69f-77bbb99ee89c")
    
    # Excel Output
    EXCEL_FILE_PATH = os.getenv('EXCEL_FILE_PATH', "output.xlsx")
    
    # File Processing
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.xls', '.png', '.jpg', '.jpeg'}
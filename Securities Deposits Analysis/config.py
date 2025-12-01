import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    
    # MongoDB Configuration
    MONGODB_DB = os.getenv('MONGO_DB', 'depositsense')
    MONGODB_HOST = os.getenv('MONGO_HOST', 'localhost')
    MONGODB_PORT = int(os.getenv('MONGO_PORT', 27017))
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    
    # Aging Analysis Configuration
    AGING_BUCKETS = [
        ('0-30', 0, 30),
        ('31-60', 31, 60),
        ('61-90', 61, 90),
        ('91-180', 91, 180),
        ('181-365', 181, 365),
        ('365+', 365, float('inf'))
    ]
    
    # Dormancy threshold in days
    DORMANCY_THRESHOLD_DAYS = 1095  # 3 years
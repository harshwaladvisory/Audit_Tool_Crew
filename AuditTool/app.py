import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta
import mongoengine
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# MongoDB Configuration
# Load from environment variable (from .env file)
MONGODB_URI = os.environ.get("MONGODB_URI")
# MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/audit_tool")
# MONGODB_URI="mongodb://Administrator:Hcsllp%21%402010@192.168.100.84:27017/audit_tool?authSource=admin&directConnection=true"

# Connect to MongoDB using mongoengine
mongoengine.connect(
    host=MONGODB_URI,
    alias='default'
)
app.logger.info(f"Successfully connected to MongoDB at {MONGODB_URI.split('@')[1] if '@' in MONGODB_URI else MONGODB_URI}")
print(f"Successfully connected to MongoDB at {MONGODB_URI.split('@')[1] if '@' in MONGODB_URI else MONGODB_URI}")

# try:
#     mongoengine.connect(
#         host=MONGODB_URI,
#         alias='default'
#     )
#     app.logger.info(f"Successfully connected to MongoDB at {MONGODB_URI.split('@')[1] if '@' in MONGODB_URI else MONGODB_URI}")
# except Exception as e:
#     app.logger.error(f"Failed to connect to MongoDB: {str(e)}")
#     raise


# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Custom Jinja2 filter for adding days to a date and formatting it
def add_days(date, days):
    if date is None:
        return None
    return (date + timedelta(days=days)).strftime('%Y-%m-%d')

# Register the custom filter with Jinja2
app.jinja_env.filters['add_days'] = add_days

# Import models to ensure they are registered
import models

# Import routes
import routes
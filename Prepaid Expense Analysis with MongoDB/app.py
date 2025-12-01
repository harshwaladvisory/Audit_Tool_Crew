import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from database import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # MongoDB Configuration
    mongodb_uri = os.environ.get(
        "MONGODB_URI", 
        "mongodb://localhost:27017/prepaid_expense_db"
    )
    
    app.config["MONGODB_SETTINGS"] = {
        'host': mongodb_uri,
    }
    
    # Configure upload settings
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = 'uploads'
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize MongoDB
    db.init_app(app)
    
    # Import models to register them with mongoengine
    with app.app_context():
        import models
        app.logger.info("MongoDB models registered successfully")
        app.logger.info(f"Connected to MongoDB at: {mongodb_uri}")
    
    # Register routes
    from routes import register_routes
    register_routes(app)
    
    return app

# Create the app
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8565, debug=True)
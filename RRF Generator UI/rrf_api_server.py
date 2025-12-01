"""
RRF Generator API Server - Standalone Launcher
Port: 5009
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'supersecret')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Create folders
Path('uploads').mkdir(exist_ok=True)
Path('outputs').mkdir(exist_ok=True)

# Global database manager reference
db_manager = None

# ============================================
# IMPORT AND REGISTER AGENT API BLUEPRINT
# ============================================

try:
    from agent_api import rrf_agent_api, init_agent_api
    
    # Initialize agent API (MongoDB optional)
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager(
            mongo_uri='mongodb://localhost:27017/',
            db_name='rrf_processing_db'
        )
        db_manager.connect()
        init_agent_api(db_manager)
        logger.info("✅ MongoDB connected")
    except Exception as e:
        logger.warning(f"⚠️ MongoDB unavailable (optional): {e}")
        init_agent_api(None)  # Initialize without MongoDB
    
    # Register blueprint (single registration at root level)
    # This makes endpoints available at both / and /api/v1/ paths
    app.register_blueprint(rrf_agent_api, url_prefix='')
    
    logger.info("✅ RRF Agent API Blueprint registered successfully!")
    
except ImportError as e:
    logger.error(f"❌ Failed to import agent_api.py: {e}")
    logger.error("Make sure agent_api.py, pdf_extractor.py, and template_filler.py are in the same directory")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ Failed to register agent API: {e}")
    sys.exit(1)


# ============================================
# ROOT ENDPOINT (INFO)
# ============================================

@app.route('/', methods=['GET'])
def root():
    """Root endpoint - API information"""
    mongodb_status = 'connected' if db_manager is not None else 'disabled'
    
    return {
        'service': 'RRF Generator API',
        'version': '2.1.0',
        'port': 5009,
        'status': 'running',
        'endpoints': {
            'health': '/health or /api/v1/health',
            'info': '/info or /api/v1/info',
            'execute': '/execute or /api/v1/execute (POST - multipart/form-data)',
            'download': '/download/<session_id>/<filename> or /api/v1/download/<session_id>/<filename>'
        },
        'required_files': ['pdf_file', 'word_file'],
        'optional_params': ['approval_date'],
        'storage': 'file_system',
        'mongodb': f'optional ({mongodb_status})'
    }


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return {'error': 'Endpoint not found', 'status': 404}, 404


@app.errorhandler(500)
def internal_error(error):
    return {'error': 'Internal server error', 'status': 500}, 500


@app.errorhandler(413)
def file_too_large(error):
    return {'error': 'File too large. Maximum size is 50MB', 'status': 413}, 413


# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🚀 RRF GENERATOR API SERVER - Starting")
    logger.info("=" * 70)
    logger.info("Port: 5009")
    logger.info("Storage: File System (uploads/ → outputs/)")
    logger.info("MongoDB: Optional (non-blocking if unavailable)")
    logger.info("")
    logger.info("📡 Available Endpoints:")
    logger.info("  GET  /              - API info")
    logger.info("  GET  /health        - Health check")
    logger.info("  GET  /api/v1/health - Health check (alt)")
    logger.info("  GET  /info          - Tool info")
    logger.info("  GET  /api/v1/info   - Tool info (alt)")
    logger.info("  POST /execute       - Execute RRF generation")
    logger.info("  POST /api/v1/execute - Execute RRF generation (alt)")
    logger.info("  GET  /download/<session_id>/<filename> - Download file")
    logger.info("  GET  /api/v1/download/<session_id>/<filename> - Download file (alt)")
    logger.info("=" * 70)
    logger.info("")
    logger.info("✅ Server ready! Listening on http://0.0.0.0:5009")
    logger.info("🔗 Test: http://localhost:5009/health")
    logger.info("")
    
    app.run(
        host='0.0.0.0',
        port=5009,
        debug=False,
        threaded=True
    )
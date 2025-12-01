import os
import logging
from flask import Flask
from mongoengine import connect
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.DEBUG)

def create_app():
    app = Flask(__name__)
    
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/rm_agent")
    mongodb_uri = os.environ.get("MONGODB_URI")
    connect(host=mongodb_uri, alias='default')
    
    app.config["FILE_STORAGE"] = os.environ.get("FILE_STORAGE", "./storage")
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB (increased from 16MB)
    
    app.config["CAPITALIZATION_THRESHOLD"] = float(os.environ.get("CAPITALIZATION_THRESHOLD", "5000"))
    app.config["MATERIALITY"] = float(os.environ.get("MATERIALITY", "25000"))
    app.config["FY_START"] = os.environ.get("FY_START", "2025-07-01")
    app.config["FY_END"] = os.environ.get("FY_END", "2026-06-30")
    app.config["ALLOWED_ACCOUNTS"] = os.environ.get("ALLOWED_ACCOUNTS", "Repair & Maintenance;Repairs;Maintenance").split(";")
    
    os.makedirs(app.config["FILE_STORAGE"], exist_ok=True)
    
    with app.app_context():
        import models
        
        from api.upload import upload_bp
        from api.runs import runs_bp
        from api.samples import samples_bp
        from api.reports import reports_bp
        from api.exceptions import exceptions_bp
        from web.routes import web_bp
        
        app.register_blueprint(upload_bp, url_prefix='/api')
        app.register_blueprint(runs_bp, url_prefix='/api')
        app.register_blueprint(samples_bp, url_prefix='/api')
        app.register_blueprint(reports_bp, url_prefix='/api')
        app.register_blueprint(exceptions_bp, url_prefix='/api')
        app.register_blueprint(web_bp)
    
    return app

app = create_app()
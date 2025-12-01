import os
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import json
from datetime import datetime

from config import Config
from db_models import (
    Database, GLEntryModel, PopulationModel, SampleModel, 
    AnalysisModel, TestResultModel, ExceptionModel
)
from je_processor import JEProcessor
from risk_analyzer import RiskAnalyzer
from sample_selector import SampleSelector
from artifact_generator import ArtifactGenerator
from gemini_integration import GeminiIntegration

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize MongoDB with connection recovery
db_connection = None
db = None
gl_entry_model = None
population_model = None
sample_model = None
analysis_model = None
test_result_model = None
exception_model = None

def init_mongodb():
    """Initialize or reinitialize MongoDB connection"""
    global db_connection, db, gl_entry_model, population_model, sample_model
    global analysis_model, test_result_model, exception_model
    
    try:
        if db_connection is not None:
            # Test if connection is alive
            try:
                db_connection.client.admin.command('ping')
                logger.debug("Existing MongoDB connection is alive")
                return True
            except:
                logger.warning("Existing MongoDB connection is dead, reconnecting...")
                try:
                    db_connection.close()
                except:
                    pass
                db_connection = None
        
        # Create new connection
        db_connection = Database(app.config['MONGODB_URI'], app.config['MONGODB_DB_NAME'])
        db = db_connection.db
        
        # Initialize models
        gl_entry_model = GLEntryModel(db)
        population_model = PopulationModel(db)
        sample_model = SampleModel(db)
        analysis_model = AnalysisModel(db)
        test_result_model = TestResultModel(db)
        exception_model = ExceptionModel(db)
        
        logger.info("MongoDB models initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB: {str(e)}")
        logger.warning("Running without MongoDB - data will not be persisted")
        db_connection = None
        db = None
        return False

# Initialize MongoDB on startup
init_mongodb()

# Initialize processors
je_processor = JEProcessor()
risk_analyzer = RiskAnalyzer()
sample_selector = SampleSelector()
artifact_generator = ArtifactGenerator()
gemini_integration = GeminiIntegration()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.before_request
def ensure_mongodb_connection():
    """Ensure MongoDB connection is alive before each request"""
    if db is None:
        init_mongodb()
    elif db_connection is not None:
        try:
            # Quick ping to check if connection is alive
            db_connection.client.admin.command('ping', maxTimeMS=1000)
        except:
            logger.warning("MongoDB connection lost, reconnecting...")
            init_mongodb()

@app.route('/')
def index():
    # Get list of uploaded files
    uploaded_files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if allowed_file(filename):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                uploaded_files.append({
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    # Get recent analyses from MongoDB
    recent_analyses = []
    if db is not None:
        try:
            recent_analyses = analysis_model.get_recent_analyses(limit=5)
        except Exception as e:
            logger.error(f"Error fetching recent analyses: {str(e)}")
    
    return render_template('index.html', 
                         uploaded_files=uploaded_files,
                         recent_analyses=recent_analyses)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and save to uploads directory"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files selected'}), 400
        
        files = request.files.getlist('files')
        uploaded_files = []
        
        for file in files:
            if file.filename == '':
                continue
                
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to prevent overwrites
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{name}_{timestamp}{ext}"
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                uploaded_files.append(filename)
                logger.info(f"File uploaded: {filename}")
            else:
                logger.warning(f"Invalid file type: {file.filename}")
        
        if uploaded_files:
            flash(f"Successfully uploaded {len(uploaded_files)} files", "success")
            return jsonify({
                'message': f'Successfully uploaded {len(uploaded_files)} files',
                'files': uploaded_files
            })
        else:
            return jsonify({'error': 'No valid files uploaded'}), 400
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    """Main analysis pipeline with MongoDB integration"""
    analysis_id = None
    
    try:
        # Get parameters from form
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        # Extract parameters with defaults
        investigate_threshold = int(float(data.get('investigate_if', app.config['DEFAULT_INVESTIGATE_THRESHOLD'])))
        high_risk_keywords = data.get('high_risk_rules', 'adjusting,reversal,year-end,correction,JE,manual').split(',')
        period_end_window = int(data.get('period_end_window', app.config['DEFAULT_PERIOD_END_WINDOW']))
        coverage_target = float(data.get('coverage_target', app.config['DEFAULT_COVERAGE_TARGET']))
        materiality = int(float(data.get('materiality', app.config['DEFAULT_MATERIALITY'])))
        period_start = data.get('period_start', '')
        period_end = data.get('period_end', '')
        framework = data.get('framework', 'GAAP')
        
        # Create analysis record in MongoDB
        if db is not None:
            analysis_id = analysis_model.create_analysis({
                'investigate_threshold': investigate_threshold,
                'high_risk_keywords': high_risk_keywords,
                'period_end_window': period_end_window,
                'coverage_target': coverage_target,
                'materiality': materiality,
                'period_start': period_start,
                'period_end': period_end,
                'framework': framework
            })
            logger.info(f"Created analysis record: {analysis_id}")
        
        # Get list of uploaded GL files
        gl_files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.lower().endswith(('.csv', '.xlsx', '.xls')):
                gl_files.append(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        if not gl_files:
            return jsonify({'error': 'No general ledger files found. Please upload CSV or Excel files.'}), 400
        
        logger.info(f"Starting analysis with {len(gl_files)} GL files")
        
        # Step 1: Ingest and validate GL data
        gl_data = je_processor.ingest_gl_files(gl_files)
        if gl_data.empty:
            return jsonify({'error': 'No valid journal entry data found in uploaded files'}), 400
        
        # Save GL entries to MongoDB
        if db is not None and analysis_id:
            gl_entry_model.insert_entries(gl_data, analysis_id)
        
        # Step 2: Build population with risk flags
        population = risk_analyzer.build_population(
            gl_data, 
            high_risk_keywords=high_risk_keywords,
            period_end_window=period_end_window,
            investigate_threshold=investigate_threshold
        )
        
        # Save population to MongoDB
        if db is not None and analysis_id:
            population_model.insert_population(population, analysis_id)
        
        # Step 3: Select samples
        samples = sample_selector.select_samples(
            population,
            coverage_target=coverage_target,
            materiality=materiality
        )
        
        # Save samples to MongoDB
        if db is not None and analysis_id:
            sample_model.insert_samples(samples, analysis_id)
        
        # Step 4: Generate artifacts
        output_files = artifact_generator.generate_all_artifacts(
            population=population,
            samples=samples,
            parameters={
                'investigate_threshold': investigate_threshold,
                'coverage_target': coverage_target,
                'materiality': materiality,
                'period_start': period_start,
                'period_end': period_end,
                'framework': framework
            },
            output_dir=app.config['UPLOAD_FOLDER']
        )
        
        # Step 5: Generate summary memo using Gemini (optional)
        memo_content = gemini_integration.generate_summary_memo(
            population=population,
            samples=samples,
            output_files=output_files
        )
        
        if memo_content:
            memo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'JE_Summary_Memo.md')
            with open(memo_path, 'w', encoding='utf-8') as f:
                f.write(memo_content)
            output_files.append('JE_Summary_Memo.md')
        
        # Calculate metrics
        high_risk_count = len(samples[samples['risk_category'] == 'High Risk']) if not samples.empty else 0
        test_results = artifact_generator.get_test_results()
        
        metrics = {
            "population_count": len(population),
            "sample_count": len(samples),
            "high_risk_selected": high_risk_count,
            "tests_passed": test_results.get('passed', 0),
            "exceptions": test_results.get('exceptions', 0),
            "largest_exception": test_results.get('largest_exception', {})
        }
        
        # Update analysis record in MongoDB
        if db is not None and analysis_id:
            analysis_model.complete_analysis(analysis_id, metrics, output_files)
        
        response = {
            "analysis_id": analysis_id,
            "summary": f"Selected {len(samples)} samples from {len(population)} journal entries for testing. Coverage: {coverage_target*100}% target.",
            "metrics": metrics,
            "files_created": output_files,
            "open_requests": []
        }
        
        logger.info(f"Analysis completed successfully. Generated {len(output_files)} files.")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        # Mark analysis as failed in MongoDB
        if db is not None and analysis_id:
            try:
                analysis_model.update_analysis(analysis_id, {
                    "status": "Failed",
                    "error": str(e),
                    "failed_at": datetime.utcnow()
                })
            except:
                pass
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/analysis/<analysis_id>')
def get_analysis(analysis_id):
    """Get analysis details by ID"""
    try:
        if db is None:
            return jsonify({'error': 'Database not available'}), 503
        
        analysis = analysis_model.get_analysis(analysis_id)
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Convert ObjectId to string
        analysis['_id'] = str(analysis['_id'])
        
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error fetching analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/analysis/<analysis_id>/population')
def get_population(analysis_id):
    """Get population data for an analysis"""
    try:
        if db is None:
            return jsonify({'error': 'Database not available'}), 503
        
        population_df = population_model.get_population_by_analysis(analysis_id)
        if population_df.empty:
            return jsonify({'error': 'No population data found'}), 404
        
        return jsonify(population_df.to_dict('records'))
    except Exception as e:
        logger.error(f"Error fetching population: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/analysis/<analysis_id>/samples')
def get_samples(analysis_id):
    """Get samples for an analysis"""
    try:
        if db is None:
            return jsonify({'error': 'Database not available'}), 503
        
        samples_df = sample_model.get_samples_by_analysis(analysis_id)
        if samples_df.empty:
            return jsonify({'error': 'No samples found'}), 404
        
        return jsonify(samples_df.to_dict('records'))
    except Exception as e:
        logger.error(f"Error fetching samples: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/files/<filename>')
def download_file(filename):
    """Serve generated files from uploads directory"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/results')
def results():
    """Display analysis results and generated files"""
    generated_files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if any(filename.startswith(prefix) for prefix in ['JE_', 'Proposed_']):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                generated_files.append({
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    # Get recent analyses
    recent_analyses = []
    if db is not None:
        try:
            recent_analyses = analysis_model.get_recent_analyses(limit=10)
        except Exception as e:
            logger.error(f"Error fetching recent analyses: {str(e)}")
    
    return render_template('results.html', 
                         generated_files=generated_files,
                         recent_analyses=recent_analyses)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "mongodb": "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if db is not None:
        try:
            db_connection.client.admin.command('ping')
            health_status["mongodb"] = "connected"
        except:
            health_status["mongodb"] = "disconnected"
            health_status["status"] = "degraded"
    
    return jsonify(health_status)

if __name__ == '__main__':
    import atexit
    
    def cleanup_mongodb():
        """Cleanup MongoDB connection on shutdown"""
        global db_connection
        if db_connection is not None:
            try:
                db_connection.close()
                logger.info("MongoDB connection closed on shutdown")
            except Exception as e:
                logger.error(f"Error closing MongoDB: {str(e)}")
    
    # Register cleanup handler
    atexit.register(cleanup_mongodb)
    
    # Run the application
    app.run(host='192.168.100.158', port=8555, debug=True, use_reloader=True)
import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import json
from capex_analyzer import CapExAnalyzer
from flask_pymongo import PyMongo
from datetime import datetime
import time
from bson import ObjectId
import gridfs

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "capex-analyzer-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# MongoDB Configuration
app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/capex_db")

# Configuration
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'pdf', 'txt'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Initialize PyMongo
mongo = PyMongo(app)

# Initialize GridFS for large file storage
fs = gridfs.GridFS(mongo.db)

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to get MongoDB collections
def get_files_collection():
    return mongo.db.uploaded_files
    
def get_results_collection():
    return mongo.db.analysis_results

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page with upload form and results display"""
    
    # Get list of uploaded files from MongoDB
    files_collection = get_files_collection()
    uploaded_files_data = files_collection.find({}, {"filename": 1, "original_filename": 1, "uploaded_on": 1, "_id": 0}).sort("uploaded_on", -1)
    uploaded_files = [d for d in uploaded_files_data]
    
    # Get list of generated output files (still file-based as they are artifacts)
    output_files = []
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith('CapEx_') and filename.endswith(('.xlsx', '.md')) and os.path.isfile(os.path.join(UPLOAD_FOLDER, filename)):
                output_files.append(filename)
    
    # Fetch recent analysis results
    results_collection = get_results_collection()
    recent_results = list(results_collection.find().sort('run_date', -1).limit(10))
    
    # Convert ObjectId to string for JSON serialization
    for result in recent_results:
        result['_id'] = str(result['_id'])
    
    return render_template('index.html', 
                         uploaded_files=uploaded_files, 
                         output_files=output_files,
                         recent_results=recent_results)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle multiple file uploads"""
    try:
        uploaded_files_metadata = []
        files_collection = get_files_collection()
        
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files selected'}), 400
        
        files = request.files.getlist('files[]')
        
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to avoid conflicts
                timestamp = str(int(time.time()))
                name, ext = os.path.splitext(filename)
                unique_filename = f"{name}_{timestamp}{ext}"
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Insert file metadata into MongoDB
                file_metadata = {
                    'original_filename': filename,
                    'filename': unique_filename,
                    'uploaded_on': datetime.utcnow(),
                    'size_bytes': os.path.getsize(file_path),
                    'mimetype': file.mimetype,
                    'status': 'uploaded'
                }
                
                files_collection.insert_one(file_metadata)
                
                uploaded_files_metadata.append(unique_filename)
                logging.info(f"Uploaded file: {unique_filename}")
        
        if uploaded_files_metadata:
            flash(f'Successfully uploaded {len(uploaded_files_metadata)} file(s)', 'success')
            return jsonify({
                'success': True,
                'files': uploaded_files_metadata,
                'message': f'Uploaded {len(uploaded_files_metadata)} file(s) successfully'
            })
        else:
            return jsonify({'error': 'No valid files were uploaded'}), 400
            
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/analyze', methods=['POST'])
def analyze_capex():
    """Run the CapEx analysis pipeline"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        cap_threshold = float(data.get('cap_threshold', 500))
        isi_level = float(data.get('isi_level', 10000))
        coverage_target = float(data.get('coverage_target', 0.75))
        materiality = float(data.get('materiality', 50000))
        
        logging.info(f"Starting analysis with threshold: {cap_threshold}, ISI: {isi_level}")
        
        # Initialize analyzer
        analyzer = CapExAnalyzer(
            upload_folder=UPLOAD_FOLDER,
            cap_threshold=cap_threshold,
            isi_level=isi_level,
            coverage_target=coverage_target,
            materiality=materiality
        )
        
        # Run the analysis pipeline
        result = analyzer.run_analysis()
        
        if result['success']:
            # Save the successful result to MongoDB
            result['run_date'] = datetime.utcnow()
            result['parameters'] = {
                'cap_threshold': cap_threshold,
                'isi_level': isi_level,
                'coverage_target': coverage_target,
                'materiality': materiality
            }
            
            # Convert any non-serializable objects
            result_copy = result.copy()
            inserted_result = get_results_collection().insert_one(result_copy)
            result['result_id'] = str(inserted_result.inserted_id)
            
            # Update file status in MongoDB
            files_collection = get_files_collection()
            files_collection.update_many(
                {'status': 'uploaded'},
                {'$set': {'status': 'analyzed', 'last_analyzed': datetime.utcnow()}}
            )
            
            flash('Analysis completed successfully!', 'success')
            return jsonify(result)
        else:
            flash(f'Analysis failed: {result.get("error", "Unknown error")}', 'error')
            return jsonify(result), 400
            
    except Exception as e:
        logging.error(f"Analysis error: {str(e)}")
        error_msg = f'Analysis failed: {str(e)}'
        flash(error_msg, 'error')
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/results/<result_id>')
def view_result(result_id):
    """View a specific analysis result"""
    try:
        results_collection = get_results_collection()
        result = results_collection.find_one({'_id': ObjectId(result_id)})
        
        if not result:
            flash('Result not found', 'error')
            return redirect(url_for('index'))
        
        # Convert ObjectId to string
        result['_id'] = str(result['_id'])
        
        return render_template('results.html', 
                             summary=result.get('summary'),
                             metrics=result.get('metrics'),
                             files_created=result.get('files_created', []),
                             open_requests=result.get('open_requests', []))
    except Exception as e:
        logging.error(f"Error viewing result: {str(e)}")
        flash('Error loading result', 'error')
        return redirect(url_for('index'))

@app.route('/history')
def view_history():
    """View analysis history"""
    try:
        results_collection = get_results_collection()
        results = list(results_collection.find().sort('run_date', -1).limit(50))
        
        # Convert ObjectId to string
        for result in results:
            result['_id'] = str(result['_id'])
        
        return render_template('history.html', results=results)
    except Exception as e:
        logging.error(f"Error loading history: {str(e)}")
        flash('Error loading history', 'error')
        return redirect(url_for('index'))

@app.route('/files/<filename>')
def download_file(filename):
    """Serve generated files from uploads directory"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        logging.error(f"File download error: {str(e)}")
        flash(f'File not found: {filename}', 'error')
        return redirect(url_for('index'))

@app.route('/delete_file/<filename>', methods=['POST'])
def delete_file(filename):
    """Delete a file from uploads directory and MongoDB"""
    try:
        secure_name = secure_filename(filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
        
        deleted_from_db = False
        deleted_from_fs = False
        
        # Delete from MongoDB
        result = get_files_collection().delete_one({'filename': secure_name})
        if result.deleted_count > 0:
            deleted_from_db = True
            logging.info(f"Deleted {secure_name} from MongoDB")
        
        # Delete from filesystem
        if os.path.exists(file_path):
            os.remove(file_path)
            deleted_from_fs = True
            logging.info(f"Deleted {secure_name} from filesystem")
        
        if deleted_from_db or deleted_from_fs:
            return jsonify({
                'success': True, 
                'message': f'Deleted {filename}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
            
    except Exception as e:
        logging.error(f"File deletion error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/delete_result/<result_id>', methods=['POST'])
def delete_result(result_id):
    """Delete an analysis result"""
    try:
        result = get_results_collection().delete_one({'_id': ObjectId(result_id)})
        
        if result.deleted_count > 0:
            flash('Result deleted successfully', 'success')
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Result not found'}), 404
            
    except Exception as e:
        logging.error(f"Result deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        mongo.db.command('ping')
        mongo_status = 'connected'
    except Exception as e:
        mongo_status = f'error: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'uploads_dir': os.path.exists(UPLOAD_FOLDER),
        'mongodb': mongo_status
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8556)
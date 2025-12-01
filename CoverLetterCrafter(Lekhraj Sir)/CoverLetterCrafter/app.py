import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify, make_response
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import tempfile
import uuid
from utils.excel_processor import ExcelProcessor
from utils.document_generator import DocumentGenerator
from datetime import datetime
import re
import base64
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import io

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# MongoDB configuration - Use environment variable or fallback to local
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/cover_letter_db')
DATABASE_NAME = 'cover_letter_db'  # Default database name

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ——— Database Helpers ——————————————————————————————————————————————————————————

def connect_to_db():
    """Connect to MongoDB database using connection string."""
    try:
        # Create MongoDB client with connection string
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            retryWrites=True
        )
        
        # Test the connection
        client.admin.command('ping')
        
        # Extract database name from URI if present, otherwise use default
        db_name = DATABASE_NAME
        if '/' in MONGODB_URI and '?' in MONGODB_URI:
            extracted_db = MONGODB_URI.split('/')[-1].split('?')[0]
            if extracted_db:
                db_name = extracted_db
        elif '/' in MONGODB_URI and not MONGODB_URI.endswith('/'):
            # Handle URI without query parameters
            parts = MONGODB_URI.split('/')
            if len(parts) > 3 and parts[-1]:
                db_name = parts[-1]
        
        db = client[db_name]
        
        # Mask credentials in log
        log_uri = MONGODB_URI
        if '@' in MONGODB_URI:
            log_uri = 'mongodb://****:****@' + MONGODB_URI.split('@')[-1]
        
        logger.info(f"Connected to MongoDB - URI: {log_uri} - Database: {db_name}")
        return db
        
    except ConnectionFailure as err:
        logger.error(f"MongoDB connection failed: {err}")
        log_uri = MONGODB_URI
        if '@' in MONGODB_URI:
            log_uri = 'mongodb://****:****@' + MONGODB_URI.split('@')[-1]
        logger.error(f"Connection string (masked): {log_uri}")
        raise
    except ConfigurationError as err:
        logger.error(f"MongoDB configuration error: {err}")
        raise
    except Exception as err:
        logger.error(f"Unexpected MongoDB error: {err}")
        raise

def save_cover_letter_record(db, job_id, client_name, draft_type, tax_year,
                           input_excel_name, input_excel_path, input_excel_content,
                           output_docx_name, output_docx_path, output_docx_content,
                           output_pdf_name, output_pdf_path, output_pdf_content,
                           cover_letter_data, log_message, status):
    """Save cover letter processing record to MongoDB, including file contents as Base64 strings."""
    collection = db.processing_records
    record = {
        'job_id': job_id,
        'run_timestamp': datetime.now(),
        'client_name': client_name,
        'draft_type': draft_type,
        'tax_year': tax_year,
        'input_excel_name': input_excel_name,
        'input_excel_path': input_excel_path,
        'input_excel_content': base64.b64encode(input_excel_content).decode('utf-8') if input_excel_content else None,
        'output_docx_name': output_docx_name,
        'output_docx_path': output_docx_path,
        'output_docx_content': base64.b64encode(output_docx_content).decode('utf-8') if output_docx_content else None,
        'output_pdf_name': output_pdf_name,
        'output_pdf_path': output_pdf_path,
        'output_pdf_content': base64.b64encode(output_pdf_content).decode('utf-8') if output_pdf_content else None,
        'cover_letter_data': cover_letter_data,  # Store the processed data as JSON
        'log_message': log_message,
        'status': status
    }
    try:
        result = collection.insert_one(record)
        logger.info(f"Cover letter record saved for job_id: {job_id}, MongoDB ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as err:
        logger.error(f"Failed to save cover letter record to MongoDB: {err}")
        raise

# ——— Existing Helper Functions ——————————————————————————————————————————————————

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_client_short_name(client_name):
    """Generate client short name from full client name"""
    # Remove common business suffixes and convert to uppercase
    business_suffixes = [
        'Pvt Ltd', 'Private Limited', 'Ltd', 'Limited', 
        'Inc.', 'Inc', 'Corporation', 'Corp.', 'Corp', 
        'LLC', 'LLP'
    ]
    # Clean the client name
    clean_name = client_name.strip()
    # Remove commas first
    clean_name = clean_name.replace(',', '')
    # Remove business suffixes (case insensitive)
    for suffix in business_suffixes:
        # Create pattern that matches the suffix at word boundaries
        pattern = rf'\b{re.escape(suffix)}\b'
        clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE).strip()
    # Split into words and get first letter of each word
    words = clean_name.split()
    short_name = ''.join([word[0].upper() for word in words if word])
    return short_name

# ——— Routes ———————————————————————————————————————————————————————————————————

@app.route('/')
def index():
    """Main page for file upload and client name input"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and client name submission with database integration"""
    # Initialize database connection
    db = connect_to_db()
    job_id = str(uuid.uuid4())
    
    try:
        # Check if file was uploaded
        if 'excel_file' not in request.files:
            flash('No file selected', 'error')
            save_cover_letter_record(db, job_id, '', '', '', '', '', None, 
                                   None, None, None, None, None, None, 
                                   {}, 'No file selected', 'FAILURE')
            return redirect(url_for('index'))
        
        file = request.files['excel_file']
        client_name = request.form.get('client_name', '').strip()
        draft_type = request.form.get('draft_type', '').strip()
        tax_year = request.form.get('tax_year', '').strip()
        
        # Validate inputs
        if file.filename == '':
            flash('No file selected', 'error')
            save_cover_letter_record(db, job_id, client_name, draft_type, tax_year, 
                                   '', '', None, None, None, None, None, None, None,
                                   {}, 'Empty filename', 'FAILURE')
            return redirect(url_for('index'))
        
        if not client_name:
            flash('Client name is required', 'error')
            save_cover_letter_record(db, job_id, '', draft_type, tax_year, 
                                   file.filename, '', None, None, None, None, None, None, None,
                                   {}, 'Client name missing', 'FAILURE')
            return redirect(url_for('index'))
        
        if not draft_type:
            flash('Draft type is required', 'error')
            save_cover_letter_record(db, job_id, client_name, '', tax_year, 
                                   file.filename, '', None, None, None, None, None, None, None,
                                   {}, 'Draft type missing', 'FAILURE')
            return redirect(url_for('index'))
        
        if not tax_year:
            flash('Tax year is required', 'error')
            save_cover_letter_record(db, job_id, client_name, draft_type, '', 
                                   file.filename, '', None, None, None, None, None, None, None,
                                   {}, 'Tax year missing', 'FAILURE')
            return redirect(url_for('index'))
        
        if not file.filename or not allowed_file(file.filename):
            flash('Invalid file type. Please upload an Excel file (.xlsx or .xls)', 'error')
            save_cover_letter_record(db, job_id, client_name, draft_type, tax_year, 
                                   file.filename, '', None, None, None, None, None, None, None,
                                   {}, 'Invalid file type', 'FAILURE')
            return redirect(url_for('index'))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_filename = f"{job_id}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Read input file content for database storage
        input_excel_content = None
        try:
            with open(filepath, 'rb') as f:
                input_excel_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read input Excel file: {str(e)}")
            save_cover_letter_record(db, job_id, client_name, draft_type, tax_year, 
                                   filename, filepath, None, None, None, None, None, None, None,
                                   {}, f"File read error: {str(e)}", 'FAILURE')
            flash(f"File read error: {e}", 'error')
            return redirect(url_for('index'))
        
        # Process Excel file
        processor = ExcelProcessor()
        try:
            cover_letter_data = processor.process_excel(filepath, client_name, draft_type, tax_year)
            
            # Store data in session for preview and download
            session['cover_letter_data'] = cover_letter_data
            session['client_name'] = client_name
            session['draft_type'] = draft_type
            session['tax_year'] = tax_year
            session['original_filename'] = filename
            session['job_id'] = job_id  # Store job_id in session
            
            # Save successful processing record (without output files yet)
            save_cover_letter_record(db, job_id, client_name, draft_type, tax_year, 
                                   filename, filepath, input_excel_content, 
                                   None, None, None, None, None, None,
                                   cover_letter_data, 'Excel processing successful', 'PROCESSING')
            
            # Clean up uploaded file
            os.remove(filepath)
            
            return redirect(url_for('preview'))
            
        except Exception as e:
            # Clean up uploaded file on error
            if os.path.exists(filepath):
                os.remove(filepath)
            save_cover_letter_record(db, job_id, client_name, draft_type, tax_year, 
                                   filename, filepath, input_excel_content, 
                                   None, None, None, None, None, None,
                                   {}, f'Excel processing error: {str(e)}', 'FAILURE')
            flash(f'Error processing Excel file: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        save_cover_letter_record(db, job_id, client_name or '', draft_type or '', tax_year or '', 
                               file.filename if 'file' in locals() else '', '', None, 
                               None, None, None, None, None, None,
                               {}, f'Upload error: {str(e)}', 'FAILURE')
        flash('An error occurred while processing your request', 'error')
        return redirect(url_for('index'))

@app.route('/preview')
def preview():
    """Preview the generated cover letter"""
    if 'cover_letter_data' not in session:
        flash('No data to preview. Please upload a file first.', 'error')
        return redirect(url_for('index'))
    
    cover_letter_data = session['cover_letter_data']
    client_name = session['client_name']
    draft_type = session.get('draft_type', 'Preliminary Draft')
    tax_year = session.get('tax_year', '2023')
    job_id = session.get('job_id')
    
    return render_template('preview.html', 
                         cover_letter_data=cover_letter_data, 
                         client_name=client_name,
                         draft_type=draft_type,
                         tax_year=tax_year,
                         job_id=job_id)

@app.route('/download/<format>')
def download(format):
    """Generate and download cover letter in specified format with database storage"""
    if 'cover_letter_data' not in session:
        flash('No data to download. Please upload a file first.', 'error')
        return redirect(url_for('index'))
    
    if format not in ['docx', 'pdf']:
        flash('Invalid format requested', 'error')
        return redirect(url_for('preview'))
    
    db = connect_to_db()
    job_id = session.get('job_id')
    
    try:
        cover_letter_data = session['cover_letter_data']
        client_name = session['client_name']
        draft_type = session.get('draft_type', 'Preliminary Draft')
        tax_year = session.get('tax_year', '2023')
        
        # Generate client short name
        client_short_name = generate_client_short_name(client_name)
        
        # Get current date in MM.DD.YYYY format
        current_date = datetime.now().strftime('%m.%d.%Y')
        
        # Generate document
        generator = DocumentGenerator()
        
        if format == 'docx':
            temp_file = generator.generate_docx(cover_letter_data, client_name)
            filename = f"{client_short_name}_Cover Letter_{current_date}.docx"
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:  # pdf
            temp_file = generator.generate_pdf(cover_letter_data, client_name)
            filename = f"{client_short_name}_Cover Letter_{current_date}.pdf"
            mimetype = 'application/pdf'
        
        # Read generated file content for database storage
        with open(temp_file, 'rb') as f:
            output_content = f.read()
        
        # Update database record with output file
        try:
            collection = db.processing_records
            update_data = {
                'status': 'SUCCESS',
                'log_message': f'Document generated successfully in {format.upper()} format',
                'completion_timestamp': datetime.now()
            }
            
            if format == 'docx':
                update_data.update({
                    'output_docx_name': filename,
                    'output_docx_path': temp_file,
                    'output_docx_content': base64.b64encode(output_content).decode('utf-8')
                })
            else:  # pdf
                update_data.update({
                    'output_pdf_name': filename,
                    'output_pdf_path': temp_file,
                    'output_pdf_content': base64.b64encode(output_content).decode('utf-8')
                })
            
            collection.update_one(
                {'job_id': job_id},
                {'$set': update_data}
            )
            logger.info(f"Updated database record for job_id: {job_id} with {format.upper()} output")
            
        except Exception as e:
            logger.error(f"Failed to update database record: {str(e)}")
            # Continue with download even if DB update fails
        
        return send_file(temp_file, 
                        as_attachment=True, 
                        download_name=filename,
                        mimetype=mimetype)
    
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}")
        
        # Update database with error status
        try:
            if job_id:
                collection = db.processing_records
                collection.update_one(
                    {'job_id': job_id},
                    {'$set': {
                        'status': 'FAILURE',
                        'log_message': f'Download error for {format.upper()}: {str(e)}',
                        'completion_timestamp': datetime.now()
                    }}
                )
        except Exception as db_error:
            logger.error(f"Failed to update error status in database: {str(db_error)}")
        
        flash(f'Error generating {format.upper()} file: {str(e)}', 'error')
        return redirect(url_for('preview'))

@app.route('/download_from_db/<job_id>/<format>')
def download_from_db(job_id, format):
    """Download files directly from database storage"""
    if format not in ['docx', 'pdf']:
        flash('Invalid format requested', 'error')
        return redirect(url_for('index'))
    
    db = connect_to_db()
    collection = db.processing_records
    
    try:
        record = collection.find_one({'job_id': job_id})
        
        if not record:
            flash('Record not found', 'error')
            return redirect(url_for('index'))
        
        # Get the appropriate file content and name
        if format == 'docx':
            file_content_b64 = record.get('output_docx_content')
            filename = record.get('output_docx_name', f"{job_id}_cover_letter.docx")
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:  # pdf
            file_content_b64 = record.get('output_pdf_content')
            filename = record.get('output_pdf_name', f"{job_id}_cover_letter.pdf")
            mimetype = 'application/pdf'
        
        if not file_content_b64:
            flash(f'{format.upper()} file not found in database', 'error')
            return redirect(url_for('index'))
        
        # Decode Base64 content
        file_binary = base64.b64decode(file_content_b64.encode('utf-8'))
        
        # Create in-memory file
        buffer = io.BytesIO(file_binary)
        buffer.seek(0)
        
        response = make_response(buffer.read())
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-Type"] = mimetype
        return response
        
    except Exception as e:
        logger.error(f"Error downloading from database for job_id {job_id}: {e}")
        flash(f"Error downloading file: {e}", "error")
        return redirect(url_for('index'))

@app.route('/history')
def history():
    """View processing history from database"""
    db = connect_to_db()
    collection = db.processing_records
    
    try:
        # Get recent records, sorted by timestamp (most recent first)
        records = list(collection.find({}).sort('run_timestamp', -1).limit(50))
        
        # Convert ObjectId to string for template rendering
        for record in records:
            record['_id'] = str(record['_id'])
            # Format timestamp for display
            if 'run_timestamp' in record:
                record['formatted_timestamp'] = record['run_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        return render_template('history.html', records=records)
    
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        flash(f"Error loading history: {e}", "error")
        return redirect(url_for('index'))

@app.route('/record/<job_id>')
def view_record(job_id):
    """View detailed record information"""
    db = connect_to_db()
    collection = db.processing_records
    
    try:
        record = collection.find_one({'job_id': job_id})
        
        if not record:
            flash('Record not found', 'error')
            return redirect(url_for('history'))
        
        # Convert ObjectId to string
        record['_id'] = str(record['_id'])
        
        # Format timestamps
        if 'run_timestamp' in record:
            record['formatted_run_timestamp'] = record['run_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if 'completion_timestamp' in record:
            record['formatted_completion_timestamp'] = record['completion_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        return render_template('record_detail.html', record=record)
    
    except Exception as e:
        logger.error(f"Error fetching record {job_id}: {e}")
        flash(f"Error loading record: {e}", "error")
        return redirect(url_for('history'))

@app.route('/new')
def new_letter():
    """Clear session and start new cover letter"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Health check endpoint to verify MongoDB connection"""
    try:
        db = connect_to_db()
        # Try to ping the database
        db.command('ping')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'message': 'Application is running and database is connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 503

# ——— Error Handlers ———————————————————————————————————————————————————————————

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    flash('File too large. Maximum size is 16MB.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    app.logger.error(f"Internal error: {str(e)}")
    flash('An internal error occurred. Please try again.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='192.168.100.158', port=8512, debug=True)
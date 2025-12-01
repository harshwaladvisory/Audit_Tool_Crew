"""
Accufund Formatter with MongoDB - API Endpoints
"""

from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from werkzeug.utils import secure_filename
import os
import logging
import uuid
from datetime import datetime
from pathlib import Path
import pandas as pd
from pymongo import MongoClient
from bson import ObjectId
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# ... rest of your code ...
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')

# MongoDB Configuration - UPDATED WITH NEW CONNECTION STRING
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://Administrator:Hcsllp%21%402010@192.168.100.84:27017/accufund_db?authSource=admin&directConnection=true')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'accufund_db')

# Initialize MongoDB client with error handling
try:
    print(f"🔗 Attempting to connect to MongoDB...")
    print(f"📍 Server: 192.168.100.84:27017")
    print(f"🗄️  Database: {MONGO_DB_NAME}")
    
    mongo_client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    
    # Test the connection
    mongo_client.admin.command('ping')
    print("✅ Successfully connected to MongoDB!")
    
    db = mongo_client[MONGO_DB_NAME]
    
    # Collections
    files_collection = db['files']
    logs_collection = db['processing_logs']
    
except Exception as e:
    print(f"❌ MongoDB Connection Error: {str(e)}")
    print("⚠️  Application will start but database features will not work")
    db = None
    files_collection = None
    logs_collection = None

# File upload configuration
UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file_metadata(original_name, unique_filename, file_size):
    """Save file metadata to MongoDB"""
    if files_collection is None:
        return None
    
    try:
        file_doc = {
            'original_filename': original_name,
            'unique_filename': unique_filename,
            'file_size': file_size,
            'upload_date': datetime.utcnow(),
            'status': 'uploaded',
            'processed_date': None,
            'download_count': 0,
            'error_message': None
        }
        result = files_collection.insert_one(file_doc)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error saving file metadata: {e}")
        return None


def update_file_status(file_id, status, error_message=None, processed_date=None):
    """Update file processing status in MongoDB"""
    if files_collection is None or file_id is None:
        return
    
    try:
        update_data = {
            'status': status,
            'error_message': error_message
        }
        if processed_date:
            update_data['processed_date'] = processed_date
        
        files_collection.update_one(
            {'_id': ObjectId(file_id)},
            {'$set': update_data}
        )
    except Exception as e:
        print(f"Error updating file status: {e}")


def log_processing(file_id, original_name, success, rows_processed=0, rows_removed=0, error_message=None):
    """Log processing details to MongoDB"""
    if logs_collection is None:
        return
    
    try:
        log_doc = {
            'file_id': ObjectId(file_id) if file_id else None,
            'original_filename': original_name,
            'timestamp': datetime.utcnow(),
            'success': success,
            'rows_processed': rows_processed,
            'rows_removed': rows_removed,
            'error_message': error_message
        }
        logs_collection.insert_one(log_doc)
    except Exception as e:
        print(f"Error logging processing: {e}")


def increment_download_count(file_id):
    """Increment download counter for a file"""
    if files_collection is None or file_id is None:
        return
    
    try:
        files_collection.update_one(
            {'_id': ObjectId(file_id)},
            {'$inc': {'download_count': 1}}
        )
    except Exception as e:
        print(f"Error incrementing download count: {e}")


def get_statistics():
    """Get statistics from database"""
    if files_collection is None:
        return {
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'total_downloads': 0
        }
    
    try:
        # Total files
        total_files = files_collection.count_documents({})
        
        # Files by status
        processed_count = files_collection.count_documents({'status': 'processed'})
        failed_count = files_collection.count_documents({'status': 'failed'})
        
        # Total downloads
        pipeline = [
            {'$group': {'_id': None, 'total_downloads': {'$sum': '$download_count'}}}
        ]
        download_stats = list(files_collection.aggregate(pipeline))
        total_downloads = download_stats[0]['total_downloads'] if download_stats else 0
        
        return {
            'total_files': total_files,
            'processed': processed_count,
            'failed': failed_count,
            'total_downloads': total_downloads
        }
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return {
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'total_downloads': 0
        }


@app.route('/')
def index():
    """Home page with statistics"""
    stats = get_statistics()
    return render_template('index.html', stats=stats)

def process_excel_file(filepath):
    """
    Process Excel file and format it for Accufund
    Adds Fund, Dept, MEPA, GL Code, Type, F.Y., Balance columns
    """
    try:
        # Read the Excel file
        df = pd.read_excel(filepath)
        
        # Create new formatted dataframe with Accufund structure
        formatted_df = pd.DataFrame()
        
        # Add required Accufund columns
        # Adjust these mappings based on your actual Excel structure
        formatted_df['Fund'] = ''  # Empty or map from existing column
        formatted_df['Dept'] = ''  # Empty or map from existing column
        formatted_df['MEPA'] = ''  # Empty or map from existing column
        
        # Try to map GL Code from common column names
        if 'Account' in df.columns:
            formatted_df['GL Code'] = df['Account']
        elif 'GL Account' in df.columns:
            formatted_df['GL Code'] = df['GL Account']
        elif 'Account Number' in df.columns:
            formatted_df['GL Code'] = df['Account Number']
        else:
            # Use first column as GL Code
            formatted_df['GL Code'] = df.iloc[:, 0]
        
        # Add Type column
        formatted_df['Type'] = ''
        
        # Add F.Y. (Fiscal Year) column
        formatted_df['F.Y.'] = ''
        
        # Try to map Balance from common column names
        if 'Balance' in df.columns:
            formatted_df['Balance'] = df['Balance']
        elif 'Amount' in df.columns:
            formatted_df['Balance'] = df['Amount']
        elif 'Debit' in df.columns and 'Credit' in df.columns:
            formatted_df['Balance'] = df['Debit'] - df['Credit']
        else:
            # Use last numeric column as Balance
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                formatted_df['Balance'] = df[numeric_cols[-1]]
            else:
                formatted_df['Balance'] = 0
        
        # Create Excel writer to save with specific sheet name
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            formatted_df.to_excel(writer, sheet_name='#Formatted', index=False)
        
        logger.info(f"✓ Processing complete: {len(formatted_df)} rows formatted")
        
        return {
            'rows_processed': len(formatted_df),
            'rows_removed': len(df) - len(formatted_df),
            'columns_added': list(formatted_df.columns)
        }
        
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")
        raise

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        filepath = UPLOAD_FOLDER / unique_filename
        
        # Save file to disk
        file.save(filepath)
        file_size = filepath.stat().st_size
        
        # Save metadata to MongoDB
        file_id = save_file_metadata(original_filename, unique_filename, file_size)
        
        try:
            # Process the Excel file
            process_excel_file(filepath)
            
            # Update status to processed
            update_file_status(file_id, 'processed', processed_date=datetime.utcnow())
            
            # Log successful processing
            log_processing(file_id, original_filename, success=True)
            
            # Store in session for download
            session['processed_file'] = unique_filename
            session['original_name'] = original_filename
            session['file_id'] = file_id
            
            flash(f'Successfully processed {original_filename}! Your formatted file is ready for download.', 'success')
            return render_template('download.html', filename=original_filename, unique_id=unique_filename)
        
        except Exception as e:
            error_msg = str(e)
            
            # Update status to failed
            update_file_status(file_id, 'failed', error_message=error_msg)
            
            # Log failed processing
            log_processing(file_id, original_filename, success=False, error_message=error_msg)
            
            flash(f'Error processing file: {error_msg}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload an Excel file (.xlsx)', 'error')
        return redirect(url_for('index'))


@app.route('/download/<unique_id>')
def download_file(unique_id):
    """Handle file download"""
    if 'processed_file' not in session or session['processed_file'] != unique_id:
        flash('Invalid download link or session expired', 'error')
        return redirect(url_for('index'))
    
    filepath = UPLOAD_FOLDER / secure_filename(unique_id)
    original_name = session.get('original_name', 'formatted_file.xlsx')
    file_id = session.get('file_id')
    
    if filepath.exists():
        # Increment download counter in MongoDB
        if file_id:
            increment_download_count(file_id)
        
        return send_file(filepath, as_attachment=True, download_name=f'formatted_{original_name}')
    else:
        flash('File not found', 'error')
        return redirect(url_for('index'))


@app.route('/delete/<file_id>')
def delete_file_record(file_id):
    """Delete file from database and filesystem"""
    if files_collection is None:
        flash('Database not available', 'error')
        return redirect(url_for('file_history'))
    
    try:
        # Get file information from database
        file_doc = files_collection.find_one({'_id': ObjectId(file_id)})
        
        if not file_doc:
            flash('File not found in database', 'error')
            return redirect(url_for('file_history'))
        
        # Delete physical file from uploads folder
        filepath = UPLOAD_FOLDER / file_doc['unique_filename']
        if filepath.exists():
            try:
                filepath.unlink()
                print(f"Deleted physical file: {filepath}")
            except Exception as e:
                print(f"Error deleting physical file: {e}")
        
        # Delete file metadata from database
        files_collection.delete_one({'_id': ObjectId(file_id)})
        
        # Delete associated processing logs
        if logs_collection:
            logs_collection.delete_many({'file_id': ObjectId(file_id)})
        
        flash(f'Successfully deleted file: {file_doc["original_filename"]}', 'success')
        
    except Exception as e:
        flash(f'Error deleting file: {str(e)}', 'error')
    
    return redirect(url_for('file_history'))


@app.route('/delete-all', methods=['POST'])
def delete_all_files():
    """Delete all files from database and filesystem"""
    if files_collection is None:
        flash('Database not available', 'error')
        return redirect(url_for('file_history'))
    
    try:
        # Get all files
        all_files = list(files_collection.find())
        deleted_count = 0
        
        for file_doc in all_files:
            # Delete physical file
            filepath = UPLOAD_FOLDER / file_doc['unique_filename']
            if filepath.exists():
                try:
                    filepath.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting file {filepath}: {e}")
        
        # Delete all file metadata from database
        files_collection.delete_many({})
        
        # Delete all processing logs
        if logs_collection:
            logs_collection.delete_many({})
        
        flash(f'Successfully deleted {deleted_count} files and cleared all records', 'success')
        
    except Exception as e:
        flash(f'Error deleting files: {str(e)}', 'error')
    
    return redirect(url_for('file_history'))


@app.route('/history')
def file_history():
    """View file processing history"""
    if files_collection is None:
        flash('Database not available', 'error')
        return render_template('history.html', files=[])
    
    try:
        # Get all files from MongoDB, sorted by upload date (newest first)
        files = list(files_collection.find().sort('upload_date', -1).limit(50))
        return render_template('history.html', files=files)
    except Exception as e:
        print(f"Error fetching file history: {e}")
        flash('Error loading file history', 'error')
        return render_template('history.html', files=[])


@app.route('/stats')
def statistics():
    """View processing statistics"""
    # Get basic statistics
    stats = get_statistics()
    
    # Add recent processing logs
    if logs_collection:
        try:
            recent_logs = list(logs_collection.find().sort('timestamp', -1).limit(10))
            stats['recent_logs'] = recent_logs
        except Exception as e:
            print(f"Error fetching recent logs: {e}")
            stats['recent_logs'] = []
    else:
        stats['recent_logs'] = []
    
    return render_template('stats.html', stats=stats)


@app.route('/test-db')
def test_db():
    """Test database connection"""
    try:
        if mongo_client is None:
            return "❌ MongoDB client not initialized", 500
        
        # Test connection
        mongo_client.admin.command('ping')
        
        # Get database info
        db_list = mongo_client.list_database_names()
        
        return f"""
        ✅ MongoDB Connection Successful!
        <br><br>
        📊 Available Databases: {', '.join(db_list)}
        <br>
        🗄️  Current Database: {MONGO_DB_NAME}
        <br>
        📁 Collections: {', '.join(db.list_collection_names()) if db else 'N/A'}
        """
    except Exception as e:
        return f"❌ MongoDB Connection Failed: {str(e)}", 500


@app.teardown_appcontext
def close_db_connection(error):
    """Close MongoDB connection when app context ends"""
    if error:
        print(f"Error during request: {error}")


# ============================================================================
# API ENDPOINTS FOR AI ASSISTANT (Add after line 187)
# ============================================================================

@app.route('/api/v1/format', methods=['POST'])
def api_format_accufund():
    """
    API endpoint for AI assistant to format Accufund files
    
    Request (multipart/form-data):
    - file: Excel file to format
    - format_type: (optional) 'standard' (default)
    - output_format: (optional) 'excel' or 'csv' (default: 'excel')
    
    Response:
    {
        "success": true,
        "tool_id": "accufund_formatter",
        "output_file": "/path/to/formatted.xlsx",
        "download_url": "/api/v1/download/<file_id>",
        "summary": {
            "rows_processed": 150,
            "rows_removed": 25,
            "columns_added": ["Fund", "Dept", "MEPA", "GL Code", "Type", "F.Y.", "Balance"]
        }
    }
    """
    try:
        logger.info("=" * 70)
        logger.info("API: Accufund Format Request")
        logger.info("=" * 70)
        
        # Validate file upload
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'error_type': 'missing_file'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Empty filename',
                'error_type': 'invalid_file'
            }), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only .xlsx files allowed',
                'error_type': 'invalid_file_type'
            }), 400
        
        # Get optional parameters
        format_type = request.form.get('format_type', 'standard')
        output_format = request.form.get('output_format', 'excel')
        
        logger.info(f"File: {file.filename}")
        logger.info(f"Format Type: {format_type}")
        logger.info(f"Output Format: {output_format}")
        
        # Save uploaded file with unique name
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        filepath = UPLOAD_FOLDER / unique_filename
        
        file.save(filepath)
        file_size = filepath.stat().st_size
        
        logger.info(f"✓ Saved file: {filepath} ({file_size:,} bytes)")
        
        # Save metadata to MongoDB
        file_id = save_file_metadata(original_filename, unique_filename, file_size)
        
        # Process the Excel file using your existing logic
        from datetime import datetime
        start_time = datetime.utcnow()
        
        process_excel_file(filepath)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update status
        update_file_status(file_id, 'processed', processed_date=datetime.utcnow())
        
        # Verify output file exists
        if not filepath.exists():
            raise FileNotFoundError("Formatted file not created")
        
        output_size = filepath.stat().st_size
        
        # Generate download URL
        download_url = f"/api/v1/download/{unique_filename}"
        
        # Build response
        response = {
            'success': True,
            'tool_id': 'accufund_formatter',
            'tool_name': 'Accufund Formatter',
            'output_file': str(filepath),
            'download_url': download_url,
            'file_id': unique_filename,
            'summary': {
                'original_filename': original_filename,
                'output_size_bytes': output_size,
                'processing_time_ms': processing_time,
                'columns_added': ['Fund', 'Dept', 'MEPA', 'GL Code', 'Type', 'F.Y.', 'Balance'],
                'sheet_name': '#Formatted'
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("✅ API: Accufund Format Complete")
        logger.info("=" * 70)
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ API Error: {e}", exc_info=True)
        
        if file_id:
            update_file_status(file_id, 'failed', error_message=str(e))
        
        return jsonify({
            'success': False,
            'tool_id': 'accufund_formatter',
            'error': str(e),
            'error_type': 'processing_error',
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/download/<file_id>', methods=['GET'])
def api_download_file(file_id: str):
    """Download formatted file by ID"""
    try:
        safe_file_id = secure_filename(file_id)
        filepath = UPLOAD_FOLDER / safe_file_id
        
        if not filepath.exists():
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=f"formatted_{safe_file_id}"
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v1/health', methods=['GET'])
def api_health():
    """Health check endpoint"""
    db_status = 'connected' if db is not None else 'disconnected'
    
    return jsonify({
        'status': 'healthy',
        'tool_id': 'accufund_formatter',
        'tool_name': 'Accufund Formatter',
        'version': '1.0.0',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/v1/info', methods=['GET'])
def api_info():
    """Tool information endpoint"""
    return jsonify({
        'tool_id': 'accufund_formatter',
        'tool_name': 'Accufund Formatter',
        'description': 'Formats Excel files to Accufund-compatible format with Fund, Dept, MEPA, GL Code, Type, F.Y., and Balance columns',
        'category': 'accounting',
        'version': '1.0.0',
        'port': 8580,
        'required_params': [
            {
                'name': 'file',
                'type': 'file',
                'description': 'Excel file to format (.xlsx)',
                'allowed_types': ['.xlsx']
            }
        ],
        'optional_params': [
            {
                'name': 'format_type',
                'type': 'string',
                'default': 'standard',
                'options': ['standard']
            },
            {
                'name': 'output_format',
                'type': 'string',
                'default': 'excel',
                'options': ['excel', 'csv']
            }
        ],
        'returns': {
            'output_file': 'Path to formatted Excel file',
            'download_url': 'URL to download file',
            'summary': 'Processing statistics and metadata'
        },
        'examples': [
            'Format this Excel file for Accufund',
            'Convert accounting data to Accufund format',
            'Process general ledger file'
        ]
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
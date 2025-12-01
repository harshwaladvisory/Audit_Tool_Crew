#!/usr/bin/env python3
"""
Securities Deposits Analysis AI Agent (MongoDB version)
"""

import os
import sys

print("Starting application...")

try:
    from flask import Flask, render_template, request, jsonify, send_file
    from mongoengine import connect
    from werkzeug.utils import secure_filename
    from werkzeug.exceptions import RequestEntityTooLarge
    from datetime import datetime
    import json
    import traceback
    
    print("✓ Imports successful")
    
except Exception as e:
    print(f"✗ Import Error: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# Try loading config
try:
    from config import Config
    print("✓ Config loaded")
except Exception as e:
    print(f"✗ Config Error: {str(e)}")
    print("Creating default config...")
    
    class Config:
        SECRET_KEY = 'dev-secret-key-change-in-production'
        UPLOAD_FOLDER = 'uploads'
        MAX_CONTENT_LENGTH = 16 * 1024 * 1024
        MONGODB_DB = 'depositsense'
        MONGODB_HOST = 'localhost'
        MONGODB_PORT = 27017

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

print(f"✓ Flask app created")

@app.after_request
def add_no_cache_headers(response):
    """Prevent caching."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Initialize MongoDB
try:
    connect(
        db=app.config['MONGODB_DB'],
        host=app.config['MONGODB_HOST'],
        port=app.config['MONGODB_PORT']
    )
    print(f"✓ Connected to MongoDB: {app.config['MONGODB_DB']}")
except Exception as e:
    print(f"✗ MongoDB connection failed: {str(e)}")
    print("Please ensure MongoDB is running on localhost:27017")

# Import models
try:
    from models import FileUpload, Deposit, InterestCalculation, AgingAnalysis, AuditProgram, Report, AuditLog
    print("✓ Models imported")
except Exception as e:
    print(f"✗ Models import error: {str(e)}")
    traceback.print_exc()

# Custom Jinja2 filter
@app.template_filter('datetime_format')
def datetime_format(value, format='%Y-%m-%d %H:%M'):
    """Format datetime."""
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime(format)
    return str(value)

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Routes
@app.route('/')
def dashboard():
    """Dashboard."""
    try:
        stats = get_dashboard_stats()
        recent_activity = get_recent_activity()
        return render_template('dashboard.html', stats=stats, recent_activity=recent_activity)
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        traceback.print_exc()
        return f"<h1>Error</h1><pre>{str(e)}\n\n{traceback.format_exc()}</pre>", 500

@app.route('/file-upload')
def file_upload_page():
    """File upload page."""
    return render_template('file_upload.html')

@app.route('/api/upload-file', methods=['POST'])
def upload_file():
    """Handle file upload with PDF support."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            file_upload = FileUpload(
                filename=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                status='uploaded'
            )
            file_upload.save()
            
            from services.file_processor import FileProcessor
            file_processor = FileProcessor()
            
            try:
                result = file_processor.process_file(file_path, str(file_upload.id))
                return jsonify({
                    'message': 'File processed successfully',
                    'file_id': str(file_upload.id),
                    'processed_records': result['records_processed']
                })
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
        else:
            return jsonify({'error': 'Invalid file format. Supported: .xlsx, .xls, .csv, .pdf'}), 400
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-file-upload/<file_id>', methods=['DELETE'])
def delete_file_upload(file_id):
    """Delete file and deposits."""
    try:
        file_upload = FileUpload.objects(id=file_id).first()
        if not file_upload:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        deposits = list(Deposit.objects(file_upload=file_upload))
        
        aging_deleted = 0
        interest_deleted = 0
        for deposit in deposits:
            aging_deleted += AgingAnalysis.objects(deposit=deposit).delete()
            interest_deleted += InterestCalculation.objects(deposit=deposit).delete()
        
        deposits_deleted = Deposit.objects(file_upload=file_upload).delete()
        
        if file_upload.file_path and os.path.exists(file_upload.file_path):
            os.remove(file_upload.file_path)
        
        file_upload.delete()
        
        return jsonify({
            'success': True,
            'deposits_deleted': deposits_deleted,
            'aging_deleted': aging_deleted,
            'interest_deleted': interest_deleted
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/deposits-analysis')
def deposits_analysis():
    """Deposits page."""
    deposits = Deposit.objects.order_by('-created_at').limit(100)
    return render_template('deposits_analysis.html', deposits=deposits)

@app.route('/aging-analysis')
def aging_analysis_page():
    """Aging analysis."""
    from services.analysis_engine import AnalysisEngine
    try:
        aging_data = AnalysisEngine().perform_aging_analysis()
    except:
        aging_data = None
    return render_template('aging_analysis.html', aging_data=aging_data)

@app.route('/interest-accrual')
def interest_accrual_page():
    """Interest accrual."""
    from services.analysis_engine import AnalysisEngine
    try:
        interest_data = AnalysisEngine().calculate_interest_accruals()
    except:
        interest_data = None
    return render_template('interest_accrual.html', interest_data=interest_data)

@app.route('/unclaimed-deposits')
def unclaimed_deposits_page():
    """Unclaimed deposits."""
    from services.analysis_engine import AnalysisEngine
    try:
        unclaimed_data = AnalysisEngine().identify_unclaimed_deposits()
    except:
        unclaimed_data = None
    return render_template('unclaimed_deposits.html', unclaimed_data=unclaimed_data)

@app.route('/audit-program')
def audit_program_page():
    """Audit program."""
    return render_template('audit_program.html')

@app.route('/reports')
def reports_page():
    """Reports."""
    reports = Report.objects.order_by('-created_at')
    return render_template('reports.html', reports=reports)

@app.route('/api/files-list')
def files_list():
    """Get files list."""
    try:
        files = FileUpload.objects.order_by('-created_at')
        files_data = []
        for file in files:
            deposit_count = Deposit.objects(file_upload=file).count()
            files_data.append({
                'id': str(file.id),
                'filename': file.filename,
                'created_at': file.created_at.isoformat(),
                'status': file.status,
                'records_processed': deposit_count
            })
        return jsonify({'success': True, 'files': files_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete-all-files', methods=['DELETE'])
def delete_all_files():
    """Delete all files."""
    try:
        files_count = FileUpload.objects.count()
        deposits_count = Deposit.objects.count()
        
        AgingAnalysis.objects.delete()
        InterestCalculation.objects.delete()
        Deposit.objects.delete()
        FileUpload.objects.delete()
        
        return jsonify({
            'success': True,
            'files_deleted': files_count,
            'deposits_deleted': deposits_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cleanup-orphaned-data', methods=['DELETE'])
def cleanup_orphaned_data():
    """Cleanup orphaned deposits."""
    try:
        valid_file_ids = [file.id for file in FileUpload.objects]
        if len(valid_file_ids) == 0:
            orphaned = Deposit.objects.delete()
        else:
            orphaned = Deposit.objects(file_upload__nin=valid_file_ids).delete()
            orphaned += Deposit.objects(file_upload=None).delete()
        
        return jsonify({'success': True, 'deposits_deleted': orphaned})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Utility functions
def allowed_file(filename):
    """Check file extension - INCLUDES PDF."""
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_dashboard_stats():
    """Get dashboard stats."""
    try:
        deposit_count = Deposit.objects.count()
        file_count = FileUpload.objects.count()
        
        if deposit_count > 0:
            pipeline = [{'$group': {'_id': None, 'total': {'$sum': '$amount'}}}]
            result = list(Deposit.objects.aggregate(pipeline))
            total_deposits = result[0]['total'] if result else 0
        else:
            total_deposits = 0
        
        overdue = Deposit.objects(maturity_date__exists=True, maturity_date__lt=datetime.now().date()).count()
        unclaimed = Deposit.objects(status='unclaimed').count()
        
        return {
            'totalDeposits': f"${total_deposits:,.2f}",
            'depositCount': deposit_count,
            'overdueDeposits': overdue,
            'unclaimedDeposits': unclaimed,
            'fileCount': file_count
        }
    except Exception as e:
        print(f"Stats error: {str(e)}")
        return {
            'totalDeposits': "$0.00",
            'depositCount': 0,
            'overdueDeposits': 0,
            'unclaimedDeposits': 0,
            'fileCount': 0
        }

def get_recent_activity():
    """Get recent activity."""
    try:
        uploads = FileUpload.objects.order_by('-created_at').limit(5)
        activity = []
        for upload in uploads:
            activity.append({
                'type': 'file_upload',
                'description': f"Uploaded {upload.filename}",
                'timestamp': upload.created_at.isoformat(),
                'status': upload.status,
                'file_id': str(upload.id)
            })
        return activity
    except:
        return []
@app.route('/api/run-aging-analysis', methods=['POST'])
def run_aging_analysis():
    """Run aging analysis."""
    try:
        from services.analysis_engine import AnalysisEngine
        engine = AnalysisEngine()
        result = engine.perform_aging_analysis()
        return jsonify(result)
    except Exception as e:
        print(f"Error running aging analysis: {str(e)}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/calculate-interest', methods=['POST'])
def calculate_interest():
    """Calculate interest accruals."""
    try:
        from services.analysis_engine import AnalysisEngine
        engine = AnalysisEngine()
        result = engine.calculate_interest_accruals()
        return jsonify(result)
    except Exception as e:
        print(f"Error calculating interest: {str(e)}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    
@app.route('/api/aging-summary', methods=['GET'])
def get_aging_summary():
    """Get aging analysis summary for charts."""
    try:
        from services.analysis_engine import AnalysisEngine
        engine = AnalysisEngine()
        summary = engine._generate_aging_summary()
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        print(f"Error getting summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Add this to your app.py file

@app.route('/api/generate-audit-program', methods=['POST'])
def generate_audit_program():
    """Generate audit program based on organization type."""
    try:
        data = request.get_json()
        org_type = data.get('org_type')
        program_type = data.get('program_type')
        
        if not org_type or not program_type:
            return jsonify({'error': 'Missing org_type or program_type'}), 400
        
        from services.audit_program_generator import AuditProgramGenerator
        
        generator = AuditProgramGenerator()
        program = generator.generate_program(org_type, program_type)
        
        # Save to database
        from models import AuditProgram
        audit_program = AuditProgram(
            name=program['name'],
            description=program['description'],
            procedures=[],
            status='active'
        )
        audit_program.save()
        
        return jsonify({'success': True, 'program': program})
        
    except Exception as e:
        print(f"Error generating audit program: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Securities Deposits Analysis - Starting...")
    print("=" * 60)
    app.run(host='0.0.0.0', port=8567, debug=True)

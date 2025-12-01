"""
Capital Addition Sampling & Testwork API
Standardized API for audit capital expenditure analysis
Port: 5005
"""

import os
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
from pathlib import Path
from capex_analyzer_api import CapExAnalyzer

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
UPLOAD_FOLDER = Path('./uploads')
OUTPUT_FOLDER = Path('./outputs')
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'pdf', 'txt'}

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['OUTPUT_FOLDER'] = str(OUTPUT_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Capital Outlay Analysis API',
        'version': '1.0.0',
        'port': 5005
    }), 200


@app.route('/api/v1/info', methods=['GET'])
def get_info():
    """Get tool information"""
    return jsonify({
        'tool_id': 'capital_outlay',
        'name': 'Capital Addition Sampling & Testwork',
        'description': 'Comprehensive capital expenditure analysis and audit workpaper generation',
        'version': '1.0.0',
        'parameters': {
            'cap_threshold': {
                'type': 'float',
                'default': 500,
                'description': 'Capitalization threshold in dollars'
            },
            'isi_level': {
                'type': 'float',
                'default': 10000,
                'description': 'Individual Significant Item (ISI) level in dollars'
            },
            'coverage_target': {
                'type': 'float',
                'default': 0.75,
                'description': 'Target coverage percentage (0-1)'
            },
            'materiality': {
                'type': 'float',
                'default': 50000,
                'description': 'Materiality threshold in dollars'
            }
        },
        'required_files': ['gl_file'],
        'optional_files': ['tb_file', 'policy_file'],
        'output_files': [
            'CapEx_Population.xlsx',
            'CapEx_Sample_Selection.xlsx',
            'CapEx_PBC_Request_List.xlsx',
            'CapEx_Test_Workpaper.xlsx',
            'CapEx_Exceptions_Log.xlsx',
            'Proposed_AJEs.xlsx',
            'CapEx_Summary_Memo.md'
        ]
    }), 200


@app.route('/api/v1/execute', methods=['POST'])
def execute_analysis():
    """Execute capital outlay analysis"""
    try:
        start_time = datetime.now()
        
        # Get parameters
        cap_threshold = float(request.form.get('cap_threshold', 500))
        isi_level = float(request.form.get('isi_level', 10000))
        coverage_target = float(request.form.get('coverage_target', 0.75))
        materiality = float(request.form.get('materiality', 50000))
        
        logger.info("=" * 70)
        logger.info("CAPITAL OUTLAY ANALYSIS: Starting execution")
        logger.info("=" * 70)
        logger.info(f"Parameters: cap_threshold=${cap_threshold}, isi_level=${isi_level}, "
                   f"coverage={coverage_target}, materiality=${materiality}")
        
        # Handle file uploads
        if not request.files:
            return jsonify({
                'success': False,
                'error': 'No files provided. Upload GL file (required) and optionally TB/policy files.'
            }), 400
        
        # Create unique session folder
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_folder = UPLOAD_FOLDER / session_id
        session_folder.mkdir(exist_ok=True)
        
        saved_files = {}
        
        # Save uploaded files
        for field_name in ['gl_file', 'tb_file', 'policy_file']:
            if field_name in request.files:
                file = request.files[field_name]
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp_filename = f"{session_id}_{field_name}_{filename}"
                    filepath = session_folder / timestamp_filename
                    file.save(str(filepath))
                    saved_files[field_name] = str(filepath)
                    logger.info(f"Saved {field_name}: {timestamp_filename}")
        
        if 'gl_file' not in saved_files:
            return jsonify({
                'success': False,
                'error': 'GL file is required for analysis'
            }), 400
        
        logger.info("Files saved, starting analysis...")
        
        # Initialize analyzer
        analyzer = CapExAnalyzer(
            upload_folder=str(session_folder),
            cap_threshold=cap_threshold,
            isi_level=isi_level,
            coverage_target=coverage_target,
            materiality=materiality
        )
        
        # Run analysis
        result = analyzer.run_analysis()
        
        if not result.get('success'):
            logger.error(f"Analysis failed: {result.get('error')}")
            return jsonify(result), 400
        
        # Move output files to outputs folder
        output_session = OUTPUT_FOLDER / session_id
        output_session.mkdir(exist_ok=True)
        
        download_urls = []
        files_created = result.get('files_created', [])
        
        for filename in files_created:
            src_file = session_folder / filename
            if src_file.exists():
                dst_file = output_session / filename
                src_file.rename(dst_file)
                download_urls.append(f"/api/v1/download/{session_id}/{filename}")
                logger.info(f"Moved output: {filename}")
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info("=" * 70)
        logger.info("SUMMARY:")
        logger.info(f"  Population: {result['metrics']['population_count']}")
        logger.info(f"  Samples: {result['metrics']['sample_count']}")
        logger.info(f"  CapEx Value: ${result['metrics']['capex_value']:,.2f}")
        logger.info(f"  Exceptions: {result['metrics']['exceptions']}")
        logger.info(f"  Files Created: {len(download_urls)}")
        logger.info(f"  Processing time: {processing_time:.2f}ms")
        logger.info("=" * 70)
        
        return jsonify({
            'success': True,
            'result': {
                'download_urls': download_urls,
                'session_id': session_id,
                'summary': result['summary'],
                'metrics': result['metrics'],
                'files_created': files_created,
                'open_requests': result.get('open_requests', []),
                'processing_time_ms': processing_time
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500


@app.route('/api/v1/download/<session_id>/<filename>', methods=['GET'])
def download_file(session_id: str, filename: str):
    """Download generated analysis files"""
    try:
        file_path = OUTPUT_FOLDER / session_id / secure_filename(filename)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        logger.info(f"Downloading: {filename} from session {session_id}")
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("CAPITAL OUTLAY ANALYSIS API - Starting")
    logger.info("=" * 70)
    logger.info("Port: 5005")
    logger.info("Endpoints:")
    logger.info("  GET  /health")
    logger.info("  GET  /api/v1/info")
    logger.info("  POST /api/v1/execute")
    logger.info("  GET  /api/v1/download/<session_id>/<filename>")
    logger.info("=" * 70)
    
    app.run(
        host='0.0.0.0',
        port=5005,
        debug=True
    )
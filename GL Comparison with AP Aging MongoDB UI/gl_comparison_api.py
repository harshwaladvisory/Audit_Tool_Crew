"""
GL COMPARISON API - Standardized API Wrapper
Port: 5003
Compares AP Aging with General Ledger data

Endpoints:
- GET  /health                     - Health check
- POST /api/v1/execute             - Execute comparison (2 files required)
- GET  /api/v1/download/<filename> - Download result file
"""

import os
import sys
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import re
from flask import Flask, Blueprint, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

UPLOAD_FOLDER = Path(__file__).parent / 'uploads' / 'gl_comparison'
OUTPUT_FOLDER = Path(__file__).parent / 'outputs' / 'gl_comparison'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# Create directories
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# ============================================================================
# HELPER FUNCTIONS (from original app.py)
# ============================================================================

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_uploaded_file(file_path: str) -> pd.DataFrame:
    """Parse Excel or CSV file"""
    ext = file_path.split('.')[-1].lower()
    
    if ext == 'csv':
        return pd.read_csv(file_path)
    elif ext in ['xlsx', 'xls']:
        return pd.read_excel(file_path, engine='openpyxl')
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def extract_relevant_columns(df: pd.DataFrame, required_columns: list) -> pd.DataFrame:
    """Extract and clean vendor and amount columns"""
    columns = df.columns
    extracted_data = {}
    
    for col in required_columns:
        col_match = [col_name for col_name in columns 
                    if re.match(f'.*{col}.*', col_name, re.IGNORECASE)]
        if col_match:
            extracted_data[col] = df[col_match[0]].values
        else:
            raise ValueError(f"Required column '{col}' not found in the uploaded file.")
    
    result_df = pd.DataFrame(extracted_data)
    
    # Clean amounts
    if 'Amount' in result_df.columns:
        result_df['Amount'] = result_df['Amount'].astype(str).str.strip().str.replace(',', '', regex=False)
        result_df['Amount'] = pd.to_numeric(result_df['Amount'], errors='coerce')
    
    # Group by vendor and sum amounts
    if 'Vendor' in result_df.columns and 'Amount' in result_df.columns:
        result_df = result_df.groupby('Vendor', as_index=False)['Amount'].sum()
    
    return result_df


def compare_ap_gl_data(ap_data: pd.DataFrame, gl_data: pd.DataFrame) -> tuple:
    """Compare AP and GL data, return 3 dataframes"""
    merged_data = pd.merge(ap_data, gl_data, on="Vendor", how="outer", suffixes=('_AP', '_GL'))
    
    # Vendors in both datasets
    found_in_both = merged_data.dropna(subset=['Amount_AP', 'Amount_GL']).copy()
    
    # GL only
    gl_not_in_ap = merged_data[merged_data['Amount_AP'].isna()].copy()
    
    # AP only
    ap_not_in_gl = merged_data[merged_data['Amount_GL'].isna()].copy()
    
    # Calculate difference for matched vendors
    if len(found_in_both) > 0:
        found_in_both['Difference'] = found_in_both['Amount_GL'] - found_in_both['Amount_AP']
    
    return found_in_both, gl_not_in_ap, ap_not_in_gl


# ============================================================================
# FLASK BLUEPRINT
# ============================================================================

gl_comparison_api = Blueprint('gl_comparison_api', __name__)


@gl_comparison_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'tool': 'gl_comparison',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    }), 200


@gl_comparison_api.route('/api/v1/execute', methods=['POST'])
def execute_comparison():
    """
    Execute GL comparison
    
    Required files:
    - ap_file: AP Aging file (Excel/CSV)
    - gl_file: General Ledger file (Excel/CSV)
    
    Returns:
    {
        "success": true,
        "tool_id": "gl_comparison",
        "result": {
            "download_url": "/api/v1/download/GL_comparison_20241103_143022.xlsx",
            "file_id": "abc-123-def",
            "summary": {
                "both_count": 150,
                "gl_only_count": 10,
                "ap_only_count": 5,
                "both_difference": 5000.00,
                "total_difference": 25000.00,
                "processing_time_ms": 1234
            }
        }
    }
    """
    start_time = datetime.now()
    
    try:
        logger.info("=" * 70)
        logger.info("GL COMPARISON: Starting execution")
        logger.info("=" * 70)
        
        # Validate files
        if 'ap_file' not in request.files or 'gl_file' not in request.files:
            logger.error("Missing required files")
            return jsonify({
                'success': False,
                'error': 'Both ap_file and gl_file are required',
                'error_type': 'missing_files'
            }), 400
        
        ap_file = request.files['ap_file']
        gl_file = request.files['gl_file']
        
        if ap_file.filename == '' or gl_file.filename == '':
            logger.error("Empty filenames")
            return jsonify({
                'success': False,
                'error': 'No files selected',
                'error_type': 'empty_files'
            }), 400
        
        if not (allowed_file(ap_file.filename) and allowed_file(gl_file.filename)):
            logger.error("Invalid file formats")
            return jsonify({
                'success': False,
                'error': 'Invalid file format. Please upload CSV or Excel files',
                'error_type': 'invalid_format'
            }), 400
        
        # Save uploaded files
        ap_filename = secure_filename(ap_file.filename or 'ap_file')
        gl_filename = secure_filename(gl_file.filename or 'gl_file')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ap_path = UPLOAD_FOLDER / f"{timestamp}_ap_{ap_filename}"
        gl_path = UPLOAD_FOLDER / f"{timestamp}_gl_{gl_filename}"
        
        ap_file.save(str(ap_path))
        gl_file.save(str(gl_path))
        
        logger.info(f"Files saved:")
        logger.info(f"  AP: {ap_path.name}")
        logger.info(f"  GL: {gl_path.name}")
        
        # Parse files
        logger.info("Parsing files...")
        ap_data = parse_uploaded_file(str(ap_path))
        gl_data = parse_uploaded_file(str(gl_path))
        
        logger.info(f"AP rows: {len(ap_data)}")
        logger.info(f"GL rows: {len(gl_data)}")
        
        # Extract relevant columns
        required_columns = ['Vendor', 'Amount']
        ap_data_extracted = extract_relevant_columns(ap_data, required_columns)
        gl_data_extracted = extract_relevant_columns(gl_data, required_columns)
        
        logger.info(f"AP vendors: {len(ap_data_extracted)}")
        logger.info(f"GL vendors: {len(gl_data_extracted)}")
        
        # Compare data
        logger.info("Comparing data...")
        found_in_both, gl_not_in_ap, ap_not_in_gl = compare_ap_gl_data(
            ap_data_extracted, 
            gl_data_extracted
        )
        
        # Generate output filename with descriptive pattern
        file_id = str(uuid.uuid4())
        output_filename = f"GL_comparison_{timestamp}.xlsx"
        output_path = OUTPUT_FOLDER / output_filename
        
        # Write Excel with 3 sheets
        logger.info(f"Writing output: {output_filename}")
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            found_in_both.to_excel(writer, sheet_name="Vendors in Both", index=False)
            gl_not_in_ap.to_excel(writer, sheet_name="GL Only", index=False)
            ap_not_in_gl.to_excel(writer, sheet_name="AP Only", index=False)
        
        # Calculate summary statistics
        both_difference = found_in_both['Difference'].sum() if len(found_in_both) > 0 else 0
        
        gl_only_nonzero = gl_not_in_ap[
            (gl_not_in_ap['Amount_GL'].notna()) & 
            (gl_not_in_ap['Amount_GL'] != 0)
        ] if len(gl_not_in_ap) > 0 else gl_not_in_ap
        gl_only_total = gl_only_nonzero['Amount_GL'].sum() if len(gl_only_nonzero) > 0 else 0
        
        ap_only_nonzero = ap_not_in_gl[
            (ap_not_in_gl['Amount_AP'].notna()) & 
            (ap_not_in_gl['Amount_AP'] != 0)
        ] if len(ap_not_in_gl) > 0 else ap_not_in_gl
        ap_only_total = ap_only_nonzero['Amount_AP'].sum() if len(ap_only_nonzero) > 0 else 0
        
        total_difference = both_difference + gl_only_total - ap_only_total
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        summary = {
            'both_count': len(found_in_both),
            'gl_only_count': len(gl_not_in_ap),
            'ap_only_count': len(ap_not_in_gl),
            'both_difference': float(both_difference),
            'gl_only_total': float(gl_only_total),
            'ap_only_total': float(ap_only_total),
            'total_difference': float(total_difference),
            'processing_time_ms': round(processing_time, 2),
            'ap_filename': ap_filename,
            'gl_filename': gl_filename,
            'output_filename': output_filename
        }
        
        logger.info("=" * 70)
        logger.info("SUMMARY:")
        logger.info(f"  Vendors in both: {summary['both_count']}")
        logger.info(f"  GL only: {summary['gl_only_count']}")
        logger.info(f"  AP only: {summary['ap_only_count']}")
        logger.info(f"  Total difference: ${summary['total_difference']:,.2f}")
        logger.info(f"  Processing time: {summary['processing_time_ms']:.2f}ms")
        logger.info("=" * 70)
        
        # Clean up uploaded files
        try:
            ap_path.unlink()
            gl_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete temp files: {e}")
        
        # Return standardized response
        return jsonify({
            'success': True,
            'tool_id': 'gl_comparison',
            'tool_name': 'GL Comparison Tool',
            'result': {
                'download_url': f'/api/v1/download/{output_filename}',
                'file_id': file_id,
                'summary': summary
            },
            'status_code': 200
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            'success': False,
            'tool_id': 'gl_comparison',
            'error': str(e),
            'error_type': 'validation_error'
        }), 400
        
    except Exception as e:
        logger.error(f"Execution error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'tool_id': 'gl_comparison',
            'error': str(e),
            'error_type': 'execution_error'
        }), 500


@gl_comparison_api.route('/api/v1/download/<filename>', methods=['GET'])
def download_result(filename: str):
    """
    Download comparison result file
    
    Args:
        filename: Output filename (e.g., GL_comparison_20241103_143022.xlsx)
    
    Returns:
        Excel file with 3 sheets
    """
    try:
        # Security: Only allow specific pattern
        if not filename.startswith('GL_comparison_') or not filename.endswith('.xlsx'):
            logger.error(f"Invalid filename pattern: {filename}")
            return jsonify({
                'error': 'Invalid filename',
                'error_type': 'invalid_filename'
            }), 400
        
        # Security: Prevent path traversal
        if '/' in filename or '\\' in filename or '..' in filename:
            logger.error(f"Path traversal attempt: {filename}")
            return jsonify({
                'error': 'Invalid file path',
                'error_type': 'path_traversal'
            }), 400
        
        file_path = OUTPUT_FOLDER / filename
        
        if not file_path.exists():
            logger.error(f"File not found: {filename}")
            return jsonify({
                'error': 'File not found',
                'error_type': 'file_not_found'
            }), 404
        
        logger.info(f"✅ Sending file: {filename}")
        
        return send_from_directory(
            OUTPUT_FOLDER,
            filename,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'error_type': 'download_error'
        }), 500


# ============================================================================
# STANDALONE FLASK APP (for testing)
# ============================================================================

def create_app():
    """Create Flask app with blueprint"""
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
    
    # Register blueprint
    app.register_blueprint(gl_comparison_api)
    
    return app


if __name__ == '__main__':
    app = create_app()
    
    logger.info("=" * 70)
    logger.info("GL COMPARISON API - Starting")
    logger.info("=" * 70)
    logger.info("Port: 5003")
    logger.info("Endpoints:")
    logger.info("  GET  /health")
    logger.info("  POST /api/v1/execute")
    logger.info("  GET  /api/v1/download/<filename>")
    logger.info("=" * 70)
    
    app.run(
        host='0.0.0.0',
        port=5003,
        debug=True,
        threaded=True
    )
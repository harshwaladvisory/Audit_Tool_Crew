"""
RRF STATUS TRACKER - API WRAPPER (FIXED)
Checks charity registration status for EINs from Excel files
Port: 5014
"""

import os
import sys
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import pandas as pd
from pathlib import Path

# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import scraper with error handling
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from scraper import CharityStatusScraper
    SCRAPER_AVAILABLE = True
    logger.info("✅ CharityStatusScraper loaded successfully")
except Exception as e:
    SCRAPER_AVAILABLE = False
    logger.error(f"❌ Failed to load CharityStatusScraper: {str(e)}")
    CharityStatusScraper = None

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
OUTPUT_FOLDER = Path(__file__).parent / 'outputs'
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}

def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'rrf_status_tracker',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/v1/info', methods=['GET'])
def get_info():
    """Get tool information"""
    return jsonify({
        'tool_id': 'rrf_status_tracker',
        'name': 'RRF Status Tracker',
        'description': 'Check charity registration status for multiple EINs',
        'version': '1.0.0',
        'category': 'compliance',
        'required_params': [
            {
                'name': 'file',
                'type': 'file',
                'description': 'Excel file containing EIN Number column'
            }
        ],
        'optional_params': [],
        'outputs': [
            'RRF_Status_Results_YYYYMMDD_HHMMSS.xlsx'
        ]
    }), 200


@app.route('/api/v1/execute', methods=['POST'])
def execute_tracking():
    """Execute RRF status tracking"""
    try:
        logger.info("=" * 70)
        logger.info("RRF STATUS TRACKER: Starting execution")
        logger.info("=" * 70)

        # Check for uploaded file
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file format. Please upload an .xlsx or .xls file'
            }), 400

        # Save uploaded file
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(file.filename)
        file_path = UPLOAD_FOLDER / f"{session_id}_{filename}"
        file.save(str(file_path))
        logger.info(f"File saved: {file_path.name}")

        # Read Excel file
        try:
            df = pd.read_excel(file_path)
            logger.info(f"Excel loaded: {len(df)} rows, columns: {list(df.columns)}")
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to read Excel file: {str(e)}'
            }), 400

        # Validate required column
        ein_column = None
        for col in df.columns:
            if 'ein' in col.lower() or 'tax id' in col.lower() or 'fein' in col.lower():
                ein_column = col
                break

        if ein_column is None:
            return jsonify({
                'success': False,
                'error': 'Excel file must contain an "EIN Number" or similar column'
            }), 400

        logger.info(f"Using EIN column: {ein_column}")

        # Process EINs
        results = []
        processed_count = 0
        error_count = 0

        # Initialize scraper
        if not SCRAPER_AVAILABLE or CharityStatusScraper is None:
            return jsonify({
                'success': False,
                'error': 'Scraper not available. Please check server logs.',
                'error_type': 'service_unavailable'
            }), 503

        with CharityStatusScraper() as scraper:
            for idx, row in df.iterrows():
                ein = str(row[ein_column]).strip()
                
                # Clean EIN (remove dashes, spaces)
                ein_clean = ''.join(filter(str.isdigit, ein))
                
                if len(ein_clean) != 9:
                    logger.warning(f"Invalid EIN format: {ein}")
                    results.append({
                        'Original_EIN': ein,
                        'Registry_Status': 'Invalid EIN Format',
                        'Processed_At': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    error_count += 1
                    continue

                # Check status
                try:
                    logger.info(f"Checking EIN {idx+1}/{len(df)}: {ein_clean}")
                    status = scraper.get_charity_status(ein_clean)
                    
                    results.append({
                        'Original_EIN': ein,
                        'Cleaned_EIN': ein_clean,
                        'Registry_Status': status,
                        'Processed_At': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    processed_count += 1
                    logger.info(f"Status: {status}")
                    
                except Exception as e:
                    logger.error(f"Error processing EIN {ein_clean}: {str(e)}")
                    results.append({
                        'Original_EIN': ein,
                        'Cleaned_EIN': ein_clean,
                        'Registry_Status': f'Error: {str(e)}',
                        'Processed_At': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    error_count += 1

        # Create output Excel
        results_df = pd.DataFrame(results)
        output_filename = f"RRF_Status_Results_{session_id}.xlsx"
        output_path = OUTPUT_FOLDER / output_filename

        # Write Excel with formatting
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            results_df.to_excel(writer, sheet_name='Status Results', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Status Results']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        logger.info(f"Results saved: {output_filename}")

        # Summary
        summary = {
            'total_eins': len(df),
            'processed_successfully': processed_count,
            'errors': error_count,
            'output_file': output_filename
        }

        download_url = f"/api/v1/download/{session_id}/{output_filename}"

        logger.info("=" * 70)
        logger.info("SUMMARY:")
        logger.info(f"  Total EINs: {summary['total_eins']}")
        logger.info(f"  Processed: {summary['processed_successfully']}")
        logger.info(f"  Errors: {summary['errors']}")
        logger.info(f"  Report: {output_filename}")
        logger.info("=" * 70)

        return jsonify({
            'success': True,
            'tool_id': 'rrf_status_tracker',
            'tool_name': 'RRF Status Tracker',
            'result': {
                'download_url': download_url,
                'file_id': session_id,
                'summary': summary,
                'files_created': [output_filename]
            },
            'status_code': 200
        }), 200

    except Exception as e:
        logger.error(f"Error in RRF status tracking: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'execution_error'
        }), 500


@app.route('/api/v1/download/<session_id>/<filename>', methods=['GET'])
def download_file(session_id, filename):
    """Download generated report"""
    try:
        file_path = OUTPUT_FOLDER / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("RRF STATUS TRACKER API - Starting")
    logger.info("=" * 70)
    logger.info("Port: 5014")
    logger.info("Endpoints:")
    logger.info("  GET  /health")
    logger.info("  GET  /api/v1/info")
    logger.info("  POST /api/v1/execute")
    logger.info("  GET  /api/v1/download/<session_id>/<filename>")
    logger.info("=" * 70)
    
    app.run(
        host='0.0.0.0',
        port=5015,
        debug=False,
        use_reloader=False,
        threaded=True
    )
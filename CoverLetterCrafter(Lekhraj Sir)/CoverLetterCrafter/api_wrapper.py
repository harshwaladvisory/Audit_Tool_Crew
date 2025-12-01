"""
Cover Letter Crafter API - Port 5010
Generates tax return cover letters from Excel data containing Form 990 instructions
"""

import os
import logging
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime
import tempfile
import re

# Import the existing processors
from utils.excel_processor import ExcelProcessor
from utils.document_generator import DocumentGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Configuration
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
SESSION_STORAGE = {}  # Session-based storage (no MongoDB)


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_client_short_name(client_name: str) -> str:
    """Generate client short name from full client name"""
    business_suffixes = [
        'Pvt Ltd', 'Private Limited', 'Ltd', 'Limited',
        'Inc.', 'Inc', 'Corporation', 'Corp.', 'Corp',
        'LLC', 'LLP'
    ]
    clean_name = client_name.strip().replace(',', '')
    for suffix in business_suffixes:
        pattern = rf'\b{re.escape(suffix)}\b'
        clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE).strip()
    words = clean_name.split()
    short_name = ''.join([word[0].upper() for word in words if word])
    return short_name


# ============================================================================
# STANDARD API ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Cover Letter Crafter',
        'port': 5010,
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/v1/info', methods=['GET'])
def get_info():
    """Get tool information"""
    return jsonify({
        'tool_id': 'cover_letter_crafter',
        'name': 'Cover Letter Crafter',
        'description': 'Generate tax return cover letters from Excel data containing Form 990 instructions',
        'category': 'tax',
        'version': '1.0.0',
        'required_params': {
            'file': {
                'type': 'file',
                'description': 'Excel file with cover letter data (.xlsx, .xls)',
                'required': True
            },
            'client_name': {
                'type': 'string',
                'description': 'Client name (e.g., "ABC Nonprofit")',
                'required': True
            },
            'draft_type': {
                'type': 'string',
                'description': 'Draft type',
                'options': ['Preliminary Draft', 'Revised Draft', 'Final Package'],
                'required': True
            },
            'tax_year': {
                'type': 'string',
                'description': 'Tax year (e.g., "2023")',
                'required': True
            },
            'format': {
                'type': 'string',
                'description': 'Output format',
                'options': ['docx', 'pdf'],
                'required': True
            }
        },
        'excel_structure': {
            'columns': [
                'S. No.', 'Form', 'Part', 'Line', 'Topic',
                'Applicability', 'Prefill Status', 'Header',
                'Instruction – Prefilled',
                'Instruction – Data Required',
                'Instruction – Applicability Unknown'
            ],
            'processing_rules': [
                'Only process rows where Applicability == "Applicable"',
                'Select instruction based on Prefill Status',
                'Group by Header and create bullet points if multiple instructions',
                'Handles typo: "Confirm Applicabilty" (missing i)'
            ]
        },
        'examples': [
            'Generate cover letter for ABC Nonprofit',
            'Create tax return cover letter',
            'Generate Form 990 cover letter'
        ]
    }), 200


@app.route('/api/v1/execute', methods=['POST'])
def execute():
    """Execute cover letter generation"""
    try:
        # Get parameters
        client_name = request.form.get('client_name', '').strip()
        draft_type = request.form.get('draft_type', '').strip()
        tax_year = request.form.get('tax_year', '').strip()
        output_format = request.form.get('format', 'docx').strip().lower()

        logger.info(f"📥 Execute request received:")
        logger.info(f"  Client: {client_name}")
        logger.info(f"  Draft: {draft_type}")
        logger.info(f"  Year: {tax_year}")
        logger.info(f"  Format: {output_format}")

        # Validate parameters
        if not client_name:
            return jsonify({
                'success': False,
                'error': 'client_name is required'
            }), 400

        if not draft_type:
            return jsonify({
                'success': False,
                'error': 'draft_type is required'
            }), 400

        if draft_type not in ['Preliminary Draft', 'Revised Draft', 'Final Package']:
            return jsonify({
                'success': False,
                'error': f'Invalid draft_type. Must be one of: Preliminary Draft, Revised Draft, Final Package'
            }), 400

        if not tax_year:
            return jsonify({
                'success': False,
                'error': 'tax_year is required'
            }), 400

        if output_format not in ['docx', 'pdf']:
            return jsonify({
                'success': False,
                'error': 'format must be either "docx" or "pdf"'
            }), 400

        # Check for file
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded. Please upload an Excel file.'
            }), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Please upload an Excel file (.xlsx or .xls)'
            }), 400

        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)

        logger.info(f"📁 File saved: {filepath}")

        # Process Excel file
        processor = ExcelProcessor()
        try:
            cover_letter_data = processor.process_excel(
                filepath=filepath,
                client_name=client_name,
                draft_type=draft_type,
                tax_year=tax_year
            )
            logger.info(f"✅ Excel processed: {cover_letter_data['total_sections']} sections")
        except Exception as e:
            logger.error(f"❌ Excel processing error: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Error processing Excel file: {str(e)}'
            }), 400
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rmdir(temp_dir)

        # Generate document
        generator = DocumentGenerator()
        try:
            if output_format == 'docx':
                temp_file = generator.generate_docx(cover_letter_data, client_name)
                mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            else:  # pdf
                temp_file = generator.generate_pdf(cover_letter_data, client_name)
                mimetype = 'application/pdf'

            logger.info(f"✅ Document generated: {temp_file}")

            # Generate filename
            client_short_name = generate_client_short_name(client_name)
            current_date = datetime.now().strftime('%m.%d.%Y')
            output_filename = f"{client_short_name}_Cover_Letter_{current_date}.{output_format}"

            # Create session ID
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Store file in session storage
            SESSION_STORAGE[session_id] = {
                'filepath': temp_file,
                'filename': output_filename,
                'mimetype': mimetype,
                'timestamp': datetime.now().isoformat(),
                'client_name': client_name,
                'draft_type': draft_type,
                'tax_year': tax_year,
                'format': output_format,
                'total_sections': cover_letter_data['total_sections']
            }

            logger.info(f"📦 Session created: {session_id}")

            # Build download URL
            download_url = f"/api/v1/download/{session_id}/{output_filename}"

            # Return success response
            return jsonify({
                'success': True,
                'tool_id': 'cover_letter_crafter',
                'tool_name': 'Cover Letter Crafter',
                'result': {
                    'download_url': download_url,
                    'summary': {
                        'client_name': client_name,
                        'total_sections': cover_letter_data['total_sections'],
                        'draft_type': draft_type,
                        'tax_year': tax_year,
                        'format': output_format,
                        'filename': output_filename
                    }
                }
            }), 200

        except Exception as e:
            logger.error(f"❌ Document generation error: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Error generating document: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"❌ Execution error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/v1/download/<session_id>/<filename>', methods=['GET'])
def download_file(session_id: str, filename: str):
    """Download generated cover letter"""
    try:
        logger.info(f"📥 Download request: {session_id}/{filename}")

        if session_id not in SESSION_STORAGE:
            logger.error(f"❌ Session not found: {session_id}")
            return jsonify({
                'success': False,
                'error': 'Session not found or expired'
            }), 404

        session_data = SESSION_STORAGE[session_id]
        filepath = session_data['filepath']

        if not os.path.exists(filepath):
            logger.error(f"❌ File not found: {filepath}")
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

        logger.info(f"✅ Sending file: {filename}")

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype=session_data['mimetype']
        )

    except Exception as e:
        logger.error(f"❌ Download error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🚀 COVER LETTER CRAFTER API - Starting")
    logger.info("=" * 70)
    logger.info(f"📍 Port: 5010")
    logger.info(f"🔧 Tool ID: cover_letter_crafter")
    logger.info(f"📦 Category: Tax Tools")
    logger.info("=" * 70)

    app.run(
        host='0.0.0.0',
        port=5010,
        debug=False,
        threaded=True
    )
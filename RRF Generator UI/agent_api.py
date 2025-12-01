"""
Agent API for RRF Generator - UPDATED FOR ORCHESTRATION
File System Storage + Optional MongoDB
Port: 5009
"""

from flask import Blueprint, jsonify, request, send_file, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import logging
from pathlib import Path

# Import inline processors
from pdf_extractor import RRFPDFExtractor
from template_filler import WordTemplateFiller

logger = logging.getLogger(__name__)

# Create Blueprint
rrf_agent_api = Blueprint('rrf_agent', __name__)

# Database manager (optional - will be injected if available)
db_manager = None

# Initialize processors
pdf_extractor = RRFPDFExtractor()
template_filler = WordTemplateFiller()

# File system paths
UPLOAD_FOLDER = Path('./uploads')
OUTPUT_FOLDER = Path('./outputs')
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

# Create folders
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def init_agent_api(database_manager=None):
    """Initialize agent API with optional database manager"""
    global db_manager
    db_manager = database_manager
    if db_manager:
        logger.info("✅ RRF Agent API initialized with MongoDB")
    else:
        logger.info("✅ RRF Agent API initialized (MongoDB optional - disabled)")


def allowed_file(filename, extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions


def format_approval_date(date_str):
    """Format date to 'Month DD, YYYY'"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
    except ValueError:
        return datetime.now().strftime('%B %d, %Y')


# ============================================
# ENDPOINT 1: Health Check
# ============================================
@rrf_agent_api.route('/health', methods=['GET'])
@rrf_agent_api.route('/api/v1/health', methods=['GET'])
def health():
    """Check if RRF Generator Agent API is working"""
    return jsonify({
        "status": "healthy",
        "tool_id": "rrf_generator",
        "tool_name": "RRF Generator",
        "version": "2.1.0",
        "mode": "synchronous",
        "storage": "file_system",
        "mongodb_enabled": db_manager is not None,
        "timestamp": datetime.now().isoformat()
    }), 200


# ============================================
# ENDPOINT 2: Tool Info (For Orchestrator)
# ============================================
@rrf_agent_api.route('/info', methods=['GET'])
@rrf_agent_api.route('/api/v1/info', methods=['GET'])
def get_tool_info():
    """Return metadata about this tool - Used by orchestrator"""
    return jsonify({
        "tool_id": "rrf_generator",
        "name": "RRF Generator",
        "description": "Generate Letter of Instruction from RRF-1 PDF forms by extracting data and populating Word templates",
        "version": "2.1.0",
        "category": "tax",
        "processing_mode": "synchronous",
        "storage_mode": "file_system",
        "required_params": [
            {
                "name": "pdf_file",
                "type": "file",
                "description": "RRF-1 PDF form with data to extract",
                "accepted_formats": ["pdf"]
            },
            {
                "name": "word_file",
                "type": "file", 
                "description": "Word template with placeholders (<<Date>>, <<Client Name>>, etc.)",
                "accepted_formats": ["docx", "doc"]
            }
        ],
        "optional_params": [
            {
                "name": "approval_date",
                "type": "date",
                "description": "Approval date (YYYY-MM-DD format)",
                "default": "current_date"
            }
        ],
        "template_placeholders": [
            "<<Date>>", "<<Signing Person>>", "<<Title>>", 
            "<<Client Name>>", "<<Address>>", "<<First Name>>",
            "<<Fee>>", "<<Fiscal Year>>", "<<Date1>>"
        ],
        "outputs": ["Letter of Instruction (Word document)"],
        "processing_type": "synchronous",
        "estimated_time": "5-7 seconds",
        "keywords": [
            "rrf", "rrf-1", "request for reimbursement",
            "letter of instruction", "loi", "form 990",
            "extract", "populate", "template"
        ]
    }), 200


# ============================================
# ENDPOINT 3: Execute (MAIN - FILE SYSTEM STORAGE)
# ============================================
@rrf_agent_api.route('/execute', methods=['POST'])
@rrf_agent_api.route('/api/v1/execute', methods=['POST'])
def execute():
    """
    Main execution endpoint - FILE SYSTEM STORAGE
    
    Request (multipart/form-data):
    - pdf_file: RRF-1 PDF form (required)
    - word_file: Word template document (required)
    - approval_date: Approval date in YYYY-MM-DD format (optional)
    
    Returns IMMEDIATE result with download URL:
    {
        "success": true,
        "tool_id": "rrf_generator",
        "result": {
            "success": true,
            "download_url": "/api/v1/download/<session_id>/<filename>",
            "summary": {...}
        }
    }
    """
    start_time = datetime.now()
    session_id = None
    session_folder = None
    
    try:
        logger.info("=" * 70)
        logger.info("RRF GENERATOR: Starting execution")
        logger.info("=" * 70)
        
        # Validate files
        if 'pdf_file' not in request.files or 'word_file' not in request.files:
            return jsonify({
                "success": False,
                "tool_id": "rrf_generator",
                "error": "Both pdf_file and word_file are required",
                "error_type": "missing_files"
            }), 400
        
        pdf_file = request.files['pdf_file']
        word_file = request.files['word_file']
        
        # Get approval date (optional, defaults to today)
        approval_date_str = request.form.get('approval_date', datetime.now().strftime('%Y-%m-%d'))
        approval_date = format_approval_date(approval_date_str)
        
        logger.info(f"📄 Received files:")
        logger.info(f"   PDF: {pdf_file.filename}")
        logger.info(f"   Word: {word_file.filename}")
        logger.info(f"📅 Approval date: {approval_date}")
        
        # Validate filenames
        if pdf_file.filename == '' or word_file.filename == '':
            return jsonify({
                "success": False,
                "tool_id": "rrf_generator",
                "error": "Empty filenames not allowed",
                "error_type": "invalid_filename"
            }), 400
        
        # Validate file extensions
        if not allowed_file(pdf_file.filename, ['pdf']):
            return jsonify({
                "success": False,
                "tool_id": "rrf_generator",
                "error": "PDF file must have .pdf extension",
                "error_type": "invalid_file_type"
            }), 400
        
        if not allowed_file(word_file.filename, ['docx', 'doc']):
            return jsonify({
                "success": False,
                "tool_id": "rrf_generator",
                "error": "Word file must have .docx or .doc extension",
                "error_type": "invalid_file_type"
            }), 400
        
        # Generate unique session ID
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_folder = UPLOAD_FOLDER / session_id
        session_folder.mkdir(exist_ok=True)
        
        logger.info(f"📁 Session folder: {session_folder}")
        
        # Save files with secure names
        pdf_filename = secure_filename(pdf_file.filename)
        word_filename = secure_filename(word_file.filename)
        
        pdf_path = session_folder / pdf_filename
        word_path = session_folder / word_filename
        
        pdf_file.save(str(pdf_path))
        word_file.save(str(word_path))
        
        logger.info(f"✅ Files saved")
        
        # ============================================
        # STEP 1: Extract data from PDF (INLINE)
        # ============================================
        logger.info("🔍 Step 1: Extracting data from PDF...")
        extracted_data = pdf_extractor.extract(str(pdf_path))
        
        if not extracted_data:
            raise ValueError("No data extracted from PDF")
        
        logger.info(f"✅ Extracted {len(extracted_data)} fields")
        
        # ============================================
        # STEP 2: Process extracted data
        # ============================================
        logger.info("🔧 Step 2: Processing extracted data...")
        
        printed_name = extracted_data.get('Signing Person', '').strip()
        if not printed_name:
            raise ValueError("Missing 'Signing Person' in PDF")
        
        first_name = printed_name.split()[0] if printed_name else ''
        title = extracted_data.get('Title', '').strip()
        org_name = extracted_data.get('Client name', '').strip()
        
        addr1 = extracted_data.get('Address Line 1', '').strip()
        addr2 = extracted_data.get('Address Line 2', '').strip()
        address = addr1 + ("\n" + addr2 if addr2 else "")
        
        fiscal_year = extracted_data.get('Fiscal Year', '').strip()
        total_revenue = extracted_data.get('Total Revenue', '0')
        
        # Calculate fee
        fee = pdf_extractor.calculate_fee(total_revenue)
        
        # Prepare data for template
        template_data = {
            'printed_name': printed_name,
            'first_name': first_name,
            'title': title,
            'org_name': org_name,
            'address': address,
            'fiscal_year': fiscal_year,
            'fee': fee,
            'approval_date': approval_date
        }
        
        logger.info(f"✅ Data prepared:")
        logger.info(f"   Client: {org_name}")
        logger.info(f"   Signer: {printed_name}")
        logger.info(f"   Fee: ${fee:.2f}")
        
        # ============================================
        # STEP 3: Fill Word template
        # ============================================
        logger.info("📝 Step 3: Filling Word template...")
        
        # Generate output filename
        pdf_prefix = pdf_filename.split('_')[0] if '_' in pdf_filename else pdf_filename.replace('.pdf', '')
        output_filename = f"{pdf_prefix}_Letter of Instruction- Form 990 & RRF-1.docx"
        
        # Create output session folder
        output_session = OUTPUT_FOLDER / session_id
        output_session.mkdir(exist_ok=True)
        
        output_path = output_session / output_filename
        
        # Fill template
        template_filler.fill_template(str(word_path), template_data, str(output_path))
        
        logger.info(f"✅ Document saved: {output_filename}")
        
        # ============================================
        # STEP 4: Save to MongoDB (OPTIONAL)
        # ============================================
        if db_manager:
            try:
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
                with open(word_path, 'rb') as f:
                    word_content = f.read()
                with open(output_path, 'rb') as f:
                    output_content = f.read()
                
                import base64
                record = {
                    'job_id': session_id,
                    'run_timestamp': datetime.now(),
                    'status': 'SUCCESS',
                    'input_pdf_name': pdf_filename,
                    'input_pdf_path': str(pdf_path),
                    'input_pdf_content': base64.b64encode(pdf_content).decode('utf-8'),
                    'input_word_name': word_filename,
                    'input_word_path': str(word_path),
                    'input_word_content': base64.b64encode(word_content).decode('utf-8'),
                    'output_word_name': output_filename,
                    'output_word_path': str(output_path),
                    'output_word_content': base64.b64encode(output_content).decode('utf-8'),
                    'approval_date': approval_date,
                    'log_message': 'Processing completed successfully',
                    'extracted_data': extracted_data
                }
                
                db_manager.db.processing_records.insert_one(record)
                logger.info(f"✅ Record saved to MongoDB")
            except Exception as db_error:
                logger.warning(f"⚠️ MongoDB save failed (non-blocking): {db_error}")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info("=" * 70)
        logger.info("SUMMARY:")
        logger.info(f"  Client: {org_name}")
        logger.info(f"  Signer: {printed_name}")
        logger.info(f"  Fiscal Year: {fiscal_year}")
        logger.info(f"  Fee: ${fee:.2f}")
        logger.info(f"  Output: {output_filename}")
        logger.info(f"  Processing time: {processing_time:.2f}ms")
        logger.info("=" * 70)
        
        # ============================================
        # STEP 5: Return immediate result
        # ============================================
        return jsonify({
            "success": True,
            "tool_id": "rrf_generator",
            "tool_name": "RRF Generator",
            "result": {
                "success": True,
                "download_url": f"/api/v1/download/{session_id}/{output_filename}",
                "session_id": session_id,
                "summary": {
                    "original_pdf": pdf_filename,
                    "original_template": word_filename,
                    "output_filename": output_filename,
                    "extracted_fields": len(extracted_data),
                    "client_name": org_name,
                    "signing_person": printed_name,
                    "fiscal_year": fiscal_year,
                    "calculated_fee": f"${fee:.2f}",
                    "approval_date": approval_date,
                    "processing_time_ms": int(processing_time)
                }
            },
            "status_code": 200
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Processing error: {str(e)}", exc_info=True)
        
        # Save error to MongoDB (optional)
        if db_manager and session_id:
            try:
                record = {
                    'job_id': session_id,
                    'run_timestamp': datetime.now(),
                    'status': 'FAILURE',
                    'input_pdf_name': pdf_file.filename if 'pdf_file' in locals() else None,
                    'input_word_name': word_file.filename if 'word_file' in locals() else None,
                    'log_message': f"Error: {str(e)}",
                    'extracted_data': {}
                }
                db_manager.db.processing_records.insert_one(record)
            except:
                pass
        
        return jsonify({
            "success": False,
            "tool_id": "rrf_generator",
            "error": str(e),
            "error_type": "execution_error"
        }), 500
    
    finally:
        # Cleanup temp upload folder (keep outputs)
        try:
            if session_folder and session_folder.exists():
                import shutil
                shutil.rmtree(session_folder)
                logger.info(f"🗑️ Cleaned up temp upload folder: {session_folder}")
        except Exception as cleanup_error:
            logger.warning(f"Cleanup warning: {cleanup_error}")


# ============================================
# ENDPOINT 4: Download Processed File
# ============================================
@rrf_agent_api.route('/download/<session_id>/<filename>', methods=['GET'])
@rrf_agent_api.route('/api/v1/download/<session_id>/<filename>', methods=['GET'])
def download_file(session_id, filename):
    """Download the processed Word document from file system"""
    try:
        # Get file from outputs folder
        file_path = OUTPUT_FOLDER / session_id / secure_filename(filename)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return jsonify({
                "success": False,
                "error": "File not found"
            }), 404
        
        logger.info(f"📥 Downloading: {filename} from session {session_id}")
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        logger.error(f"❌ Error downloading file: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
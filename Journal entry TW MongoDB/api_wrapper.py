"""
JOURNAL ENTRY TESTWORK API - Audit Tool for JE Testing
Analyzes journal entries with risk-based sampling and generates audit workpapers
Port: 5012
"""

import os
import sys
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
from pathlib import Path
import pandas as pd

# Import core modules
from je_processor import JEProcessor
from risk_analyzer import RiskAnalyzer
from sample_selector import SampleSelector
from artifact_generator import ArtifactGenerator
from gemini_integration import GeminiIntegration

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
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
OUTPUT_FOLDER = Path(__file__).parent / 'outputs'
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.pdf'}

# Default configuration (from config.py)
DEFAULT_CONFIG = {
    'INVESTIGATE_THRESHOLD': 1000,
    'COVERAGE_TARGET': 0.8,
    'MATERIALITY': 10000,
    'PERIOD_END_WINDOW': 7,
    'HIGH_RISK_KEYWORDS': ['adjusting', 'reversal', 'year-end', 'correction', 'JE', 'manual']
}

# Initialize processors (MongoDB optional - will be None if not available)
je_processor = JEProcessor()
risk_analyzer = RiskAnalyzer()
sample_selector = SampleSelector()
artifact_generator = ArtifactGenerator()
gemini_integration = GeminiIntegration()

def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'je_testwork',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/v1/info', methods=['GET'])
def get_info():
    """Get tool information"""
    return jsonify({
        'tool_id': 'je_testwork',
        'name': 'Journal Entry Testwork Agent',
        'description': 'AI-powered audit tool for journal entry risk analysis and sample selection',
        'version': '1.0.0',
        'category': 'audit',
        'required_params': [
            {
                'name': 'gl_file',
                'type': 'file',
                'description': 'General Ledger file (CSV, Excel, or PDF)'
            }
        ],
        'optional_params': [
            {
                'name': 'investigate_threshold',
                'type': 'number',
                'description': 'Amount threshold for investigation (default: 1000)',
                'default': 1000
            },
            {
                'name': 'materiality',
                'type': 'number',
                'description': 'Materiality threshold (default: 10000)',
                'default': 10000
            },
            {
                'name': 'coverage_target',
                'type': 'number',
                'description': 'Target coverage percentage (default: 0.8)',
                'default': 0.8
            },
            {
                'name': 'period_end_window',
                'type': 'number',
                'description': 'Days before/after period end to flag (default: 7)',
                'default': 7
            },
            {
                'name': 'high_risk_keywords',
                'type': 'string',
                'description': 'Comma-separated high-risk keywords (default: adjusting,reversal,year-end,correction,JE,manual)',
                'default': 'adjusting,reversal,year-end,correction,JE,manual'
            },
            {
                'name': 'client_name',
                'type': 'string',
                'description': 'Client name for audit',
                'default': 'Client'
            },
            {
                'name': 'framework',
                'type': 'string',
                'description': 'Accounting framework (GAAP/IFRS)',
                'default': 'GAAP'
            },
            {
                'name': 'period_start',
                'type': 'string',
                'description': 'Period start date (YYYY-MM-DD) - auto-detected if not provided',
                'default': 'auto'
            },
            {
                'name': 'period_end',
                'type': 'string',
                'description': 'Period end date (YYYY-MM-DD) - auto-detected if not provided',
                'default': 'auto'
            }
        ],
        'outputs': [
            'JE_Population.xlsx - Complete population analysis',
            'JE_Sample_Selection.xlsx - Selected samples',
            'JE_Request_List.xlsx - PBC request list',
            'JE_Test_Workpaper.xlsx - Testing template',
            'JE_Exceptions_Log.xlsx - Exception tracking',
            'Proposed_AJEs.xlsx - Adjusting entries template',
            'JE_Summary_Memo.md - AI-generated summary (optional)'
        ]
    }), 200


@app.route('/api/v1/execute', methods=['POST'])
def execute_testwork():
    """Main endpoint for JE testwork execution"""
    try:
        logger.info("=" * 70)
        logger.info("JE TESTWORK: Starting execution")
        logger.info("=" * 70)
        
        # ================================================================
        # STEP 0: Get parameters
        # ================================================================
        client_name = request.form.get('client_name', 'Client')
        investigate_threshold = float(request.form.get('investigate_threshold', 1000))
        materiality = float(request.form.get('materiality', 10000))
        coverage_target = float(request.form.get('coverage_target', 0.8))
        period_end_window = int(request.form.get('period_end_window', 7))
        framework = request.form.get('framework', 'GAAP')
        
        # Get high-risk keywords
        high_risk_keywords_str = request.form.get('high_risk_keywords', '')
        if high_risk_keywords_str:
            high_risk_keywords = [k.strip() for k in high_risk_keywords_str.split(',')]
        else:
            high_risk_keywords = ['adjusting', 'reversal', 'year-end', 'correction', 'JE', 'manual']
        
        logger.info(f"Client: {client_name}")
        logger.info(f"Investigation Threshold: ${investigate_threshold:,.2f}")
        logger.info(f"Materiality: ${materiality:,.2f}")
        logger.info(f"Coverage Target: {coverage_target * 100}%")
        logger.info(f"High-Risk Keywords: {high_risk_keywords}")
        
        # ============================================================
        # ⭐ FIX: Extract or initialize period_start and period_end
        # ============================================================
        # Get period dates from request (optional)
        period_start_str = request.form.get('period_start', '')
        period_end_str = request.form.get('period_end', '')

        # Initialize as None (will be calculated from data if not provided)
        period_start = None
        period_end = None

        # If provided, parse them
        if period_start_str:
            try:
                period_start = pd.to_datetime(period_start_str).strftime('%Y-%m-%d')
                logger.info(f"📅 Period start (provided): {period_start}")
            except Exception as e:
                logger.warning(f"⚠️ Invalid period_start format: {period_start_str} - {e}")
                period_start = None

        if period_end_str:
            try:
                period_end = pd.to_datetime(period_end_str).strftime('%Y-%m-%d')
                logger.info(f"📅 Period end (provided): {period_end}")
            except Exception as e:
                logger.warning(f"⚠️ Invalid period_end format: {period_end_str} - {e}")
                period_end = None
        # ============================================================
        
        # Create session-specific directories
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        upload_dir = UPLOAD_FOLDER / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # ⭐ CRITICAL FIX: Create output directory
        output_dir = OUTPUT_FOLDER / session_id
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Created output directory: {output_dir}")
        
        # Handle file upload
        if 'gl_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No GL file provided',
                'error_type': 'missing_file'
            }), 400

        gl_file = request.files['gl_file']

        if not gl_file or gl_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(gl_file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Supported: Excel (.xlsx, .xls), CSV, PDF'
            }), 400

        # Save file
        filename = secure_filename(gl_file.filename)
        filepath = upload_dir / filename
        gl_file.save(str(filepath))
        logger.info(f"File saved: {filename}")

        # ================================================================
        # STEP 1: Ingest and validate GL data
        # ================================================================
        logger.info("STEP 1: Ingesting GL data...")
        gl_data = je_processor.ingest_gl_files([str(filepath)])
        
        if gl_data.empty:
            return jsonify({
                'success': False,
                'error': 'No valid journal entry data found. Please check file format and content.'
            }), 400

        logger.info(f"✓ Loaded {len(gl_data)} journal entries")

        # ================================================================
        # STEP 2: Build population with risk flags
        # ================================================================
        logger.info("STEP 2: Analyzing risk factors...")
        population = risk_analyzer.build_population(
            gl_data,
            high_risk_keywords=high_risk_keywords,
            period_end_window=period_end_window,
            investigate_threshold=investigate_threshold
        )

        logger.info(f"✓ Risk analysis complete")
        logger.info(f"  Risk breakdown: {population['risk_category'].value_counts().to_dict()}")
        
        # ============================================================
        # ⭐ FIX: Calculate period dates from data if not provided
        # ============================================================
        # If period dates still not set, calculate from population
        if period_start is None and 'date' in population.columns:
            try:
                period_start = population['date'].min().strftime('%Y-%m-%d')
                logger.info(f"📅 Auto-detected period start from data: {period_start}")
            except Exception as e:
                logger.warning(f"⚠️ Could not auto-detect period_start from data: {e}")
        
        if period_end is None and 'date' in population.columns:
            try:
                period_end = population['date'].max().strftime('%Y-%m-%d')
                logger.info(f"📅 Auto-detected period end from data: {period_end}")
            except Exception as e:
                logger.warning(f"⚠️ Could not auto-detect period_end from data: {e}")
        
        # Fallback to current date if still None
        if period_start is None:
            period_start = datetime.now().strftime('%Y-%m-%d')
            logger.warning(f"⚠️ Using current date as period_start fallback: {period_start}")
        
        if period_end is None:
            period_end = datetime.now().strftime('%Y-%m-%d')
            logger.warning(f"⚠️ Using current date as period_end fallback: {period_end}")
        
        logger.info(f"📆 Final period: {period_start} to {period_end}")
        # ============================================================

        # ================================================================
        # STEP 3: Select samples
        # ================================================================
        logger.info("STEP 3: Selecting samples...")
        samples = sample_selector.select_samples(
            population,
            coverage_target=coverage_target,
            materiality=materiality
        )

        if samples.empty:
            logger.warning("No samples selected")
        else:
            logger.info(f"✓ Selected {len(samples)} samples")

        # ================================================================
        # STEP 4: Generate artifacts
        # ================================================================
        logger.info("STEP 4: Generating audit workpapers...")
        
        output_files = artifact_generator.generate_all_artifacts(
            population=population,
            samples=samples,
            parameters={
                'client_name': client_name,
                'investigate_threshold': investigate_threshold,
                'coverage_target': coverage_target,
                'materiality': materiality,
                'period_start': period_start,  # ✅ Now defined
                'period_end': period_end,      # ✅ Now defined
                'framework': framework
            },
            output_dir=str(output_dir)  # Use the created output directory
        )

        logger.info(f"✓ Generated {len(output_files)} workpapers")

        # ================================================================
        # STEP 5: Generate summary memo (optional - uses Gemini if available)
        # ================================================================
        logger.info("STEP 5: Generating summary memo...")
        memo_content = gemini_integration.generate_summary_memo(
            population=population,
            samples=samples,
            output_files=output_files
        )

        if memo_content:
            memo_path = output_dir / 'JE_Summary_Memo.md'
            with open(memo_path, 'w', encoding='utf-8') as f:
                f.write(memo_content)
            output_files.append('JE_Summary_Memo.md')
            logger.info("✓ Summary memo generated")

        # ================================================================
        # STEP 6: Calculate metrics
        # ================================================================
        high_risk_count = len(samples[samples['risk_category'].isin(['Critical', 'High Risk'])]) if not samples.empty else 0
        test_results = artifact_generator.get_test_results()

        metrics = {
            "population_count": len(population),
            "sample_count": len(samples),
            "high_risk_selected": high_risk_count,
            "coverage_achieved": round(len(samples) / len(population) * 100, 1) if len(population) > 0 else 0,
            "risk_breakdown": population['risk_category'].value_counts().to_dict(),
            "tests_passed": test_results.get('passed', 0),
            "exceptions": test_results.get('exceptions', 0),
            "period_start": period_start,
            "period_end": period_end
        }

        # ================================================================
        # STEP 7: Prepare download URLs
        # ================================================================
        download_urls = []
        for filename in output_files:
            download_urls.append({
                'url': f'/api/v1/download/{session_id}/{filename}',
                'filename': filename
            })

        logger.info("=" * 70)
        logger.info("EXECUTION COMPLETE")
        logger.info(f"  Population: {metrics['population_count']}")
        logger.info(f"  Samples: {metrics['sample_count']}")
        logger.info(f"  Coverage: {metrics['coverage_achieved']}%")
        logger.info(f"  Period: {period_start} to {period_end}")
        logger.info(f"  Files: {len(output_files)}")
        logger.info("=" * 70)

        return jsonify({
            'success': True,
            'tool_id': 'je_testwork',
            'tool_name': 'Journal Entry Testwork Agent',
            'result': {
                'summary': f"Analyzed {metrics['population_count']} journal entries and selected {metrics['sample_count']} samples for testing. Generated {len(output_files)} audit workpapers.",
                'metrics': metrics,
                'download_urls': download_urls
            },
            'status_code': 200
        }), 200

    except Exception as e:
        logger.error(f"Execution error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'execution_error'
        }), 500


@app.route('/api/v1/download/<session_id>/<filename>', methods=['GET'])
def download_file(session_id, filename):
    """Download generated workpaper"""
    try:
        file_path = OUTPUT_FOLDER / session_id / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Determine MIME type
        if filename.endswith('.xlsx'):
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.endswith('.md'):
            mimetype = 'text/markdown'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
    
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("JOURNAL ENTRY TESTWORK API - Starting")
    logger.info("=" * 70)
    logger.info("Port: 5012")
    logger.info("Endpoints:")
    logger.info("  GET  /health")
    logger.info("  GET  /api/v1/info")
    logger.info("  POST /api/v1/execute")
    logger.info("  GET  /api/v1/download/<session_id>/<filename>")
    logger.info("=" * 70)
    logger.info("MongoDB: Optional (graceful degradation)")
    logger.info("Gemini AI: Optional (uses basic memo if unavailable)")
    logger.info("=" * 70)
    
    app.run(host='0.0.0.0', port=5012, debug=True)
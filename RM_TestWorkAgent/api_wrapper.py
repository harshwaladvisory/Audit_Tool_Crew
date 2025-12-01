"""
R&M TESTWORK API - Repair & Maintenance Audit Testing
Analyzes R&M expenses to identify potential capitalization errors
Port: 5011
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
import xlsxwriter

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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
OUTPUT_FOLDER = Path(__file__).parent / 'outputs'
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}

# Default configuration
DEFAULT_CONFIG = {
    'CAPITALIZATION_THRESHOLD': 5000,
    'MATERIALITY': 25000,
    'ALLOWED_ACCOUNTS': ['Repair', 'Maintenance', 'R&M', 'Repairs'],
    'STRATIFICATION_BANDS': [
        (0, 1000),
        (1000, 2500),
        (2500, 5000),
        (5000, 10000),
        (10000, float('inf'))
    ],
    'SAMPLE_SIZES': {
        (0, 1000): 3,
        (1000, 2500): 3,
        (2500, 5000): 4,
        (5000, 10000): 5,
        (10000, float('inf')): 5
    },
    'ATTRIBUTE_CHECKS': {
        1: 'Amount matches supporting documentation',
        2: 'Proper authorization obtained',
        3: 'Documents properly marked (cancelled)',
        4: 'Expense relates to current fiscal year',
        5: 'Evidence of pre-approval exists',
        6: 'Segregation of duties maintained',
        7: 'Proper expense/capital classification'
    }
}


def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'rm_testwork',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/v1/info', methods=['GET'])
def get_info():
    """Get tool information"""
    return jsonify({
        'tool_id': 'rm_testwork',
        'name': 'R&M Testwork Agent',
        'description': 'Audit tool for Repair & Maintenance expense testing to identify potential capitalization errors',
        'version': '1.0.0',
        'category': 'audit',
        'required_params': [
            {
                'name': 'gl_file',
                'type': 'file',
                'description': 'General Ledger Excel file with R&M transactions'
            }
        ],
        'optional_params': [
            {
                'name': 'capitalization_threshold',
                'type': 'number',
                'description': 'Threshold for auto-inclusion (default: 5000)',
                'default': 5000
            },
            {
                'name': 'materiality',
                'type': 'number',
                'description': 'Materiality threshold (default: 25000)',
                'default': 25000
            },
            {
                'name': 'client_name',
                'type': 'string',
                'description': 'Client name for the audit',
                'default': 'Client'
            }
        ],
        'outputs': [
            'RM_Testwork_Report_YYYYMMDD_HHMMSS.xlsx'
        ]
    }), 200


@app.route('/api/v1/execute', methods=['POST'])
def execute_testwork():
    """Execute R&M testwork analysis"""
    try:
        logger.info("=" * 70)
        logger.info("R&M TESTWORK: Starting execution")
        logger.info("=" * 70)

        # Get parameters
        client_name = request.form.get('client_name', 'Client')
        cap_threshold = float(request.form.get('capitalization_threshold', DEFAULT_CONFIG['CAPITALIZATION_THRESHOLD']))
        materiality = float(request.form.get('materiality', DEFAULT_CONFIG['MATERIALITY']))

        logger.info(f"Client: {client_name}")
        logger.info(f"Cap Threshold: ${cap_threshold:,.2f}")
        logger.info(f"Materiality: ${materiality:,.2f}")

        # Check for uploaded file
        if 'gl_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'GL file is required'
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
                'error': 'Invalid file type. Only Excel files (.xlsx, .xls) are supported.'
            }), 400

        # Create session
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_folder = UPLOAD_FOLDER / session_id
        session_folder.mkdir(exist_ok=True)

        # Save file
        filename = secure_filename(gl_file.filename)
        filepath = session_folder / filename
        gl_file.save(str(filepath))
        logger.info(f"File saved: {filename}")

        # Process GL file
        logger.info("Reading GL file...")
        try:
            df = pd.read_excel(str(filepath), engine='openpyxl')
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to read Excel file: {str(e)}'
            }), 400

        logger.info(f"Original columns: {list(df.columns)}")

        # ================================================================
        # FLEXIBLE COLUMN MAPPING
        # ================================================================
        column_mapping = {
            'Account Code': ['Account Code', 'Account', 'Acct Code', 'GL Account'],
            'Account Name': ['Account Name', 'Name', 'Account Description', 'GL Name'],
            'Description': ['Description', 'Memo/Description', 'Memo', 'Transaction Description'],
            'Amount': ['Amount', 'Debit', 'Credit', 'Transaction Amount'],
            'Date': ['Date', 'Transaction Date', 'Trans Date', 'Post Date'],
            'Reference': ['Reference', 'Ref', 'Num', 'Doc Number', 'Invoice'],
            'Vendor Name': ['Vendor Name', 'Vendor', 'Payee', 'Name']
        }

        # Map columns flexibly
        mapped_columns = {}
        for standard_name, possible_names in column_mapping.items():
            for possible_name in possible_names:
                if possible_name in df.columns:
                    mapped_columns[standard_name] = possible_name
                    break
        
        logger.info(f"Column mapping: {mapped_columns}")

        # Validate required columns
        required_columns = ['Account Code', 'Account Name', 'Description', 'Amount']
        missing_columns = [col for col in required_columns if col not in mapped_columns]

        if missing_columns:
            return jsonify({
                'success': False,
                'error': f'Missing required columns: {", ".join(missing_columns)}',
                'found_columns': list(df.columns),
                'suggestion': 'Expected columns: Account Code, Account Name (or Name), Description, Amount'
            }), 400

        # Rename columns to standard names
        rename_dict = {v: k for k, v in mapped_columns.items()}
        df.rename(columns=rename_dict, inplace=True)
        
        logger.info(f"Columns after mapping: {list(df.columns)}")

        # Clean data
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        
        # Ensure optional columns exist
        for col in ['Date', 'Reference', 'Vendor Name']:
            if col not in df.columns:
                df[col] = ''

        logger.info(f"Total GL records: {len(df)}")

        # Filter R&M transactions
        logger.info("Filtering R&M transactions...")
        rm_items = []
        
        for idx, row in df.iterrows():
            account_name = str(row.get('Account Name', '')).lower()
            description = str(row.get('Description', '')).lower()
            
            # Check if any allowed account term appears
            is_rm = any(
                term.lower() in account_name or term.lower() in description
                for term in DEFAULT_CONFIG['ALLOWED_ACCOUNTS']
            )
            
            if is_rm:
                rm_items.append({
                    'row_number': idx + 2,
                    'account_code': str(row.get('Account Code', '')).strip(),
                    'account_name': str(row.get('Account Name', '')).strip(),
                    'description': str(row.get('Description', '')).strip(),
                    'amount': float(row.get('Amount', 0)),
                    'date': str(row.get('Date', '')).strip(),
                    'reference': str(row.get('Reference', '')).strip(),
                    'vendor_name': str(row.get('Vendor Name', '')).strip()
                })

        if not rm_items:
            return jsonify({
                'success': False,
                'error': 'No R&M transactions found in GL file. Check if account names contain: Repair, Maintenance, R&M'
            }), 400

        logger.info(f"Found {len(rm_items)} R&M transactions")

        # Stratified sampling
        logger.info("Generating stratified samples...")
        
        # Auto-include items above threshold
        auto_included = [item for item in rm_items if abs(item['amount']) >= cap_threshold]
        remaining = [item for item in rm_items if abs(item['amount']) < cap_threshold]

        logger.info(f"Auto-included (>= ${cap_threshold:,.2f}): {len(auto_included)}")

        # Stratify remaining items
        samples = []
        
        # Add auto-included samples
        for item in auto_included:
            samples.append({
                **item,
                'sample_type': 'Auto-Included',
                'stratum': f'Above Threshold (${cap_threshold:,.0f})',
                'selection_reason': f'Amount ${item["amount"]:,.2f} exceeds capitalization threshold',
                'risk_level': 'High' if abs(item['amount']) >= materiality else 'Medium'
            })

        # Stratify remaining by bands
        for band_min, band_max in DEFAULT_CONFIG['STRATIFICATION_BANDS']:
            band_items = [
                item for item in remaining
                if band_min <= abs(item['amount']) < band_max
            ]
            
            if not band_items:
                continue
            
            sample_size = DEFAULT_CONFIG['SAMPLE_SIZES'].get((band_min, band_max), 3)
            sample_size = min(sample_size, len(band_items))
            
            # Sort by amount descending and take top N
            band_items.sort(key=lambda x: abs(x['amount']), reverse=True)
            selected = band_items[:sample_size]
            
            stratum_label = f'${band_min:,.0f} - ${band_max:,.0f}' if band_max != float('inf') else f'Above ${band_min:,.0f}'
            
            for item in selected:
                samples.append({
                    **item,
                    'sample_type': 'Stratified',
                    'stratum': stratum_label,
                    'selection_reason': f'Stratified sampling (top {sample_size} of {len(band_items)} items)',
                    'risk_level': 'Medium' if abs(item['amount']) >= 2500 else 'Low'
                })

        logger.info(f"Total samples selected: {len(samples)}")

        # Calculate metrics
        total_rm_amount = sum(item['amount'] for item in rm_items)
        sampled_amount = sum(sample['amount'] for sample in samples)
        coverage_pct = (sampled_amount / total_rm_amount * 100) if total_rm_amount else 0

        # Generate Excel report
        logger.info("Generating Excel report...")
        
        output_filename = f"RM_Testwork_{session_id}.xlsx"
        output_path = OUTPUT_FOLDER / output_filename

        workbook = xlsxwriter.Workbook(str(output_path))
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#413178',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        currency_format = workbook.add_format({'num_format': '#,##0.00'})
        high_risk_format = workbook.add_format({'bg_color': '#FFB6C1'})
        medium_risk_format = workbook.add_format({'bg_color': '#FFFFE0'})
        low_risk_format = workbook.add_format({'bg_color': '#90EE90'})
        
        # Sheet 1: Summary
        ws_summary = workbook.add_worksheet('Executive Summary')
        
        ws_summary.write('A1', 'R&M Testwork Executive Summary', workbook.add_format({'bold': True, 'font_size': 16}))
        
        row = 3
        ws_summary.write(f'A{row}', 'Client:', workbook.add_format({'bold': True}))
        ws_summary.write(f'B{row}', client_name)
        row += 1
        
        ws_summary.write(f'A{row}', 'Generated:', workbook.add_format({'bold': True}))
        ws_summary.write(f'B{row}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        row += 2
        
        ws_summary.write(f'A{row}', 'Configuration:', workbook.add_format({'bold': True, 'underline': True}))
        row += 1
        ws_summary.write(f'A{row}', 'Capitalization Threshold:')
        ws_summary.write(f'B{row}', f'${cap_threshold:,.2f}')
        row += 1
        ws_summary.write(f'A{row}', 'Materiality:')
        ws_summary.write(f'B{row}', f'${materiality:,.2f}')
        row += 2
        
        ws_summary.write(f'A{row}', 'Population Metrics:', workbook.add_format({'bold': True, 'underline': True}))
        row += 1
        ws_summary.write(f'A{row}', 'Total GL Records:')
        ws_summary.write(f'B{row}', len(df))
        row += 1
        ws_summary.write(f'A{row}', 'R&M Transactions:')
        ws_summary.write(f'B{row}', len(rm_items))
        row += 1
        ws_summary.write(f'A{row}', 'Total R&M Amount:')
        ws_summary.write(f'B{row}', total_rm_amount, currency_format)
        row += 2
        
        ws_summary.write(f'A{row}', 'Sampling Results:', workbook.add_format({'bold': True, 'underline': True}))
        row += 1
        ws_summary.write(f'A{row}', 'Total Samples:')
        ws_summary.write(f'B{row}', len(samples))
        row += 1
        ws_summary.write(f'A{row}', 'Auto-Included:')
        ws_summary.write(f'B{row}', len(auto_included))
        row += 1
        ws_summary.write(f'A{row}', 'Stratified Samples:')
        ws_summary.write(f'B{row}', len(samples) - len(auto_included))
        row += 1
        ws_summary.write(f'A{row}', 'Sampled Amount:')
        ws_summary.write(f'B{row}', sampled_amount, currency_format)
        row += 1
        ws_summary.write(f'A{row}', 'Coverage %:')
        ws_summary.write(f'B{row}', f'{coverage_pct:.1f}%')
        
        ws_summary.set_column('A:A', 25)
        ws_summary.set_column('B:B', 20)
        
        # Sheet 2: Samples Selected
        ws_samples = workbook.add_worksheet('Samples Selected')
        
        headers = [
            'Sample #', 'Sample Type', 'Stratum', 'Risk Level',
            'Account Code', 'Account Name', 'Description',
            'Amount', 'Date', 'Reference', 'Vendor Name',
            'Selection Reason'
        ]
        
        for col, header in enumerate(headers):
            ws_samples.write(0, col, header, header_format)
        
        for row_idx, sample in enumerate(samples, 1):
            risk_format = None
            if sample['risk_level'] == 'High':
                risk_format = high_risk_format
            elif sample['risk_level'] == 'Medium':
                risk_format = medium_risk_format
            else:
                risk_format = low_risk_format
            
            ws_samples.write(row_idx, 0, row_idx)
            ws_samples.write(row_idx, 1, sample['sample_type'])
            ws_samples.write(row_idx, 2, sample['stratum'])
            ws_samples.write(row_idx, 3, sample['risk_level'], risk_format)
            ws_samples.write(row_idx, 4, sample['account_code'])
            ws_samples.write(row_idx, 5, sample['account_name'])
            ws_samples.write(row_idx, 6, sample['description'])
            ws_samples.write(row_idx, 7, sample['amount'], currency_format)
            ws_samples.write(row_idx, 8, sample['date'])
            ws_samples.write(row_idx, 9, sample['reference'])
            ws_samples.write(row_idx, 10, sample['vendor_name'])
            ws_samples.write(row_idx, 11, sample['selection_reason'])
        
        ws_samples.set_column('A:A', 10)
        ws_samples.set_column('B:C', 15)
        ws_samples.set_column('D:D', 12)
        ws_samples.set_column('E:F', 18)
        ws_samples.set_column('G:G', 35)
        ws_samples.set_column('H:H', 12)
        ws_samples.set_column('I:K', 15)
        ws_samples.set_column('L:L', 40)
        ws_samples.freeze_panes(1, 0)
        
        # Sheet 3: Attributes Checklist
        ws_attributes = workbook.add_worksheet('Attributes Checklist')
        
        attr_headers = ['Sample #', 'Account', 'Amount', 'Risk Level']
        for i in range(1, 8):
            attr_headers.append(f'Attr {i}')
        attr_headers.append('Notes')
        
        for col, header in enumerate(attr_headers):
            ws_attributes.write(0, col, header, header_format)
        
        pending_format = workbook.add_format({'bg_color': '#FFFFE0', 'align': 'center'})
        
        for row_idx, sample in enumerate(samples, 1):
            ws_attributes.write(row_idx, 0, row_idx)
            ws_attributes.write(row_idx, 1, f"{sample['account_code']} - {sample['account_name']}")
            ws_attributes.write(row_idx, 2, sample['amount'], currency_format)
            ws_attributes.write(row_idx, 3, sample['risk_level'])
            
            # Write pending status for all 7 attributes
            for attr_col in range(4, 11):
                ws_attributes.write(row_idx, attr_col, 'PENDING', pending_format)
            
            ws_attributes.write(row_idx, 11, '')  # Notes column
        
        ws_attributes.set_column('A:A', 10)
        ws_attributes.set_column('B:B', 35)
        ws_attributes.set_column('C:C', 12)
        ws_attributes.set_column('D:D', 12)
        ws_attributes.set_column('E:K', 10)
        ws_attributes.set_column('L:L', 40)
        ws_attributes.freeze_panes(1, 0)
        
        # Sheet 4: Attribute Descriptions
        ws_attr_desc = workbook.add_worksheet('Attribute Descriptions')
        
        ws_attr_desc.write('A1', 'Attribute Testing Guidelines', workbook.add_format({'bold': True, 'font_size': 14}))
        
        row = 3
        for attr_num, description in DEFAULT_CONFIG['ATTRIBUTE_CHECKS'].items():
            ws_attr_desc.write(f'A{row}', f'Attribute {attr_num}:', workbook.add_format({'bold': True}))
            ws_attr_desc.write(f'B{row}', description)
            row += 1
        
        ws_attr_desc.set_column('A:A', 15)
        ws_attr_desc.set_column('B:B', 60)
        
        workbook.close()
        
        logger.info(f"Report generated: {output_filename}")

        # Summary
        summary = {
            'total_gl_records': len(df),
            'rm_transactions': len(rm_items),
            'total_rm_amount': round(total_rm_amount, 2),
            'samples_selected': len(samples),
            'auto_included': len(auto_included),
            'stratified': len(samples) - len(auto_included),
            'sampled_amount': round(sampled_amount, 2),
            'coverage_percentage': round(coverage_pct, 1)
        }

        logger.info("=" * 70)
        logger.info("EXECUTION COMPLETE")
        logger.info(f"  R&M Transactions: {summary['rm_transactions']}")
        logger.info(f"  Samples: {summary['samples_selected']}")
        logger.info(f"  Coverage: {summary['coverage_percentage']}%")
        logger.info("=" * 70)

        return jsonify({
            'success': True,
            'tool_id': 'rm_testwork',
            'tool_name': 'R&M Testwork Agent',
            'result': {
                'download_url': f'/api/v1/download/{session_id}/{output_filename}',
                'summary': summary
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
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("R&M TESTWORK API - Starting")
    logger.info("=" * 70)
    logger.info("Port: 5011")
    logger.info("Endpoints:")
    logger.info("  GET  /health")
    logger.info("  GET  /api/v1/info")
    logger.info("  POST /api/v1/execute")
    logger.info("  GET  /api/v1/download/<session_id>/<filename>")
    logger.info("=" * 70)
    
    app.run(host='0.0.0.0', port=5011, debug=True)
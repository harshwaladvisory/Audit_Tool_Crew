import os
import json
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import logging
from datetime import datetime
from typing import List, Dict, Any
import tempfile
import io
import uuid

from config import Config
from models import Database, VendorSession, Vendor
from gemini_ai import classify_vendor, VendorClassificationResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

# Initialize MongoDB
db = Database(app.config['MONGO_URI'], app.config['MONGO_DB_NAME'])
vendor_session_model = VendorSession(db)
vendor_model = Vendor(db)

# File upload settings
ALLOWED_EXTENSIONS = app.config['ALLOWED_EXTENSIONS']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_session_id():
    """Get or create a session ID for vendor data storage"""
    if 'vendor_session_id' not in session:
        session_id = str(uuid.uuid4())
        session['vendor_session_id'] = session_id
        
        # Create session in database
        vendor_session_model.create_session(session_id)
    
    return session['vendor_session_id']


def get_vendor_data() -> List[Dict[str, Any]]:
    """Get vendor data for current session from MongoDB"""
    session_id = get_session_id()
    return vendor_model.get_vendors_by_session(session_id)


def set_vendor_data(data: List[Dict[str, Any]]) -> bool:
    """Set vendor data for current session in MongoDB"""
    session_id = get_session_id()
    
    # Replace all vendors for this session
    success = vendor_model.replace_all_vendors(session_id, data)
    
    if success:
        # Update session metadata
        vendor_session_model.update_session(session_id, {
            'vendor_count': len(data),
            'total_amount': sum(v.get('total_paid', 0) for v in data)
        })
    
    return success


@app.route('/')
def index():
    """Main page with file upload form"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and initial processing"""
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and file.filename and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the uploaded file
            vendors_data = process_vendor_file(filepath)
            
            # Save to MongoDB
            if set_vendor_data(vendors_data):
                # Update session with file info
                session_id = get_session_id()
                vendor_session_model.update_session(session_id, {
                    'file_name': filename,
                    'file_uploaded_at': datetime.utcnow()
                })
                
                flash(f'Successfully uploaded and processed {len(vendors_data)} vendors')
                return redirect(url_for('results'))
            else:
                flash('Error saving vendor data to database')
                return redirect(request.url)
            
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            flash(f'Error processing file: {str(e)}')
            return redirect(request.url)
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
    else:
        flash('Invalid file type. Please upload CSV or Excel files only.')
        return redirect(request.url)


def process_vendor_file(filepath: str) -> List[Dict[str, Any]]:
    """Process uploaded vendor file with deduplication and large file support"""
    try:
        # Read file with chunked processing for large files
        chunk_size = 10000  # Process 10,000 rows at a time
        vendors_dict = {}  # For deduplication
        
        # Determine file type and read accordingly
        if filepath.endswith('.csv'):
            # Read CSV in chunks for large file support
            chunk_iter = pd.read_csv(filepath, chunksize=chunk_size)
        else:
            # For Excel, read all at once but could be optimized for very large files
            df = pd.read_excel(filepath)
            chunk_iter = [df]
        
        for chunk_df in chunk_iter:
            # Standardize column names (case-insensitive matching)
            chunk_df.columns = chunk_df.columns.str.strip()
            column_mapping = detect_columns(chunk_df)
            
            # Process each row in the chunk
            for _, row in chunk_df.iterrows():
                try:
                    vendor_name = str(row.get(column_mapping.get('vendor_name', ''), 'Unknown Vendor')).strip()
                    vendor_id = str(row.get(column_mapping.get('vendor_id', ''), '')).strip()
                    
                    # Handle amount conversion
                    amount_raw = row.get(column_mapping.get('amount', ''), 0)
                    try:
                        # Remove currency symbols and convert to float
                        if isinstance(amount_raw, str):
                            amount = float(amount_raw.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip())
                        else:
                            amount = float(amount_raw) if amount_raw is not None and not pd.isna(amount_raw) else 0.0
                    except (ValueError, TypeError):
                        amount = 0.0
                    
                    accounts = str(row.get(column_mapping.get('accounts', ''), '')).strip()
                    memo = str(row.get(column_mapping.get('memo', ''), '')).strip()
                    
                    # Skip invalid entries
                    if not vendor_name or vendor_name == 'Unknown Vendor' or amount == 0:
                        continue
                    
                    # Create vendor key for deduplication (normalize name)
                    vendor_key = normalize_vendor_name(vendor_name)
                    
                    # Aggregate vendor data (deduplication)
                    if vendor_key in vendors_dict:
                        # Add to existing vendor
                        vendors_dict[vendor_key]['total_paid'] += amount
                        vendors_dict[vendor_key]['transaction_count'] += 1
                        vendors_dict[vendor_key]['accounts'] = list(set(vendors_dict[vendor_key]['accounts'].split(', ') + [accounts]))
                        vendors_dict[vendor_key]['accounts'] = ', '.join([acc for acc in vendors_dict[vendor_key]['accounts'] if acc])
                        if memo and memo not in vendors_dict[vendor_key]['memo']:
                            vendors_dict[vendor_key]['memo'] += f"; {memo}"
                    else:
                        # Create new vendor entry
                        vendors_dict[vendor_key] = {
                            'vendor_name': vendor_name,
                            'vendor_id': vendor_id,
                            'total_paid': amount,
                            'transaction_count': 1,
                            'accounts': accounts,
                            'memo': memo,
                            'classification': '',
                            'form': '',
                            'reason': '',
                            'notes': ''
                        }
                        
                except Exception as e:
                    logger.warning(f"Error processing row: {e}")
                    continue
        
        # Convert dictionary to list and sort by total paid (descending)
        vendors_data = list(vendors_dict.values())
        vendors_data.sort(key=lambda x: x['total_paid'], reverse=True)
        
        # Add global_index to each vendor for stable identification in categorized views
        for idx, vendor in enumerate(vendors_data):
            vendor['global_index'] = idx
        
        logger.info(f"Processed {len(vendors_data)} unique vendors from file")
        return vendors_data
        
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise Exception(f"Error reading file: {str(e)}")


def detect_columns(df: pd.DataFrame) -> Dict[str, str]:
    """Detect and map column names from the dataframe"""
    column_mapping = {}
    
    for col in df.columns:
        col_lower = col.lower().strip()
        
        # Vendor name detection
        if any(keyword in col_lower for keyword in ['vendor', 'payee', 'supplier', 'company']) and any(keyword in col_lower for keyword in ['name']):
            column_mapping['vendor_name'] = col
        # SSN/EIN detection
        elif any(keyword in col_lower for keyword in ['vendor', 'tax', 'ein']) and any(keyword in col_lower for keyword in ['id', 'number']):
            column_mapping['vendor_id'] = col
        # Amount detection - prioritize "paid" over "bill" amounts
        elif any(keyword in col_lower for keyword in ['paid', 'amount', 'total']) and 'bill' not in col_lower:
            if 'amount' not in column_mapping:
                column_mapping['amount'] = col
        elif any(keyword in col_lower for keyword in ['bill', 'invoice']) and any(keyword in col_lower for keyword in ['amount']):
            if 'amount' not in column_mapping:
                column_mapping['amount'] = col
        # Account detection
        elif any(keyword in col_lower for keyword in ['account', 'category', 'class']):
            column_mapping['accounts'] = col
        # Memo/Description detection
        elif any(keyword in col_lower for keyword in ['memo', 'description', 'note', 'detail']):
            column_mapping['memo'] = col
    
    # If standard columns not found, try to infer from first few columns
    if not column_mapping.get('vendor_name'):
        cols = df.columns.tolist()
        if len(cols) >= 1:
            column_mapping['vendor_name'] = cols[0]
        if len(cols) >= 2:
            column_mapping['amount'] = cols[1]
        if len(cols) >= 3:
            column_mapping['vendor_id'] = cols[2]
        if len(cols) >= 4:
            column_mapping['accounts'] = cols[3]
    
    return column_mapping


def normalize_vendor_name(vendor_name: str) -> str:
    """Normalize vendor name for deduplication"""
    # Convert to lowercase and remove common variations
    normalized = vendor_name.lower().strip()
    
    # Remove common suffixes and prefixes
    suffixes = ['inc', 'inc.', 'corp', 'corp.', 'llc', 'ltd', 'ltd.', 'co', 'co.', 'company']
    for suffix in suffixes:
        if normalized.endswith(' ' + suffix):
            normalized = normalized[:-len(suffix)-1].strip()
    
    # Remove special characters and extra spaces
    import re
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def categorize_vendors(vendors: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize vendors into three lists based on classification"""
    categories = {
        '1099-Eligible': [],
        'Non-Reportable': [],
        'W-9 Required': []
    }
    
    for vendor in vendors:
        classification = vendor.get('classification', '')
        vendor_id = vendor.get('vendor_id', '').strip()
        
        # Enhanced detection: Check if vendor has a valid tax ID
        no_tax_id_phrases = ['no tax id', 'no ssn', 'no ein', 'missing', 'not provided', 'n/a']
        has_tax_id = bool(vendor_id and 
                         vendor_id != '-' and 
                         not any(phrase in vendor_id.lower() for phrase in no_tax_id_phrases))
        
        total_paid = vendor.get('total_paid', 0)
        
        if classification in categories:
            categories[classification].append(vendor)
            
            # Rule 1: If 1099-Eligible but no SSN/EIN, also add to W-9 Required
            if classification == '1099-Eligible' and not has_tax_id:
                categories['W-9 Required'].append(vendor)
            
            # Rule 2: If W-9 Required with $600+, also add to 1099-Eligible
            elif classification == 'W-9 Required' and total_paid >= 600:
                vendor_copy = vendor.copy()
                vendor_copy['notes'] = (vendor_copy.get('notes', '') + ' [Pending W-9 - will need 1099 once tax ID collected]').strip()
                categories['1099-Eligible'].append(vendor_copy)
                
        elif not classification:
            # Unclassified vendors
            if total_paid >= 600:
                categories['W-9 Required'].append(vendor)
                vendor_copy = vendor.copy()
                vendor_copy['classification'] = 'W-9 Required'
                vendor_copy['notes'] = (vendor_copy.get('notes', '') + ' [Pending W-9]').strip()
                categories['1099-Eligible'].append(vendor_copy)
            else:
                categories['Non-Reportable'].append(vendor)
        else:
            # Fallback for any other classifications
            categories['W-9 Required'].append(vendor)
    
    return categories


def calculate_vendor_stats_safe(vendors: List[Dict[str, Any]], categories: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Calculate comprehensive statistics with guaranteed keys"""
    total_vendors = len(vendors)
    total_amount = sum(vendor.get('total_paid', 0) for vendor in vendors)
    total_transactions = sum(vendor.get('transaction_count', 1) for vendor in vendors)
    
    # Ensure all required categories exist
    required_categories = ['1099-Eligible', 'Non-Reportable', 'W-9 Required']
    category_stats = {}
    
    for category_name in required_categories:
        category_vendors = categories.get(category_name, [])
        category_total = sum(vendor.get('total_paid', 0) for vendor in category_vendors)
        category_stats[category_name] = {
            'count': len(category_vendors),
            'total_amount': category_total,
            'percentage': (len(category_vendors) / total_vendors * 100) if total_vendors > 0 else 0
        }
    
    # Form type statistics with guaranteed keys
    required_forms = ['1099-NEC', '1099-MISC', 'Not Required', 'W-9 Needed', 'Unclassified']
    form_stats = {}
    
    for form_type in required_forms:
        form_stats[form_type] = {'count': 0, 'total_amount': 0}
    
    for vendor in vendors:
        form_type = vendor.get('form', 'Unclassified')
        if form_type not in form_stats:
            form_stats[form_type] = {'count': 0, 'total_amount': 0}
        form_stats[form_type]['count'] += 1
        form_stats[form_type]['total_amount'] += vendor.get('total_paid', 0)
    
    # Threshold analysis
    over_600 = [v for v in vendors if v.get('total_paid', 0) >= 600]
    under_600 = [v for v in vendors if v.get('total_paid', 0) < 600]
    
    return {
        'total_vendors': total_vendors,
        'total_amount': total_amount,
        'total_transactions': total_transactions,
        'categories': category_stats,
        'forms': form_stats,
        'over_600_count': len(over_600),
        'under_600_count': len(under_600),
        'over_600_amount': sum(v.get('total_paid', 0) for v in over_600),
        'classified_count': len([v for v in vendors if v.get('classification')]),
        'unclassified_count': len([v for v in vendors if not v.get('classification')])
    }


@app.route('/results')
def results():
    """Display results page with categorized vendor data"""
    vendors_data = get_vendor_data()
    if not vendors_data:
        flash('No vendor data available. Please upload a file first.')
        return redirect(url_for('index'))
    
    # Categorize vendors
    vendor_categories = categorize_vendors(vendors_data)
    
    # Calculate statistics with guaranteed keys
    stats = calculate_vendor_stats_safe(vendors_data, vendor_categories)
    
    return render_template('results.html', 
                         vendors=vendors_data,
                         vendor_categories=vendor_categories,
                         stats=stats,
                         processed_vendors=True)


@app.route('/classify', methods=['POST'])
def classify_vendors():
    """Fast classification using rule-based logic only"""
    vendors_data = get_vendor_data()
    
    if not vendors_data:
        return jsonify({'error': 'No vendor data available'}), 400
    
    try:
        import time
        start = time.time()
        
        classified_count = 0
        batch_updates = []
        
        for vendor in vendors_data:
            if not vendor.get('classification'):
                # Use ONLY fast fallback rules (skip AI entirely)
                from gemini_ai import classify_vendor_fallback
                
                result = classify_vendor_fallback(
                    vendor['vendor_name'],
                    vendor['vendor_id'],
                    vendor['total_paid'],
                    vendor['accounts']
                )
                
                update_data = {
                    'global_index': vendor['global_index'],
                    'classification': result.classification,
                    'form': result.form,
                    'reason': result.reason
                }
                
                batch_updates.append(update_data)
                vendor.update({
                    'classification': result.classification,
                    'form': result.form,
                    'reason': result.reason
                })
                
                classified_count += 1
        
        # Batch update database
        if batch_updates:
            session_id = get_session_id()
            vendor_model.bulk_update_vendors(session_id, batch_updates)
        
        elapsed = time.time() - start
        logger.info(f"✅ Classified {classified_count} vendors in {elapsed:.2f} seconds")
        
        return jsonify({
            'success': True,
            'classified_count': classified_count,
            'total_vendors': len(vendors_data),
            'time_seconds': elapsed
        })
        
    except Exception as e:
        logger.error(f"Error during classification: {e}", exc_info=True)
        return jsonify({'error': f'Classification failed: {str(e)}'}), 500


@app.route('/update_vendor', methods=['POST'])
def update_vendor():
    """Update vendor information"""
    try:
        data = request.get_json()
        vendor_index = data.get('index')
        field = data.get('field')
        value = data.get('value')
        
        if vendor_index is None or field not in ['classification', 'form', 'reason', 'notes']:
            return jsonify({'error': 'Invalid request'}), 400
        
        # Update in database
        session_id = get_session_id()
        success = vendor_model.update_vendor(session_id, vendor_index, {field: value})
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Vendor not found'}), 404
        
    except Exception as e:
        logger.error(f"Error updating vendor: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/transfer_vendor', methods=['POST'])
def transfer_vendor():
    """Transfer vendor between 1099-Eligible and Non-Reportable categories"""
    try:
        data = request.get_json()
        vendor_index = data.get('vendor_index')
        new_classification = data.get('new_classification')
        
        # Validate new classification
        if new_classification not in ['1099-Eligible', 'Non-Reportable']:
            return jsonify({'success': False, 'error': 'Invalid classification'}), 400
        
        session_id = get_session_id()
        
        # Get vendor from database
        vendor = vendor_model.get_vendor_by_index(session_id, vendor_index)
        
        if not vendor:
            return jsonify({'success': False, 'error': 'Vendor not found'}), 404
        
        old_classification = vendor.get('classification')
        
        # Only allow transfers between 1099-Eligible and Non-Reportable
        if old_classification not in ['1099-Eligible', 'Non-Reportable']:
            return jsonify({'success': False, 'error': f'Cannot transfer from {old_classification}'}), 400
        
        # Update vendor classification
        update_data = {'classification': new_classification}
        
        # Update form based on new classification
        if new_classification == '1099-Eligible':
            update_data['form'] = '1099-NEC'
            update_data['reason'] = f"Manually transferred from {old_classification} - requires 1099 reporting"
        else:
            update_data['form'] = 'Not Required'
            update_data['reason'] = f"Manually transferred from {old_classification} - not subject to 1099 reporting"
        
        success = vendor_model.update_vendor(session_id, vendor_index, update_data)
        
        if success:
            logger.info(f"Transferred vendor at index {vendor_index} ({vendor.get('vendor_name')}) from {old_classification} to {new_classification}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Update failed'}), 500
        
    except Exception as e:
        logger.error(f"Error transferring vendor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/export/<format_type>')
def export_data(format_type):
    """Export vendor data to CSV or Excel"""
    vendors_data = get_vendor_data()
    
    if not vendors_data:
        flash('No data to export')
        return redirect(url_for('results'))
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'csv':
            return export_to_csv(vendors_data, f'vendor_classification_{timestamp}.csv')
        elif format_type == 'excel':
            return export_to_excel_categorized(vendors_data, f'vendor_classification_{timestamp}.xlsx')
        else:
            flash('Invalid export format')
            return redirect(url_for('results'))
            
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        flash(f'Export failed: {str(e)}')
        return redirect(url_for('results'))


def export_to_csv(vendors: List[Dict], filename: str):
    """Export vendors to CSV format with category sections"""
    vendor_categories = categorize_vendors(vendors)
    
    output = io.StringIO()
    
    # Write summary section
    output.write('VENDOR CLASSIFICATION SUMMARY\n')
    output.write('Category,Vendor Count,Total Amount ($),Percentage\n')
    
    total_vendors = len(vendors)
    total_amount = sum(v.get('total_paid', 0) for v in vendors)
    
    output.write(f'OVERALL TOTAL,{total_vendors},{total_amount:.2f},100.0%\n')
    
    for category_name in ['1099-Eligible', 'Non-Reportable', 'W-9 Required']:
        category_vendors = vendor_categories.get(category_name, [])
        category_total = sum(v.get('total_paid', 0) for v in category_vendors)
        category_count = len(category_vendors)
        percentage = f"{(category_count / total_vendors * 100):.1f}%" if total_vendors > 0 else "0.0%"
        output.write(f'{category_name},{category_count},{category_total:.2f},{percentage}\n')
    
    output.write('\n')
    
    # Define headers
    headers = ['Vendor Name', 'SSN/EIN No.', 'Total Paid', 'Transaction Count',
               'Classification', 'Likely 1099 Form', 'AI Reason', 'Accounts', 'Memo', 'Manual Notes']
    
    # Write categorized vendor data
    for category_name in ['1099-Eligible', 'Non-Reportable', 'W-9 Required']:
        category_vendors = vendor_categories.get(category_name, [])
        
        if category_vendors:
            output.write('\n')
            output.write(f'=== {category_name.upper()} ===\n')
            output.write(','.join(headers) + '\n')
            
            for vendor in category_vendors:
                row = [
                    vendor.get('vendor_name', ''),
                    vendor.get('vendor_id', ''),
                    str(vendor.get('total_paid', 0)),
                    str(vendor.get('transaction_count', 1)),
                    vendor.get('classification', ''),
                    vendor.get('form', ''),
                    vendor.get('reason', ''),
                    vendor.get('accounts', ''),
                    vendor.get('memo', ''),
                    vendor.get('notes', '')
                ]
                
                # Escape commas in fields
                escaped_row = []
                for field in row:
                    if ',' in str(field):
                        escaped_row.append(f'"{field}"')
                    else:
                        escaped_row.append(str(field))
                
                output.write(','.join(escaped_row) + '\n')
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )


def export_to_excel_categorized(vendors: List[Dict], filename: str):
    """Export vendors to Excel with Summary tab and categorized sheets"""
    vendor_categories = categorize_vendors(vendors)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    
    with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
        # Create Summary sheet
        summary_data = []
        total_vendors = len(vendors)
        total_amount = sum(v.get('total_paid', 0) for v in vendors)
        
        summary_data.append(['OVERALL TOTAL', total_vendors, total_amount, '100.0%'])
        
        for category_name in ['1099-Eligible', 'Non-Reportable', 'W-9 Required']:
            category_vendors = vendor_categories.get(category_name, [])
            category_total = sum(v.get('total_paid', 0) for v in category_vendors)
            category_count = len(category_vendors)
            percentage = f"{(category_count / total_vendors * 100):.1f}%" if total_vendors > 0 else "0.0%"
            summary_data.append([category_name, category_count, category_total, percentage])
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.columns = ['Category', 'Vendor Count', 'Total Amount ($)', 'Percentage']
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Create category sheets
        headers = ['Vendor Name', 'SSN/EIN No.', 'Total Paid', 'Transaction Count',
                   'Classification', 'Likely 1099 Form', 'AI Reason', 'Accounts', 'Memo', 'Manual Notes']
        
        category_order = ['1099-Eligible', 'Non-Reportable', 'W-9 Required']
        
        for category_name in category_order:
            category_vendors = vendor_categories.get(category_name, [])
            
            if category_vendors:
                data = []
                for vendor in category_vendors:
                    data.append([
                        vendor.get('vendor_name', ''),
                        vendor.get('vendor_id', ''),
                        vendor.get('total_paid', 0),
                        vendor.get('transaction_count', 1),
                        vendor.get('classification', ''),
                        vendor.get('form', ''),
                        vendor.get('reason', ''),
                        vendor.get('accounts', ''),
                        vendor.get('memo', ''),
                        vendor.get('notes', '')
                    ])
                
                df = pd.DataFrame(data)
                df.columns = headers
                sheet_name = category_name.replace('/', '_').replace(' ', '_').replace('-', '_')[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                empty_df = pd.DataFrame(columns=headers)
                sheet_name = category_name.replace('/', '_').replace(' ', '_').replace('-', '_')[:31]
                empty_df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    temp_file.close()
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/test_classify_one', methods=['POST'])
def test_classify_one():
    """Test classification on a single vendor for debugging"""
    import time
    
    vendors_data = get_vendor_data()
    if not vendors_data:
        return jsonify({'error': 'No data'}), 400
    
    # Find first unclassified vendor
    test_vendor = None
    for v in vendors_data:
        if not v.get('classification'):
            test_vendor = v
            break
    
    if not test_vendor:
        return jsonify({'error': 'All vendors already classified'}), 400
    
    try:
        logger.info(f"Testing classification for: {test_vendor['vendor_name']}")
        
        start_time = time.time()
        
        # Test classification
        result = classify_vendor(
            test_vendor['vendor_name'],
            test_vendor['vendor_id'],
            test_vendor['total_paid'],
            test_vendor['accounts']
        )
        
        elapsed = time.time() - start_time
        
        return jsonify({
            'success': True,
            'vendor': test_vendor['vendor_name'],
            'classification': result.classification,
            'form': result.form,
            'reason': result.reason,
            'time_seconds': elapsed
        })
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    flash('File is too large. Maximum size is 16MB.')
    return redirect(url_for('index'))


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return render_template('500.html'), 500


@app.teardown_appcontext
def cleanup_old_sessions(error):
    """Cleanup old sessions periodically"""
    try:
        # Run cleanup only occasionally (e.g., 10% of requests)
        import random
        if random.random() < 0.1:
            vendor_session_model.cleanup_old_sessions(app.config['SESSION_TIMEOUT_HOURS'])
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")


# ============================================================================
# API ENDPOINTS FOR AI ASSISTANT
# ============================================================================

@app.route('/api/v1/track', methods=['POST'])
def api_track_1099():
    """
    API endpoint for 1099 vendor tracking
    
    FIXED VERSION - Properly handles session continuity and Windows file locking
    
    Request (multipart/form-data or JSON):
    - action: 'add', 'classify', 'report'
    - file: (for add) Excel/CSV with vendor data
    - session_id: (for classify/report) Session ID from 'add' step
    - tax_year: (optional) Tax year (default: current year)
    - format: (for report) 'excel' or 'csv'
    
    Response:
    {
        "success": true,
        "action": "add",
        "result": {
            "session_id": "abc-123",
            "vendors_processed": 215,
            "total_amount": 1207912.35
        }
    }
    """
    try:
        logger.info("=" * 70)
        logger.info("API: 1099 Tracker Request")
        logger.info("=" * 70)
        
        # Get parameters (support both form-data and JSON)
        if request.is_json:
            data = request.json
            action = data.get('action', 'query')
            tax_year = data.get('tax_year', str(datetime.now().year))
            session_id_param = data.get('session_id')
            report_format = data.get('format', 'excel')
        else:
            action = request.form.get('action', 'query')
            tax_year = request.form.get('tax_year', str(datetime.now().year))
            session_id_param = request.form.get('session_id')
            report_format = request.form.get('format', 'excel')
        
        logger.info(f"Action: {action}")
        logger.info(f"Tax Year: {tax_year}")
        logger.info(f"Session ID param: {session_id_param}")
        
        # =====================================================================
        # ACTION: ADD - Create new session and process file
        # =====================================================================
        if action == 'add':
            # Process file upload
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'tool_id': 'tracker_1099',
                    'error': 'File required for add action',
                    'error_type': 'missing_file'
                }), 400
            
            file = request.files['file']
            
            if not file.filename or not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'tool_id': 'tracker_1099',
                    'error': 'Invalid file type. Use CSV or Excel',
                    'error_type': 'invalid_file_type'
                }), 400
            
            # Create NEW session for this workflow
            api_session_id = str(uuid.uuid4())
            vendor_session_model.create_session(api_session_id)
            logger.info(f"✅ Created new session: {api_session_id}")
            
            # Save file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{api_session_id}_{filename}")
            file.save(filepath)
            
            try:
                # Process vendors
                vendors_data = process_vendor_file(filepath)
                
                # Save to database
                vendor_model.bulk_create_vendors(api_session_id, vendors_data)
                
                total_amount = sum(v.get('total_paid', 0) for v in vendors_data)
                
                # Update session
                vendor_session_model.update_session(api_session_id, {
                    'file_name': filename,
                    'vendor_count': len(vendors_data),
                    'total_amount': total_amount,
                    'file_uploaded_at': datetime.utcnow(),
                    'tax_year': tax_year
                })
                
                result = {
                    'session_id': api_session_id,  # CRITICAL: Return this!
                    'vendors_processed': len(vendors_data),
                    'total_amount': total_amount
                }
                
                logger.info(f"✅ Processed {len(vendors_data)} vendors")
                
            finally:
                # Clean up file
                if os.path.exists(filepath):
                    os.remove(filepath)
        
        # =====================================================================
        # ACTION: CLASSIFY - Use existing session
        # =====================================================================
        elif action == 'classify':
            # MUST have session_id from previous 'add' call
            if not session_id_param:
                return jsonify({
                    'success': False,
                    'tool_id': 'tracker_1099',
                    'error': 'session_id required for classify action',
                    'error_type': 'missing_session_id'
                }), 400
            
            api_session_id = session_id_param
            logger.info(f"Using existing session: {api_session_id}")
            
            # Get vendors for this session
            vendors_data = vendor_model.get_vendors_by_session(api_session_id)
            
            if not vendors_data:
                return jsonify({
                    'success': False,
                    'tool_id': 'tracker_1099',
                    'error': f'No vendors found for session {api_session_id[:8]}. Did you run add first?',
                    'error_type': 'no_data'
                }), 400
            
            logger.info(f"Found {len(vendors_data)} vendors to classify")
            
            # Fast classification using rule-based logic
            classified_count = 0
            batch_updates = []
            
            for vendor in vendors_data:
                if not vendor.get('classification'):
                    from gemini_ai import classify_vendor_fallback
                    
                    result_class = classify_vendor_fallback(
                        vendor['vendor_name'],
                        vendor['vendor_id'],
                        vendor['total_paid'],
                        vendor.get('accounts', '')
                    )
                    
                    update_data = {
                        'global_index': vendor['global_index'],
                        'classification': result_class.classification,
                        'form': result_class.form,
                        'reason': result_class.reason
                    }
                    
                    batch_updates.append(update_data)
                    vendor.update(update_data)
                    classified_count += 1
            
            # Batch update
            if batch_updates:
                vendor_model.bulk_update_vendors(api_session_id, batch_updates)
            
            # Categorize
            categories = categorize_vendors(vendors_data)
            
            result = {
                'session_id': api_session_id,
                'classified_count': classified_count,
                'total_vendors': len(vendors_data),
                'categories': {
                    '1099-Eligible': len(categories.get('1099-Eligible', [])),
                    'Non-Reportable': len(categories.get('Non-Reportable', [])),
                    'W-9 Required': len(categories.get('W-9 Required', []))
                }
            }
            
            logger.info(f"✅ Classified {classified_count} vendors")
        
        # =====================================================================
        # ACTION: REPORT - Generate downloadable report (WINDOWS COMPATIBLE)
        # =====================================================================
        elif action == 'report':
            # MUST have session_id
            if not session_id_param:
                return jsonify({
                    'success': False,
                    'tool_id': 'tracker_1099',
                    'error': 'session_id required for report action',
                    'error_type': 'missing_session_id'
                }), 400
            
            api_session_id = session_id_param
            logger.info(f"Generating report for session: {api_session_id}")
            
            # Get vendors for this session
            vendors_data = vendor_model.get_vendors_by_session(api_session_id)
            
            if not vendors_data:
                return jsonify({
                    'success': False,
                    'tool_id': 'tracker_1099',
                    'error': f'No data to report for session {api_session_id[:8]}',
                    'error_type': 'no_data'
                }), 400
            
            try:
                # Generate report filename DIRECTLY in output folder (no temp file!)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_filename = f"1099_report_{tax_year}_{timestamp}.xlsx"
                report_path = os.path.join(app.config['UPLOAD_FOLDER'], report_filename)
                
                logger.info(f"Creating Excel report at: {report_path}")
                
                # Categorize vendors
                vendor_categories = categorize_vendors(vendors_data)
                
                # Create Excel file DIRECTLY (no temp file needed - Windows safe!)
                with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
                    # Summary sheet
                    summary_data = []
                    total_vendors = len(vendors_data)
                    total_amount = sum(v.get('total_paid', 0) for v in vendors_data)
                    
                    summary_data.append(['OVERALL TOTAL', total_vendors, f'${total_amount:,.2f}', '100.0%'])
                    summary_data.append(['', '', '', ''])  # Blank row
                    
                    for category_name in ['1099-Eligible', 'Non-Reportable', 'W-9 Required']:
                        category_vendors = vendor_categories.get(category_name, [])
                        category_total = sum(v.get('total_paid', 0) for v in category_vendors)
                        category_count = len(category_vendors)
                        percentage = f"{(category_count / total_vendors * 100):.1f}%" if total_vendors > 0 else "0.0%"
                        summary_data.append([
                            category_name, 
                            category_count, 
                            f'${category_total:,.2f}', 
                            percentage
                        ])
                    
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.columns = ['Category', 'Vendor Count', 'Total Amount', 'Percentage']
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    logger.info("✅ Summary sheet created")
                    
                    # Category sheets
                    headers = [
                        'Vendor Name', 'SSN/EIN No.', 'Total Paid', 'Transaction Count',
                        'Classification', 'Likely 1099 Form', 'AI Reason', 
                        'Accounts', 'Memo', 'Manual Notes'
                    ]
                    
                    for category_name in ['1099-Eligible', 'Non-Reportable', 'W-9 Required']:
                        category_vendors = vendor_categories.get(category_name, [])
                        
                        data = []
                        for vendor in category_vendors:
                            data.append([
                                vendor.get('vendor_name', ''),
                                vendor.get('vendor_id', ''),
                                vendor.get('total_paid', 0),
                                vendor.get('transaction_count', 1),
                                vendor.get('classification', ''),
                                vendor.get('form', ''),
                                vendor.get('reason', ''),
                                vendor.get('accounts', ''),
                                vendor.get('memo', ''),
                                vendor.get('notes', '')
                            ])
                        
                        if data:
                            df = pd.DataFrame(data, columns=headers)
                        else:
                            df = pd.DataFrame(columns=headers)
                        
                        # Clean sheet name (max 31 chars, no special chars)
                        sheet_name = category_name.replace('/', '_').replace(' ', '_').replace('-', '_')
                        sheet_name = sheet_name[:31]
                        
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        logger.info(f"✅ Created sheet: {sheet_name} with {len(data)} vendors")
                
                # File is automatically closed by the context manager - Windows safe!
                
                # Verify file was created
                if not os.path.exists(report_path):
                    raise Exception("Report file was not created successfully")
                
                file_size = os.path.getsize(report_path)
                logger.info(f"✅ Report created successfully: {report_filename} ({file_size} bytes)")
                
                # Create download URL
                download_url = f"/api/v1/download/{report_filename}"
                
                result = {
                    'session_id': api_session_id,
                    'report_file': report_filename,
                    'download_url': download_url,
                    'file_size': file_size,
                    'tax_year': tax_year,
                    'vendors_count': len(vendors_data),
                    'categories': {
                        '1099-Eligible': len(vendor_categories.get('1099-Eligible', [])),
                        'Non-Reportable': len(vendor_categories.get('Non-Reportable', [])),
                        'W-9 Required': len(vendor_categories.get('W-9 Required', []))
                    }
                }
                
                logger.info(f"✅ Report generation complete")
                
            except Exception as e:
                logger.error(f"❌ Error generating report: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'tool_id': 'tracker_1099',
                    'error': f'Report generation failed: {str(e)}',
                    'error_type': 'report_generation_error',
                    'timestamp': datetime.utcnow().isoformat()
                }), 500
        
        # =====================================================================
        # ACTION: QUERY - Get summary
        # =====================================================================
        elif action == 'query':
            if session_id_param:
                api_session_id = session_id_param
                vendors_data = vendor_model.get_vendors_by_session(api_session_id)
            else:
                vendors_data = []
            
            if vendors_data:
                categories = categorize_vendors(vendors_data)
                result = {
                    'session_id': api_session_id,
                    'total_vendors': len(vendors_data),
                    'total_amount': sum(v.get('total_paid', 0) for v in vendors_data),
                    'categories': {
                        '1099-Eligible': len(categories.get('1099-Eligible', [])),
                        'Non-Reportable': len(categories.get('Non-Reportable', [])),
                        'W-9 Required': len(categories.get('W-9 Required', []))
                    }
                }
            else:
                result = {'message': 'No active session. Start with add action.'}
        
        else:
            return jsonify({
                'success': False,
                'tool_id': 'tracker_1099',
                'error': f'Unknown action: {action}',
                'error_type': 'invalid_action'
            }), 400
        
        # =====================================================================
        # SUCCESS RESPONSE
        # =====================================================================
        response = {
            'success': True,
            'tool_id': 'tracker_1099',
            'tool_name': '1099 Tracker',
            'action': action,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("✅ API: 1099 Tracker Complete")
        logger.info("=" * 70)
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ API Error: {e}", exc_info=True)
        
        return jsonify({
            'success': False,
            'tool_id': 'tracker_1099',
            'error': str(e),
            'error_type': 'processing_error',
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/download/<filename>', methods=['GET'])
def api_download_1099(filename: str):
    """Download report file"""
    try:
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return send_file(filepath, as_attachment=True, download_name=safe_filename)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/v1/health', methods=['GET'])
def api_health_1099():
    """Health check"""
    try:
        # Test MongoDB connection
        db_connected = db.client.admin.command('ping')['ok'] == 1
    except:
        db_connected = False
    
    return jsonify({
        'status': 'healthy',
        'tool_id': 'tracker_1099',
        'tool_name': '1099 Tracker',
        'version': '1.0.0',
        'database': 'connected' if db_connected else 'disconnected',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/v1/info', methods=['GET'])
def api_info_1099():
    """Tool information"""
    return jsonify({
        'tool_id': 'tracker_1099',
        'tool_name': '1099 Tracker',
        'description': 'Track vendor payments for 1099 tax reporting with AI classification',
        'category': 'tax_compliance',
        'version': '1.0.0',
        'port': 5001,
        'required_params': [
            {
                'name': 'action',
                'type': 'string',
                'options': ['add', 'classify', 'query', 'report']
            }
        ],
        'optional_params': [
            {
                'name': 'file',
                'type': 'file',
                'description': 'Vendor data file (CSV/Excel) - required for add'
            },
            {
                'name': 'session_id',
                'type': 'string',
                'description': 'Session ID from add step - required for classify/report'
            },
            {
                'name': 'tax_year',
                'type': 'string',
                'default': 'current year'
            },
            {
                'name': 'format',
                'type': 'string',
                'default': 'excel',
                'options': ['excel', 'csv']
            }
        ],
        'examples': [
            'Track vendors for 1099 reporting',
            'Generate 1099 report for 2024',
            'Classify vendors from this Excel file'
        ]
    }), 200


if __name__ == '__main__':
    app.run(port=5001, debug=True, use_reloader=False)
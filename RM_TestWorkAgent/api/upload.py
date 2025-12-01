import os
import hashlib
import traceback
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models import Run, GLPopulation, TBMapping, AuditLog
import pandas as pd
from datetime import datetime

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_tb_columns(df):
    """Smart detection of TB file columns"""
    original_columns = list(df.columns)
    current_app.logger.info(f"Detecting TB columns from: {original_columns}")
    
    # Normalize column names
    df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_').str.replace('-', '_').str.replace('.', '_')
    normalized_columns = list(df.columns)
    current_app.logger.info(f"Normalized columns: {normalized_columns}")
    
    result = {
        'account_code': None,
        'account_name': None,
        'tb_amount': None
    }
    
    # 1. Find Account Code column
    account_patterns = ['account', 'acc', 'acct', 'code', 'number', 'no']
    for col in df.columns:
        col_lower = col.lower()
        # Skip if it's clearly a name/description column
        if any(skip in col_lower for skip in ['name', 'desc', 'title']):
            continue
        # Check if any account pattern matches
        if any(pattern in col_lower for pattern in account_patterns):
            result['account_code'] = col
            current_app.logger.info(f"Found account_code: {col}")
            break
    
    # 2. Find Account Name column
    name_patterns = ['name', 'description', 'desc', 'title']
    for col in df.columns:
        col_lower = col.lower()
        if col == result['account_code']:
            continue
        if any(pattern in col_lower for pattern in name_patterns):
            result['account_name'] = col
            current_app.logger.info(f"Found account_name: {col}")
            break
    
    # 3. Find Amount column - try multiple strategies
    
    # Strategy A: Look for explicit TB/Balance/Amount keywords
    amount_patterns = ['balance', 'amount', 'total', 'value', 'debit', 'credit', 'tb']
    for col in df.columns:
        if col in [result['account_code'], result['account_name']]:
            continue
        col_lower = col.lower()
        if any(pattern in col_lower for pattern in amount_patterns):
            if pd.api.types.is_numeric_dtype(df[col]) or df[col].dtype == 'object':
                try:
                    pd.to_numeric(df[col], errors='coerce')
                    result['tb_amount'] = col
                    current_app.logger.info(f"Found tb_amount (keyword match): {col}")
                    break
                except:
                    pass
    
    # Strategy B: If not found, find ANY numeric column that's not account code
    if not result['tb_amount']:
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        current_app.logger.info(f"Numeric columns: {numeric_columns}")
        
        for col in numeric_columns:
            if col != result['account_code']:
                result['tb_amount'] = col
                current_app.logger.info(f"Found tb_amount (numeric): {col}")
                break
    
    # Strategy C: Try to convert object columns to numeric
    if not result['tb_amount']:
        for col in df.columns:
            if col in [result['account_code'], result['account_name']]:
                continue
            try:
                test_series = pd.to_numeric(df[col], errors='coerce')
                if test_series.notna().sum() / len(df) > 0.5:
                    result['tb_amount'] = col
                    current_app.logger.info(f"Found tb_amount (convertible): {col}")
                    break
            except:
                pass
    
    # Strategy D: Last resort - use the last column
    if not result['tb_amount']:
        last_col = df.columns[-1]
        if last_col not in [result['account_code'], result['account_name']]:
            result['tb_amount'] = last_col
            current_app.logger.warning(f"Using last column as tb_amount: {last_col}")
    
    current_app.logger.info(f"Detection result: {result}")
    return result, df


@upload_bp.route('/upload', methods=['POST'])
def upload_files():
    """Upload GL, TB, and config files"""
    try:
        current_app.logger.info("Upload request received")
        
        run_name = request.form.get('run_name', 'Untitled Run')
        gl_file = request.files.get('gl_file')
        tb_file = request.files.get('tb_file')
        config_file = request.files.get('config_file')
        
        if not gl_file or gl_file.filename == '':
            return jsonify({'success': False, 'error': 'GL Population file is required'}), 400
        
        if not allowed_file(gl_file.filename):
            return jsonify({'success': False, 'error': 'Invalid GL file type'}), 400
        
        # Create new run
        run = Run(
            name=run_name,
            status='draft',
            capitalization_threshold=current_app.config.get('CAPITALIZATION_THRESHOLD', 5000),
            materiality=current_app.config.get('MATERIALITY', 25000),
            fy_start=current_app.config.get('FY_START'),
            fy_end=current_app.config.get('FY_END'),
            allowed_accounts=current_app.config.get('ALLOWED_ACCOUNTS', [])
        )
        run.save()
        current_app.logger.info(f"Run created: {run.id}")
        
        # Process GL file
        gl_filename = secure_filename(gl_file.filename)
        gl_path = os.path.join(current_app.config['FILE_STORAGE'], f"{run.id}_gl_{gl_filename}")
        gl_file.save(gl_path)
        
        if gl_filename.endswith('.csv'):
            gl_df = pd.read_csv(gl_path)
        else:
            gl_df = pd.read_excel(gl_path)
        
        current_app.logger.info(f"GL original columns: {list(gl_df.columns)}")
        gl_df.columns = gl_df.columns.str.lower().str.strip().str.replace(' ', '_')
        
        column_mapping = {
            'account': 'account_code',
            'account_no': 'account_code',
            'acc_code': 'account_code',
            'account_code': 'account_code',
            'account_description': 'account_name',
            'account_name': 'account_name',
            'desc': 'description',
            'description': 'description',
            'value': 'amount',
            'amount': 'amount',
            'vendor': 'vendor_name',
            'vendor_name': 'vendor_name'
        }
        gl_df.rename(columns=column_mapping, inplace=True)
        
        required = ['account_code', 'account_name', 'amount']
        missing = [c for c in required if c not in gl_df.columns]
        if missing:
            run.delete()
            return jsonify({'success': False, 'error': f'Missing GL columns: {", ".join(missing)}'}), 400
        
        for col in ['description', 'date', 'reference', 'vendor_name']:
            if col not in gl_df.columns:
                gl_df[col] = ''
        
        gl_df['amount'] = pd.to_numeric(gl_df['amount'], errors='coerce').fillna(0)
        
        gl_records = []
        for idx, row in gl_df.iterrows():
            gl_records.append(GLPopulation(
                run=run,
                account_code=str(row['account_code']).strip(),
                account_name=str(row['account_name']).strip(),
                description=str(row.get('description', '')).strip(),
                amount=float(row['amount']),
                date=str(row.get('date', '')).strip(),
                reference=str(row.get('reference', '')).strip(),
                vendor_name=str(row.get('vendor_name', '')).strip(),
                row_number=idx + 1
            ))
        
        if gl_records:
            GLPopulation.objects.insert(gl_records)
        
        gl_count = len(gl_records)
        gl_total = float(gl_df['amount'].sum())
        
        tb_count = 0
        tb_total = 0
        tb_warnings = []
        
        if tb_file and tb_file.filename:
            try:
                tb_filename = secure_filename(tb_file.filename)
                tb_path = os.path.join(current_app.config['FILE_STORAGE'], f"{run.id}_tb_{tb_filename}")
                tb_file.save(tb_path)
                
                current_app.logger.info(f"Processing TB file: {tb_filename}")
                
                if tb_filename.endswith('.csv'):
                    tb_df = pd.read_csv(tb_path)
                else:
                    tb_df = pd.read_excel(tb_path)
                
                # Use smart column detection
                column_map, tb_df = detect_tb_columns(tb_df)
                
                if not column_map['account_code']:
                    raise ValueError("Could not detect account code column in TB file")
                
                if not column_map['tb_amount']:
                    raise ValueError("Could not detect amount column in TB file")
                
                # Rename columns
                rename_dict = {}
                if column_map['account_code']:
                    rename_dict[column_map['account_code']] = 'account_code'
                if column_map['account_name']:
                    rename_dict[column_map['account_name']] = 'account_name'
                if column_map['tb_amount']:
                    rename_dict[column_map['tb_amount']] = 'tb_amount'
                
                tb_df.rename(columns=rename_dict, inplace=True)
                
                if 'account_name' not in tb_df.columns:
                    tb_df['account_name'] = ''
                
                # Convert amount to numeric
                tb_df['tb_amount'] = pd.to_numeric(tb_df['tb_amount'], errors='coerce').fillna(0)
                
                current_app.logger.info(f"TB final columns: {list(tb_df.columns)}")
                current_app.logger.info(f"TB rows: {len(tb_df)}")
                
                tb_records = []
                for idx, row in tb_df.iterrows():
                    account_code = str(row.get('account_code', '')).strip()
                    if account_code and account_code != 'nan' and account_code != '':
                        tb_records.append(TBMapping(
                            run=run,
                            account_code=account_code,
                            account_name=str(row.get('account_name', '')).strip(),
                            tb_amount=float(row['tb_amount'])
                        ))
                
                if tb_records:
                    TBMapping.objects.insert(tb_records)
                    tb_count = len(tb_records)
                    tb_total = sum(r.tb_amount for r in tb_records)
                    current_app.logger.info(f"TB file processed: {tb_count} records, total: {tb_total}")
                else:
                    tb_warnings.append("No valid TB records found in file")
                    
            except Exception as e:
                error_msg = str(e)
                current_app.logger.warning(f"TB file processing error: {error_msg}")
                current_app.logger.warning(traceback.format_exc())
                tb_warnings.append(f"TB file could not be processed: {error_msg}")
        
        # Process config file
        if config_file and config_file.filename:
            try:
                config_filename = secure_filename(config_file.filename)
                config_path = os.path.join(current_app.config['FILE_STORAGE'], f"{run.id}_config_{config_filename}")
                config_file.save(config_path)
                
                if config_filename.endswith('.csv'):
                    config_df = pd.read_csv(config_path)
                else:
                    config_df = pd.read_excel(config_path)
                
                config_df.columns = config_df.columns.str.lower().str.strip().str.replace(' ', '_')
                
                for idx, row in config_df.iterrows():
                    param = str(row.get('parameter', '')).lower().strip()
                    value = row.get('value', '')
                    
                    if param == 'capitalization_threshold':
                        run.capitalization_threshold = float(value)
                    elif param == 'materiality':
                        run.materiality = float(value)
                    elif param == 'fy_start':
                        run.fy_start = str(value).strip()
                    elif param == 'fy_end':
                        run.fy_end = str(value).strip()
                    elif param == 'allowed_accounts':
                        run.allowed_accounts = str(value).split(';')
                
                current_app.logger.info("Config file processed successfully")
                
            except Exception as e:
                current_app.logger.warning(f"Config file processing warning: {str(e)}")
        
        run.metrics = {
            'gl_population': {
                'total_count': gl_count,
                'total_amount': gl_total,
                'uploaded_at': datetime.utcnow().isoformat()
            }
        }
        
        if tb_count > 0:
            run.metrics['tb_reconciliation'] = {
                'tb_total': tb_total,
                'gl_total': gl_total,
                'variance': abs(tb_total - gl_total),
                'reconciled': abs(tb_total - gl_total) < 0.01
            }
        
        run.save()
        
        try:
            AuditLog(
                run=run,
                action='files_uploaded',
                resource_type='run',
                resource_id=str(run.id),
                details={'gl_records': gl_count, 'tb_records': tb_count, 'tb_warnings': tb_warnings}
            ).save()
        except:
            pass
        
        response_data = {
            'success': True,
            'run_id': str(run.id),
            'gl_records': gl_count,
            'tb_records': tb_count,
            'message': f'Successfully uploaded GL file ({gl_count} records)' + (f' and TB file ({tb_count} records)' if tb_count > 0 else '')
        }
        
        if tb_warnings:
            response_data['warnings'] = tb_warnings
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@upload_bp.route('/upload/gl', methods=['POST'])
def upload_gl():
    """Upload GL file to existing run"""
    try:
        if 'file' not in request.files or 'run_id' not in request.form:
            return jsonify({'success': False, 'error': 'Missing file or run_id'}), 400
        
        file = request.files['file']
        run_id = request.form['run_id']
        
        run = Run.objects.get(id=run_id)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['FILE_STORAGE'], f"{run_id}_gl_{filename}")
        file.save(filepath)
        
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
        
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
        
        GLPopulation.objects(run=run).delete()
        
        records = []
        for idx, row in df.iterrows():
            records.append(GLPopulation(
                run=run,
                account_code=str(row.get('account_code', '')),
                account_name=str(row.get('account_name', '')),
                amount=float(row.get('amount', 0)),
                row_number=idx + 1
            ))
        
        if records:
            GLPopulation.objects.insert(records)
        
        return jsonify({'success': True, 'message': f'Uploaded {len(records)} records'})
        
    except Exception as e:
        current_app.logger.error(f"GL upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@upload_bp.route('/upload/tb', methods=['POST'])
def upload_tb():
    """Upload TB file to existing run"""
    try:
        if 'file' not in request.files or 'run_id' not in request.form:
            return jsonify({'success': False, 'error': 'Missing file or run_id'}), 400
        
        file = request.files['file']
        run_id = request.form['run_id']
        
        run = Run.objects.get(id=run_id)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['FILE_STORAGE'], f"{run_id}_tb_{filename}")
        file.save(filepath)
        
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
        
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
        
        TBMapping.objects(run=run).delete()
        
        records = []
        for idx, row in df.iterrows():
            records.append(TBMapping(
                run=run,
                account_code=str(row.get('account_code', '')),
                account_name=str(row.get('account_name', '')),
                tb_amount=float(row.get('tb_amount', 0))
            ))
        
        if records:
            TBMapping.objects.insert(records)
        
        return jsonify({'success': True, 'message': f'Uploaded {len(records)} records'})
        
    except Exception as e:
        current_app.logger.error(f"TB upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
import re
import pandas as pd
from typing import Dict, Any, List, Optional
from werkzeug.datastructures import FileStorage
import logging

def validate_excel_file(file: FileStorage) -> bool:
    """Validate if file is a valid Excel file"""
    if not file or file.filename == '':
        return False
    
    # Check file extension
    allowed_extensions = ['.xlsx', '.xls']
    filename = file.filename.lower()
    
    return any(filename.endswith(ext) for ext in allowed_extensions)

def validate_gl_population_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate GL Population DataFrame structure"""
    required_columns = ['Account Code', 'Account Name', 'Description', 'Amount']
    optional_columns = ['Date', 'Reference', 'Vendor Name']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            'valid': False,
            'error': f'Missing required columns: {", ".join(missing_columns)}',
            'missing_columns': missing_columns
        }
    
    # Validate data types and content
    validation_errors = []
    
    # Check for empty required fields
    for col in required_columns:
        if col == 'Amount':
            # Check for numeric amounts
            non_numeric = df[df[col].notna()][col].apply(lambda x: not isinstance(x, (int, float)) and not str(x).replace('.', '').replace('-', '').isdigit())
            if non_numeric.any():
                validation_errors.append(f'Non-numeric values found in Amount column')
        else:
            # Check for empty strings in text fields
            empty_values = df[col].isna() | (df[col] == '')
            if empty_values.any():
                validation_errors.append(f'Empty values found in {col} column')
    
    # Validate account codes format
    account_codes = df['Account Code'].dropna().astype(str)
    invalid_codes = account_codes[~account_codes.str.match(r'^[A-Za-z0-9\-\.]+$')]
    if not invalid_codes.empty:
        validation_errors.append('Invalid account code format detected')
    
    # Check for duplicate entries
    if 'Reference' in df.columns:
        duplicates = df[df['Reference'].notna()].duplicated(subset=['Account Code', 'Amount', 'Reference'])
        if duplicates.any():
            validation_errors.append(f'{duplicates.sum()} potential duplicate entries found')
    
    return {
        'valid': len(validation_errors) == 0,
        'errors': validation_errors,
        'row_count': len(df),
        'column_count': len(df.columns),
        'warnings': []
    }

def validate_tb_mapping_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate Trial Balance Mapping DataFrame structure"""
    required_columns = ['Account Code', 'Account Name', 'TB Amount']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            'valid': False,
            'error': f'Missing required columns: {", ".join(missing_columns)}',
            'missing_columns': missing_columns
        }
    
    validation_errors = []
    
    # Validate TB amounts are numeric
    tb_amounts = df['TB Amount'].dropna()
    non_numeric = tb_amounts.apply(lambda x: not isinstance(x, (int, float)) and not str(x).replace('.', '').replace('-', '').isdigit())
    if non_numeric.any():
        validation_errors.append('Non-numeric values found in TB Amount column')
    
    # Check for empty account codes
    empty_codes = df['Account Code'].isna() | (df['Account Code'] == '')
    if empty_codes.any():
        validation_errors.append('Empty account codes found')
    
    # Check for duplicate account codes
    duplicates = df.duplicated(subset=['Account Code'])
    if duplicates.any():
        validation_errors.append(f'{duplicates.sum()} duplicate account codes found')
    
    return {
        'valid': len(validation_errors) == 0,
        'errors': validation_errors,
        'row_count': len(df),
        'column_count': len(df.columns)
    }

def validate_run_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate run configuration parameters"""
    validation_errors = []
    warnings = []
    
    # Validate capitalization threshold
    cap_threshold = config.get('capitalization_threshold')
    if cap_threshold is None:
        validation_errors.append('Capitalization threshold is required')
    elif not isinstance(cap_threshold, (int, float)) or cap_threshold < 0:
        validation_errors.append('Capitalization threshold must be a positive number')
    
    # Validate materiality
    materiality = config.get('materiality')
    if materiality is None:
        validation_errors.append('Materiality is required')
    elif not isinstance(materiality, (int, float)) or materiality < 0:
        validation_errors.append('Materiality must be a positive number')
    
    # Check threshold vs materiality relationship
    if cap_threshold and materiality and cap_threshold > materiality:
        warnings.append('Capitalization threshold exceeds materiality - this may result in excessive auto-inclusions')
    
    # Validate fiscal year dates
    fy_start = config.get('fy_start')
    fy_end = config.get('fy_end')
    
    if not fy_start:
        validation_errors.append('Fiscal year start date is required')
    if not fy_end:
        validation_errors.append('Fiscal year end date is required')
    
    if fy_start and fy_end:
        try:
            from datetime import datetime
            start_date = datetime.strptime(fy_start, '%Y-%m-%d')
            end_date = datetime.strptime(fy_end, '%Y-%m-%d')
            
            if start_date >= end_date:
                validation_errors.append('Fiscal year start date must be before end date')
            
            # Check if fiscal year is reasonable (between 1 month and 18 months)
            duration_days = (end_date - start_date).days
            if duration_days < 30:
                warnings.append('Fiscal year duration is less than 1 month')
            elif duration_days > 550:
                warnings.append('Fiscal year duration exceeds 18 months')
                
        except ValueError:
            validation_errors.append('Invalid date format for fiscal year dates')
    
    # Validate allowed accounts
    allowed_accounts = config.get('allowed_accounts', [])
    if not allowed_accounts:
        validation_errors.append('At least one allowed account type must be specified')
    elif isinstance(allowed_accounts, str):
        allowed_accounts = allowed_accounts.split(';')
    
    if len(allowed_accounts) == 0:
        validation_errors.append('At least one allowed account type must be specified')
    
    return {
        'valid': len(validation_errors) == 0,
        'errors': validation_errors,
        'warnings': warnings,
        'normalized_config': {
            'capitalization_threshold': float(cap_threshold) if cap_threshold else 0,
            'materiality': float(materiality) if materiality else 0,
            'fy_start': fy_start,
            'fy_end': fy_end,
            'allowed_accounts': allowed_accounts if isinstance(allowed_accounts, list) else allowed_accounts.split(';')
        }
    }

def validate_attribute_check_data(attribute_number: int, status: str, comment: str = '') -> Dict[str, Any]:
    """Validate attribute check data"""
    validation_errors = []
    
    # Validate attribute number
    if not isinstance(attribute_number, int) or attribute_number < 1 or attribute_number > 7:
        validation_errors.append('Attribute number must be between 1 and 7')
    
    # Validate status
    valid_statuses = ['pass', 'fail', 'na', 'pending']
    if status not in valid_statuses:
        validation_errors.append(f'Status must be one of: {", ".join(valid_statuses)}')
    
    # Validate comment requirements
    if status == 'fail' and not comment.strip():
        validation_errors.append('Comment is required when status is "fail"')
    
    if comment and len(comment) > 1000:
        validation_errors.append('Comment cannot exceed 1000 characters')
    
    return {
        'valid': len(validation_errors) == 0,
        'errors': validation_errors
    }

def validate_email_format(email: str) -> bool:
    """Validate email format using regex"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_account_code_format(account_code: str) -> bool:
    """Validate account code format"""
    if not account_code:
        return False
    
    # Allow alphanumeric characters, hyphens, and periods
    pattern = r'^[A-Za-z0-9\-\.]{1,20}$'
    return re.match(pattern, account_code) is not None

def validate_amount_format(amount: Any) -> Dict[str, Any]:
    """Validate monetary amount format"""
    if amount is None:
        return {'valid': False, 'error': 'Amount cannot be None'}
    
    try:
        if isinstance(amount, str):
            # Remove common currency symbols and formatting
            cleaned = amount.replace('$', '').replace(',', '').strip()
            amount = float(cleaned)
        elif not isinstance(amount, (int, float)):
            return {'valid': False, 'error': 'Amount must be a number'}
        
        # Check for reasonable range
        if amount < -1000000000:  # -1 billion
            return {'valid': False, 'error': 'Amount too small (less than -1 billion)'}
        elif amount > 1000000000:  # 1 billion
            return {'valid': False, 'error': 'Amount too large (greater than 1 billion)'}
        
        return {'valid': True, 'normalized_amount': round(float(amount), 2)}
        
    except (ValueError, TypeError):
        return {'valid': False, 'error': 'Invalid amount format'}

def validate_file_upload_data(files: Dict[str, FileStorage], required_files: List[str] = None) -> Dict[str, Any]:
    """Validate file upload data"""
    if required_files is None:
        required_files = ['gl_file']
    
    validation_errors = []
    warnings = []
    
    # Check required files
    for required_file in required_files:
        if required_file not in files or not files[required_file] or files[required_file].filename == '':
            validation_errors.append(f'Required file missing: {required_file}')
    
    # Validate each uploaded file
    for file_key, file in files.items():
        if file and file.filename:
            if not validate_excel_file(file):
                validation_errors.append(f'Invalid file format for {file_key}: must be Excel (.xlsx or .xls)')
            
            # Check file size
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            
            max_size = 16 * 1024 * 1024  # 16MB
            if file_size > max_size:
                validation_errors.append(f'File {file_key} too large: {file_size / (1024*1024):.1f}MB (max 16MB)')
            elif file_size == 0:
                validation_errors.append(f'File {file_key} is empty')
    
    return {
        'valid': len(validation_errors) == 0,
        'errors': validation_errors,
        'warnings': warnings
    }

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    if not filename:
        return 'untitled'
    
    # Remove or replace dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    sanitized = re.sub(r'\.{2,}', '.', sanitized)  # Replace multiple dots
    sanitized = sanitized.strip('. ')  # Remove leading/trailing dots and spaces
    
    # Limit length
    if len(sanitized) > 100:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:95] + ext
    
    return sanitized or 'untitled'

def validate_date_range(start_date: str, end_date: str, date_format: str = '%Y-%m-%d') -> Dict[str, Any]:
    """Validate date range"""
    try:
        from datetime import datetime
        
        start = datetime.strptime(start_date, date_format)
        end = datetime.strptime(end_date, date_format)
        
        if start >= end:
            return {
                'valid': False,
                'error': 'Start date must be before end date'
            }
        
        # Check if range is reasonable
        duration_days = (end - start).days
        warnings = []
        
        if duration_days < 30:
            warnings.append('Date range is less than 30 days')
        elif duration_days > 400:
            warnings.append('Date range exceeds 400 days')
        
        return {
            'valid': True,
            'duration_days': duration_days,
            'warnings': warnings
        }
        
    except ValueError as e:
        return {
            'valid': False,
            'error': f'Invalid date format: {str(e)}'
        }

class DataValidator:
    """Comprehensive data validation class"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_gl_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Comprehensive GL data quality validation"""
        issues = []
        warnings = []
        stats = {}
        
        # Basic statistics
        stats['total_rows'] = len(df)
        stats['total_amount'] = df['Amount'].sum() if 'Amount' in df.columns else 0
        
        # Check for missing values
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                missing_pct = (missing_count / len(df)) * 100
                if missing_pct > 10:
                    issues.append(f'{col}: {missing_pct:.1f}% missing values')
                elif missing_pct > 5:
                    warnings.append(f'{col}: {missing_pct:.1f}% missing values')
        
        # Check for outliers in amounts
        if 'Amount' in df.columns:
            amounts = df['Amount'].dropna()
            if len(amounts) > 0:
                q75, q25 = amounts.quantile([0.75, 0.25])
                iqr = q75 - q25
                outlier_threshold = q75 + 1.5 * iqr
                outliers = amounts[amounts > outlier_threshold]
                
                if len(outliers) > 0:
                    warnings.append(f'{len(outliers)} potential outliers in amounts (>{outlier_threshold:,.2f})')
        
        # Check for duplicate entries
        if 'Reference' in df.columns:
            duplicates = df[df['Reference'].notna()].duplicated(subset=['Account Code', 'Amount', 'Reference'])
            if duplicates.any():
                issues.append(f'{duplicates.sum()} potential duplicate entries found')
        
        return {
            'issues': issues,
            'warnings': warnings,
            'stats': stats,
            'quality_score': max(0, 100 - len(issues) * 10 - len(warnings) * 5)
        }

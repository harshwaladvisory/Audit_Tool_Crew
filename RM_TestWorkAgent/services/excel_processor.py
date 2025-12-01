import os
import pandas as pd
import openpyxl
from typing import Dict, Any
from models import GLPopulation, TBMapping, Run, db
import logging

class ExcelProcessor:
    """Handle Excel file processing and validation"""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.logger = logging.getLogger(__name__)
    
    def process_gl_population(self, file, run_id: int) -> Dict[str, Any]:
        """Process GL Population Excel file"""
        try:
            # Read Excel file
            df = pd.read_excel(file, engine='openpyxl')
            
            # Validate required columns
            required_columns = ['Account Code', 'Account Name', 'Description', 'Amount']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    'success': False,
                    'error': f'Missing required columns: {", ".join(missing_columns)}'
                }
            
            # Process each row
            records_processed = 0
            
            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('Account Code')) and pd.isna(row.get('Amount')):
                        continue
                    
                    gl_record = GLPopulation(
                        run_id=run_id,
                        account_code=str(row.get('Account Code', '')).strip(),
                        account_name=str(row.get('Account Name', '')).strip(),
                        description=str(row.get('Description', '')).strip(),
                        amount=float(row.get('Amount', 0)) if pd.notna(row.get('Amount')) else 0,
                        date=str(row.get('Date', '')).strip(),
                        reference=str(row.get('Reference', '')).strip(),
                        vendor_name=str(row.get('Vendor Name', '')).strip(),
                        row_number=index + 2  # Excel row number (header is row 1)
                    )
                    
                    db.session.add(gl_record)
                    records_processed += 1
                    
                except Exception as e:
                    self.logger.warning(f'Error processing GL row {index + 2}: {str(e)}')
                    continue
            
            db.session.commit()
            
            return {
                'success': True,
                'count': records_processed,
                'message': f'Processed {records_processed} GL records'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f'GL processing error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_tb_mapping(self, file, run_id: int) -> Dict[str, Any]:
        """Process Trial Balance Mapping Excel file"""
        try:
            # Read Excel file
            df = pd.read_excel(file, engine='openpyxl')
            
            # Validate required columns
            required_columns = ['Account Code', 'Account Name', 'TB Amount']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    'success': False,
                    'error': f'Missing required columns: {", ".join(missing_columns)}'
                }
            
            # Process each row
            records_processed = 0
            
            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('Account Code')) and pd.isna(row.get('TB Amount')):
                        continue
                    
                    tb_record = TBMapping(
                        run_id=run_id,
                        account_code=str(row.get('Account Code', '')).strip(),
                        account_name=str(row.get('Account Name', '')).strip(),
                        tb_amount=float(row.get('TB Amount', 0)) if pd.notna(row.get('TB Amount')) else 0
                    )
                    
                    db.session.add(tb_record)
                    records_processed += 1
                    
                except Exception as e:
                    self.logger.warning(f'Error processing TB row {index + 2}: {str(e)}')
                    continue
            
            db.session.commit()
            
            return {
                'success': True,
                'count': records_processed,
                'message': f'Processed {records_processed} TB records'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f'TB processing error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_config(self, file, run_id: int) -> Dict[str, Any]:
        """Process Configuration Excel file"""
        try:
            # Read Excel file
            df = pd.read_excel(file, engine='openpyxl')
            
            # Look for configuration parameters
            run = Run.query.get(run_id)
            if not run:
                return {'success': False, 'error': 'Run not found'}
            
            config_updates = {}
            
            # Process configuration rows
            for index, row in df.iterrows():
                param_name = str(row.get('Parameter', '')).strip().lower()
                param_value = row.get('Value')
                
                if param_name == 'capitalization_threshold' and pd.notna(param_value):
                    run.capitalization_threshold = float(param_value)
                    config_updates['capitalization_threshold'] = param_value
                elif param_name == 'materiality' and pd.notna(param_value):
                    run.materiality = float(param_value)
                    config_updates['materiality'] = param_value
                elif param_name == 'fy_start' and pd.notna(param_value):
                    run.fy_start = str(param_value).strip()
                    config_updates['fy_start'] = param_value
                elif param_name == 'fy_end' and pd.notna(param_value):
                    run.fy_end = str(param_value).strip()
                    config_updates['fy_end'] = param_value
                elif param_name == 'allowed_accounts' and pd.notna(param_value):
                    run.allowed_accounts = str(param_value).strip()
                    config_updates['allowed_accounts'] = param_value
            
            if config_updates:
                db.session.commit()
                return {
                    'success': True,
                    'updates': config_updates,
                    'message': f'Updated {len(config_updates)} configuration parameters'
                }
            else:
                return {
                    'success': True,
                    'message': 'No valid configuration parameters found'
                }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f'Config processing error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_excel_structure(self, file_path: str, required_columns: list) -> Dict[str, Any]:
        """Validate Excel file structure"""
        try:
            # Read just the header
            df = pd.read_excel(file_path, nrows=0)
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            extra_columns = [col for col in df.columns if col not in required_columns]
            
            return {
                'valid': len(missing_columns) == 0,
                'missing_columns': missing_columns,
                'extra_columns': extra_columns,
                'total_columns': len(df.columns)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def get_excel_preview(self, file, max_rows: int = 5) -> Dict[str, Any]:
        """Get preview of Excel file data"""
        try:
            df = pd.read_excel(file, nrows=max_rows, engine='openpyxl')
            
            # Convert to JSON-serializable format
            preview_data = []
            for index, row in df.iterrows():
                row_data = {}
                for col in df.columns:
                    value = row[col]
                    if pd.isna(value):
                        row_data[col] = None
                    elif isinstance(value, (int, float)):
                        row_data[col] = value
                    else:
                        row_data[col] = str(value)
                preview_data.append(row_data)
            
            return {
                'success': True,
                'columns': list(df.columns),
                'rows': preview_data,
                'total_columns': len(df.columns)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

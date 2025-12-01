import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional

class ExcelProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_file(self, file_path: str, file_type: str, fiscal_year_end: datetime.date) -> List[Dict[str, Any]]:
        """
        Process Excel file and extract transaction data
        """
        try:
            self.logger.info(f"Processing {file_type} file: {file_path}")
            
            # Check if file exists
            import os
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File does not exist: {file_path}")
            
            self.logger.info(f"File exists, size: {os.path.getsize(file_path)} bytes")
            
            # ALWAYS try to detect fiscal year end from file first
            detected_fye = self._detect_fiscal_year_end(file_path, file_type)
            if detected_fye:
                fiscal_year_end = detected_fye
                self.logger.info(f"*** AUTO-DETECTED FISCAL YEAR END FROM FILE: {fiscal_year_end} ***")
            else:
                self.logger.warning(f"!!! Could not auto-detect fiscal year end, using provided date: {fiscal_year_end} !!!")
            
            # Determine which sheet to use
            try:
                if file_type == 'check_register':
                    try:
                        df = pd.read_excel(file_path, sheet_name='Formatted', header=None)
                        self.logger.info("Using 'Formatted' sheet")
                    except Exception as e:
                        self.logger.warning(f"Could not find 'Formatted' sheet: {e}, using default sheet")
                        df = pd.read_excel(file_path, header=None)
                        self.logger.info("Using default sheet")
                else:
                    df = pd.read_excel(file_path, header=None)
                    self.logger.info("Using default sheet")
            except Exception as e:
                raise Exception(f"Failed to read Excel file: {str(e)}. Please ensure the file is a valid Excel file (.xlsx or .xls)")
            
            self.logger.info(f"File loaded with {len(df)} rows and {len(df.columns)} columns")
            
            if len(df) == 0:
                raise ValueError("The Excel file is empty (0 rows)")
            
            # Find the header row
            header_row = self._find_header_row(df)
            self.logger.info(f"Found header row at index: {header_row}")
            
            # Get the headers and clean them
            headers = df.iloc[header_row].tolist()
            
            # Clean headers
            clean_headers = []
            for i, h in enumerate(headers):
                if pd.isna(h) or h == '' or not isinstance(h, str):
                    clean_headers.append(f'Unnamed_{i}')
                else:
                    clean_headers.append(str(h).strip())
            
            self.logger.info(f"Clean headers: {clean_headers}")
            
            # Create new dataframe with data rows only
            df_data = df.iloc[header_row + 1:].copy()
            df_data.columns = clean_headers
            
            # Remove any completely empty rows
            df_data = df_data.dropna(how='all')
            
            self.logger.info(f"Data has {len(df_data)} rows after removing empty rows")
            
            if len(df_data) == 0:
                raise ValueError("No data rows found in the Excel file after removing empty rows")
            
            if file_type == 'check_register':
                transactions = self._process_check_register(df_data, fiscal_year_end)
            elif file_type == 'subsequent_gl':
                transactions = self._process_subsequent_gl(df_data, fiscal_year_end)
            else:
                raise ValueError(f"Unknown file type: {file_type}")
            
            self.logger.info(f"Extracted {len(transactions)} valid transactions from {file_type}")
            
            if len(transactions) == 0:
                raise ValueError(f"No valid transactions found in the date range. Please check the fiscal year end date ({fiscal_year_end}) and ensure your file contains transactions in the 3 months following that date.")
            
            return transactions
                
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
            raise Exception(f"Failed to process {file_type}: {str(e)}")
    
    def _detect_fiscal_year_end(self, file_path: str, file_type: str) -> Optional[datetime.date]:
        """
        Try to detect fiscal year end date from the Excel file metadata rows
        Search ALL columns in the first 10 rows for "Fiscal year end:"
        """
        try:
            # Read first few rows without header
            if file_type == 'check_register':
                try:
                    df = pd.read_excel(file_path, sheet_name='Formatted', header=None, nrows=10)
                except:
                    df = pd.read_excel(file_path, header=None, nrows=10)
            else:
                df = pd.read_excel(file_path, header=None, nrows=10)
            
            self.logger.info("Searching for 'Fiscal year end:' in first 10 rows...")
            
            # Look for "Fiscal year end:" in ANY column of first few rows
            for idx, row in df.iterrows():
                for col_idx in range(len(row)):
                    cell_value = str(row[col_idx]).lower().strip() if pd.notna(row[col_idx]) else ''
                    
                    if 'fiscal year end' in cell_value:
                        self.logger.info(f"Found 'Fiscal year end' text at row {idx}, column {col_idx}")
                        
                        # Try to get the date from adjacent columns (same row)
                        for next_col in range(col_idx + 1, len(row)):
                            date_val = row[next_col]
                            if pd.notna(date_val):
                                try:
                                    # Try to parse as date
                                    fye_date = pd.to_datetime(date_val)
                                    self.logger.info(f"Successfully parsed fiscal year end date: {fye_date.date()}")
                                    return fye_date.date()
                                except:
                                    # Try to parse as string
                                    try:
                                        fye_date = pd.to_datetime(str(date_val))
                                        self.logger.info(f"Successfully parsed fiscal year end date: {fye_date.date()}")
                                        return fye_date.date()
                                    except:
                                        continue
            
            self.logger.warning("Could not find fiscal year end in file")
            return None
            
        except Exception as e:
            self.logger.warning(f"Could not auto-detect fiscal year end: {str(e)}")
            return None
    
    def _find_header_row(self, df: pd.DataFrame) -> int:
        """
        Find the row index that contains the actual column headers
        """
        for i in range(min(20, len(df))):
            row = df.iloc[i]
            
            # Convert row to strings for checking
            row_strings = [str(val).lower() if pd.notna(val) else '' for val in row]
            
            # Check if this looks like a header row
            header_keywords = ['date', 'amount', 'vendor', 'name', 'id', 'description', 
                              'document', 'account', 'transaction', 'effective', 'fund']
            
            # Count how many header keywords we find
            keyword_count = sum(1 for s in row_strings if any(keyword in s for keyword in header_keywords))
            
            # Need at least 3 header keywords to consider this a header row
            if keyword_count >= 3:
                self.logger.info(f"Found header row at {i} with keywords: {[s for s in row_strings if s and any(kw in s for kw in header_keywords)]}")
                return i
        
        self.logger.warning("Could not find header row, using row 0")
        return 0
    
    def _process_check_register(self, df: pd.DataFrame, fiscal_year_end: datetime.date) -> List[Dict[str, Any]]:
        """
        Process Check Register file
        """
        transactions = []
        
        self.logger.info(f"Check register columns: {list(df.columns)}")
        
        # Find columns by exact matching first, then partial matching
        date_col = None
        vendor_col = None
        amount_col = None
        check_col = None
        desc_col = None
        
        # First pass: exact matches
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            if col_lower == 'document date':
                date_col = col
            elif col_lower == 'id':
                vendor_col = col
            elif col_lower == 'amount':
                amount_col = col
            elif col_lower == 'document number':
                check_col = col
            elif col_lower == 'fund description':
                desc_col = col
        
        # Second pass: partial matches for any missing columns
        if not date_col or not vendor_col or not amount_col:
            for col in df.columns:
                col_lower = str(col).lower().strip()
                
                if not date_col and 'date' in col_lower and 'unnamed' not in col_lower:
                    date_col = col
                elif not vendor_col and col_lower == 'id':
                    vendor_col = col
                elif not amount_col and 'amount' in col_lower and 'unnamed' not in col_lower:
                    amount_col = col
        
        self.logger.info(f"Mapped columns - Date: {date_col}, Vendor: {vendor_col}, Amount: {amount_col}, Check: {check_col}, Desc: {desc_col}")
        
        if date_col is None:
            raise ValueError(f"Could not find date column in Check Register. Available columns: {list(df.columns)}")
        
        if amount_col is None:
            raise ValueError(f"Could not find amount column in Check Register. Available columns: {list(df.columns)}")
        
        # Calculate date range (3 months after fiscal year end)
        start_date = fiscal_year_end + timedelta(days=1)
        end_date = start_date + timedelta(days=90)
        
        self.logger.info(f"*** SEARCHING FOR TRANSACTIONS BETWEEN {start_date} AND {end_date} ***")
        
        skipped = {'date_error': 0, 'out_of_range': 0, 'invalid_amount': 0}
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                trans_date = pd.to_datetime(row[date_col], errors='coerce')
                if pd.isna(trans_date):
                    skipped['date_error'] += 1
                    continue
                
                trans_date = trans_date.date()
                
                # Check date range
                if not (start_date <= trans_date <= end_date):
                    skipped['out_of_range'] += 1
                    continue
                
                # Parse amount
                amount_val = row[amount_col]
                if pd.isna(amount_val):
                    skipped['invalid_amount'] += 1
                    continue
                
                try:
                    amount = abs(float(amount_val))
                    if amount <= 0:
                        skipped['invalid_amount'] += 1
                        continue
                except:
                    skipped['invalid_amount'] += 1
                    continue
                
                # Extract other fields
                vendor_name = str(row[vendor_col]).strip() if vendor_col and pd.notna(row[vendor_col]) else ''
                check_number = str(row[check_col]).strip() if check_col and pd.notna(row[check_col]) else ''
                description = str(row[desc_col]).strip() if desc_col and pd.notna(row[desc_col]) else ''
                
                sample_month = self._get_sample_month(trans_date, start_date)
                
                transaction = {
                    'transaction_date': trans_date,
                    'vendor_name': vendor_name,
                    'amount': amount,
                    'description': description,
                    'check_number': check_number,
                    'payment_type': 'check',
                    'sample_month': sample_month,
                    'is_sampled': False
                }
                
                transactions.append(transaction)
                
            except Exception as e:
                self.logger.warning(f"Error processing row {idx}: {str(e)}")
                continue
        
        self.logger.info(f"Skipped - Date errors: {skipped['date_error']}, "
                        f"Out of range: {skipped['out_of_range']}, Invalid amount: {skipped['invalid_amount']}")
        
        transactions.sort(key=lambda x: x['amount'], reverse=True)
        return transactions
    
    def _process_subsequent_gl(self, df: pd.DataFrame, fiscal_year_end: datetime.date) -> List[Dict[str, Any]]:
        """
        Process Subsequent General Ledger file
        """
        transactions = []
        
        self.logger.info(f"GL columns: {list(df.columns)}")
        
        # Find columns by exact matching
        date_col = None
        vendor_col = None
        amount_col = None
        account_col = None
        desc_col = None
        
        # First pass: exact matches for GL columns
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            if col_lower == 'effective date':
                date_col = col
            elif col_lower == 'name':
                vendor_col = col
            elif col_lower == 'amount':
                amount_col = col
            elif col_lower == 'account code':
                account_col = col
            elif col_lower == 'transaction description':
                desc_col = col
        
        # Second pass: partial matches for missing columns
        if not date_col or not amount_col:
            for col in df.columns:
                col_lower = str(col).lower().strip()
                
                if not date_col and 'date' in col_lower and 'unnamed' not in col_lower:
                    date_col = col
                elif not amount_col and col_lower == 'amount':
                    amount_col = col
                elif not vendor_col and col_lower == 'name':
                    vendor_col = col
        
        self.logger.info(f"Mapped GL columns - Date: {date_col}, Vendor: {vendor_col}, Amount: {amount_col}, Account: {account_col}, Desc: {desc_col}")
        
        if date_col is None:
            raise ValueError(f"Could not find date column in GL file. Available columns: {list(df.columns)}")
        
        if amount_col is None:
            raise ValueError(f"Could not find amount column in GL file. Available columns: {list(df.columns)}")
        
        # Calculate date range
        start_date = fiscal_year_end + timedelta(days=1)
        end_date = start_date + timedelta(days=90)
        
        self.logger.info(f"*** SEARCHING FOR GL TRANSACTIONS BETWEEN {start_date} AND {end_date} ***")
        
        skipped = {'date_error': 0, 'out_of_range': 0, 'invalid_amount': 0, 'cash_transfer': 0}
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                trans_date = pd.to_datetime(row[date_col], errors='coerce')
                if pd.isna(trans_date):
                    skipped['date_error'] += 1
                    continue
                
                trans_date = trans_date.date()
                
                # Check date range
                if not (start_date <= trans_date <= end_date):
                    skipped['out_of_range'] += 1
                    continue
                
                # Parse amount
                amount_val = row[amount_col]
                if pd.isna(amount_val):
                    skipped['invalid_amount'] += 1
                    continue
                
                try:
                    amount = abs(float(amount_val))
                    if amount <= 0:
                        skipped['invalid_amount'] += 1
                        continue
                except:
                    skipped['invalid_amount'] += 1
                    continue
                
                # Check account code for cash accounts
                account_code = str(row[account_col]).lower() if account_col and pd.notna(row[account_col]) else ''
                if any(x in account_code for x in ['1005', 'cash', 'bank', 'money market', 'checking']):
                    skipped['cash_transfer'] += 1
                    continue
                
                # Check description for transfers
                description = str(row[desc_col]).lower() if desc_col and pd.notna(row[desc_col]) else ''
                if 'transfer from' in description or 'transfer to' in description or 'opening balance' in description:
                    skipped['cash_transfer'] += 1
                    continue
                
                # Extract vendor
                vendor_name = str(row[vendor_col]).strip() if vendor_col and pd.notna(row[vendor_col]) else ''
                
                # Determine payment type
                payment_type = 'other'
                if 'bill pmt' in description:
                    payment_type = 'bill_payment'
                elif 'check' in description:
                    payment_type = 'check'
                
                sample_month = self._get_sample_month(trans_date, start_date)
                
                transaction = {
                    'transaction_date': trans_date,
                    'vendor_name': vendor_name,
                    'amount': amount,
                    'description': description,
                    'account_code': account_code,
                    'payment_type': payment_type,
                    'sample_month': sample_month,
                    'is_sampled': False
                }
                
                transactions.append(transaction)
                
            except Exception as e:
                self.logger.warning(f"Error processing row {idx}: {str(e)}")
                continue
        
        self.logger.info(f"Skipped - Date errors: {skipped['date_error']}, "
                        f"Out of range: {skipped['out_of_range']}, Invalid amount: {skipped['invalid_amount']}, "
                        f"Cash/transfers: {skipped['cash_transfer']}")
        
        transactions.sort(key=lambda x: x['amount'], reverse=True)
        return transactions
    
    def _get_sample_month(self, trans_date: datetime.date, start_date: datetime.date) -> int:
        """
        Determine which sample month (1, 2, or 3) the transaction falls into
        """
        days_diff = (trans_date - start_date).days
        
        if days_diff <= 30:
            return 1
        elif days_diff <= 60:
            return 2
        else:
            return 3
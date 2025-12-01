"""
File Processor Service for Securities Deposits Analysis
Handles Excel, CSV, and PDF file processing with robust error handling
"""

import os
import pandas as pd
import pdfplumber
from datetime import datetime
from typing import Dict, List, Any
import re


class FileProcessor:
    """Process uploaded files and extract deposit data"""
    
    # Column name mappings for flexible field recognition
    COLUMN_MAPPINGS = {
        'account_number': [
            'account number', 'account no', 'acct number', 'acct no',
            'account_number', 'accountnumber', 'certificate no',
            'certificate number', 'cert no', 'deposit id', 'id'
        ],
        'customer_name': [
            'customer name', 'customer', 'name', 'depositor',
            'account holder', 'holder name', 'depositor name'
        ],
        'deposit_type': [
            'deposit type', 'type', 'product type', 'account type',
            'product', 'deposit_type', 'category'
        ],
        'amount': [
            'amount', 'balance', 'principal', 'deposit amount',
            'principal amount', 'value', 'deposit value'
        ],
        'interest_rate': [
            'interest rate', 'rate', 'interest', 'apr', 'apy',
            'interest_rate', 'rate (%)', 'interest %'
        ],
        'deposit_date': [
            'deposit date', 'opening date', 'start date', 'date opened',
            'issue date', 'open date', 'date', 'effective date'
        ],
        'maturity_date': [
            'maturity date', 'maturity', 'end date', 'expiry date',
            'due date', 'expiration date', 'term date'
        ],
        'last_activity_date': [
            'last activity', 'last transaction', 'last activity date',
            'last transaction date', 'activity date'
        ],
        'branch_code': [
            'branch code', 'branch', 'branch id', 'location',
            'branch_code', 'office'
        ],
        'product_code': [
            'product code', 'product id', 'product_code', 'product'
        ]
    }
    
    def __init__(self):
        self.processed_records = 0
        self.errors = []
    
    def process_file(self, file_path: str, file_upload_id: str) -> Dict[str, Any]:
        """
        Process uploaded file based on extension
        
        Args:
            file_path: Path to uploaded file
            file_upload_id: MongoDB ID of FileUpload document
            
        Returns:
            Dictionary with processing results
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext in ['.xlsx', '.xls']:
                data = self._process_excel(file_path)
            elif file_ext == '.csv':
                data = self._process_csv(file_path)
            elif file_ext == '.pdf':
                data = self._process_pdf(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            # Save to database
            records_saved = self._save_to_database(data, file_upload_id)
            
            return {
                'status': 'success',
                'records_processed': records_saved,
                'errors': self.errors
            }
            
        except Exception as e:
            raise ValueError(f"File processing error: {str(e)}")
    
    def _process_excel(self, file_path: str) -> pd.DataFrame:
        """Process Excel files (.xlsx, .xls)"""
        try:
            # Try reading with openpyxl first
            df = pd.read_excel(file_path, engine='openpyxl')
        except Exception as e:
            # Fallback to xlrd for older .xls files
            try:
                df = pd.read_excel(file_path, engine='xlrd')
            except:
                raise ValueError(f"Cannot read Excel file: {str(e)}")
        
        # Normalize column names
        df = self._normalize_columns(df)
        
        # Clean and validate data
        df = self._clean_data(df)
        
        return df
    
    def _process_csv(self, file_path: str) -> pd.DataFrame:
        """Process CSV files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Cannot decode CSV file with any supported encoding")
            
            # Normalize column names
            df = self._normalize_columns(df)
            
            # Clean and validate data
            df = self._clean_data(df)
            
            return df
            
        except Exception as e:
            raise ValueError(f"CSV processing error: {str(e)}")
    
    def _process_pdf(self, file_path: str) -> pd.DataFrame:
        """
        Process PDF files - extracts tables from PDF
        Note: PDF processing is complex and may need customization based on PDF format
        """
        try:
            all_tables = []
            
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Extract tables from page
                    tables = page.extract_tables()
                    
                    if tables:
                        for table in tables:
                            if table and len(table) > 1:  # Has headers and data
                                # Convert table to DataFrame
                                df = pd.DataFrame(table[1:], columns=table[0])
                                all_tables.append(df)
                    
                    # If no tables found, try text extraction
                    if not tables:
                        text = page.extract_text()
                        if text:
                            # Try to parse structured text
                            parsed = self._parse_pdf_text(text)
                            if parsed:
                                all_tables.append(parsed)
            
            if not all_tables:
                raise ValueError("No data tables found in PDF")
            
            # Combine all tables
            df = pd.concat(all_tables, ignore_index=True)
            
            # Normalize column names
            df = self._normalize_columns(df)
            
            # Clean and validate data
            df = self._clean_data(df)
            
            # Set default values for PDF files
            if 'interest_rate' not in df.columns:
                df['interest_rate'] = 0.0  # PDFs typically don't have interest rates
            
            if 'deposit_type' not in df.columns:
                df['deposit_type'] = 'security_deposit'
            
            return df
            
        except Exception as e:
            raise ValueError(f"PDF processing error: {str(e)}")
    
    def _parse_pdf_text(self, text: str) -> pd.DataFrame:
        """
        Parse structured text from PDF when tables aren't detected
        This is a basic implementation - customize based on your PDF format
        """
        lines = text.split('\n')
        data = []
        
        # Try to find patterns in text
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Example pattern matching - customize based on your PDF format
            # Looking for: "Account: 12345  Name: John Doe  Amount: $1,000.00"
            match = re.search(r'(\d+)\s+([A-Za-z\s]+)\s+\$?([\d,]+\.?\d*)', line)
            if match:
                data.append({
                    'Account Number': match.group(1),
                    'Customer Name': match.group(2).strip(),
                    'Amount': match.group(3)
                })
        
        if data:
            return pd.DataFrame(data)
        return None
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard field names"""
        # Convert column names to lowercase and strip whitespace
        df.columns = df.columns.str.lower().str.strip()
        
        # Create mapping dictionary
        column_map = {}
        for col in df.columns:
            for standard_name, variations in self.COLUMN_MAPPINGS.items():
                if col in variations:
                    column_map[col] = standard_name
                    break
        
        # Rename columns
        df = df.rename(columns=column_map)
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate data"""
        # Remove empty rows
        df = df.dropna(how='all')
        
        # Clean amount field - remove currency symbols, commas
        if 'amount' in df.columns:
            df['amount'] = df['amount'].astype(str).str.replace('$', '').str.replace(',', '')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # Clean interest rate - convert percentage to decimal
        if 'interest_rate' in df.columns:
            df['interest_rate'] = df['interest_rate'].astype(str).str.replace('%', '')
            df['interest_rate'] = pd.to_numeric(df['interest_rate'], errors='coerce')
            # If values are > 1, assume they're percentages and convert to decimal
            df.loc[df['interest_rate'] > 1, 'interest_rate'] = df['interest_rate'] / 100
        
        # Parse dates
        date_columns = ['deposit_date', 'maturity_date', 'last_activity_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Fill missing required fields
        if 'account_number' not in df.columns:
            df['account_number'] = df.index.astype(str)
        
        if 'customer_name' not in df.columns:
            df['customer_name'] = 'Unknown'
        
        if 'deposit_type' not in df.columns:
            df['deposit_type'] = 'unknown'
        
        if 'amount' not in df.columns:
            df['amount'] = 0.0
        
        if 'deposit_date' not in df.columns:
            df['deposit_date'] = datetime.now()
        
        # Set defaults for optional fields
        if 'interest_rate' not in df.columns:
            df['interest_rate'] = 0.0
        
        return df
    
    def _save_to_database(self, df: pd.DataFrame, file_upload_id: str) -> int:
        """Save processed data to MongoDB"""
        from models import Deposit, FileUpload
        
        file_upload = FileUpload.objects(id=file_upload_id).first()
        if not file_upload:
            raise ValueError("FileUpload not found")
        
        records_saved = 0
        
        for idx, row in df.iterrows():
            try:
                # Create deposit record
                deposit = Deposit(
                    account_number=str(row.get('account_number', '')),
                    customer_name=str(row.get('customer_name', '')),
                    deposit_type=str(row.get('deposit_type', 'unknown')),
                    amount=float(row.get('amount', 0.0)),
                    interest_rate=float(row.get('interest_rate', 0.0)),
                    deposit_date=row.get('deposit_date'),
                    maturity_date=row.get('maturity_date'),
                    last_activity_date=row.get('last_activity_date'),
                    branch_code=str(row.get('branch_code', '')) if pd.notna(row.get('branch_code')) else None,
                    product_code=str(row.get('product_code', '')) if pd.notna(row.get('product_code')) else None,
                    status='active',
                    file_upload=file_upload
                )
                deposit.save()
                records_saved += 1
                
            except Exception as e:
                self.errors.append(f"Row {idx + 1}: {str(e)}")
                continue
        
        # Update file upload record
        file_upload.records_processed = records_saved
        file_upload.status = 'processed'
        file_upload.save()
        
        return records_saved
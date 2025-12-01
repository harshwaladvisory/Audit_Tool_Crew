import pandas as pd
import numpy as np
import logging
from datetime import datetime
import pdfplumber
import os

logger = logging.getLogger(__name__)

class JEProcessor:
    """Handles ingestion and validation of General Ledger data"""
    
    def __init__(self):
        self.required_columns = ['date', 'account', 'description', 'debit', 'credit']
        self.optional_columns = ['doc_no', 'session_id', 'user', 'type']
    
    def ingest_gl_files(self, file_paths):
        """
        Ingest multiple GL files and combine into single dataset
        Returns: DataFrame with standardized columns
        """
        all_data = []
        
        for file_path in file_paths:
            try:
                logger.info(f"Processing file: {file_path}")
                
                if file_path.lower().endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file_path.lower().endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                elif file_path.lower().endswith('.pdf'):
                    df = self._extract_from_pdf(file_path)
                else:
                    logger.warning(f"Unsupported file format: {file_path}")
                    continue
                
                # Standardize column names
                df = self._standardize_columns(df)
                
                # Add source file reference
                df['source_file'] = os.path.basename(file_path)
                
                if not df.empty:
                    all_data.append(df)
                    logger.info(f"Loaded {len(df)} records from {file_path}")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                continue
        
        if not all_data:
            logger.warning("No data loaded from any files")
            return pd.DataFrame()
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Validate and clean data
        combined_df = self._validate_and_clean(combined_df)
        
        logger.info(f"Total records loaded: {len(combined_df)}")
        return combined_df
    
    def _extract_from_pdf(self, file_path):
        """Extract tabular data from PDF files"""
        try:
            with pdfplumber.open(file_path) as pdf:
                all_tables = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    all_tables.extend(tables)
                
                if all_tables:
                    # Convert first table to DataFrame (assuming header in first row)
                    df = pd.DataFrame(all_tables[0][1:], columns=all_tables[0][0])
                    return df
                else:
                    logger.warning(f"No tables found in PDF: {file_path}")
                    return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error extracting PDF {file_path}: {str(e)}")
            return pd.DataFrame()
    
    def _standardize_columns(self, df):
        """Standardize column names to match expected schema"""
        # Print original columns for debugging
        logger.info(f"Original columns: {df.columns.tolist()}")

        # Common column mapping variations
        column_mapping = {
            # Date variations
            'date': 'date',
            'transaction_date': 'date',
            'transaction date': 'date',
            'trans_date': 'date',
            'trans date': 'date',
            'posting_date': 'date',
            'posting date': 'date',
            'entry_date': 'date',
            'entry date': 'date',
            
            # Account variations - Use DISTRIBUTION ACCOUNT NUMBER as primary
            'account': 'account',
            'account_code': 'account',
            'account code': 'account',
            'account_number': 'account',
            'account number': 'account',
            'gl_account': 'account',
            'gl account': 'account',
            'distribution_account_number': 'account',
            'distribution account number': 'account',
            # Keep full name separate
            'account_full_name': 'account_name',
            'account full name': 'account_name',
            
            # Description variations - LINE DESCRIPTION goes here
            'description': 'description',
            'memo': 'description',
            'narrative': 'description',
            'reference': 'description',
            'line_description': 'description',
            'line description': 'description',
            
            # Amount variations
            'debit': 'debit',
            'dr': 'debit',
            'debit_amount': 'debit',
            'debit amount': 'debit',
            'credit': 'credit',
            'cr': 'credit',
            'credit_amount': 'credit',
            'credit amount': 'credit',
            
            # Document number variations
            'doc_no': 'doc_no',
            'document_number': 'doc_no',
            'document number': 'doc_no',
            'doc_num': 'doc_no',
            'transaction_no.': 'doc_no',
            'transaction no.': 'doc_no',
            'num': 'doc_no',
            
            # User variations
            'user': 'user',
            'created_by': 'user',
            'created by': 'user',
            'entered_by': 'user',
            'name': 'user',
            
            # Type variations - TRANSACTION TYPE goes here (NOT to description!)
            'type': 'type',
            'entry_type': 'type',
            'entry type': 'type',
            'transaction_type': 'type',
            'transaction type': 'type',
            'je_type': 'type'
        }
        
        # Convert column names to lowercase for matching
        df.columns = df.columns.str.lower().str.strip()

        logger.info(f"Lowercase columns: {df.columns.tolist()}")
        
        # Apply mapping
        df = df.rename(columns=column_mapping)

        logger.info(f"After mapping columns: {df.columns.tolist()}")

        # Check for duplicate columns and handle them
        if df.columns.duplicated().any():
            logger.warning(f"Duplicate columns detected: {df.columns[df.columns.duplicated()].tolist()}")
            # Keep only the first occurrence of each duplicate
            df = df.loc[:, ~df.columns.duplicated()]
            logger.info(f"After removing duplicates: {df.columns.tolist()}")
        
        return df
    
    def _validate_and_clean(self, df):
        """Validate required columns and clean data"""
        # Check for required columns
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols:
            logger.warning(f"Missing required columns: {missing_cols}")
        
        # Add missing optional columns with defaults
        for col in self.optional_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Convert date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Convert amount columns to numeric
        for col in ['debit', 'credit']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Calculate net amount
        if 'debit' in df.columns and 'credit' in df.columns:
            df['net'] = df['debit'] - df['credit']
        
        # Add unique JE ID
        df['je_id'] = df.index.astype(str).str.zfill(6)
        
        # Remove rows with invalid dates or missing critical data
        df = df.dropna(subset=['date'])
        
        # Filter for journal entries (exclude regular transactions)
        je_indicators = self._identify_journal_entries(df)
        df = df[je_indicators]
        
        logger.info(f"After validation and filtering: {len(df)} journal entries")
        return df
    
    def _identify_journal_entries(self, df):
        """Identify rows that appear to be journal entries vs regular transactions"""
        je_indicators = pd.Series(False, index=df.index)
        
        # Look for JE indicators in description/memo field
        if 'description' in df.columns:
            try:
                # Make sure it's a Series and handle NaN values
                desc_series = df['description'].astype(str)
                je_keywords = ['adjusting', 'adjustment', 'reversal', 'correction', 'year-end', 'je', 'journal']
                pattern = '|'.join(je_keywords)
                je_indicators |= desc_series.str.contains(pattern, case=False, na=False)
            except Exception as e:
                logger.warning(f"Could not check description column: {str(e)}")
        
        # Look for JE indicators in type field
        if 'type' in df.columns:
            try:
                type_series = df['type'].astype(str).str.upper()
                je_types = ['GJ', 'JV', 'AJE', 'JE', 'ADJ', 'JOURNAL ENTRY']
                je_indicators |= type_series.isin(je_types)
            except Exception as e:
                logger.warning(f"Could not check type column: {str(e)}")
        
        # Look for JE indicators in document number
        if 'doc_no' in df.columns:
            try:
                doc_series = df['doc_no'].astype(str)
                je_indicators |= doc_series.str.contains('JE|GJ|JV|ADJ', case=False, na=False)
            except Exception as e:
                logger.warning(f"Could not check doc_no column: {str(e)}")
        
        # If no specific indicators found, assume all entries are JEs
        if not je_indicators.any():
            logger.info("No JE indicators found, treating all entries as journal entries")
            je_indicators = pd.Series(True, index=df.index)
        
        return je_indicators

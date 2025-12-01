import pandas as pd
import os
from datetime import datetime
from decimal import Decimal
from bson import ObjectId
from models import GeneralLedger, TrialBalance, Invoice
import re


def process_uploaded_file(file_upload_id, filepath, file_type):
    """
    Process uploaded Excel, CSV, or PDF file and store data in MongoDB
    Returns the number of records processed
    """
    try:
        file_ext = os.path.splitext(filepath)[1].lower()
        print(f"Processing file: {os.path.basename(filepath)} (Extension: {file_ext}, Type: {file_type})")
        
        if file_ext == '.pdf':
            try:
                import pdfplumber
                df = read_pdf_file(filepath, file_type)
            except ImportError:
                raise ValueError("PDF processing requires pdfplumber. Install: pip install pdfplumber")
        elif file_ext == '.csv':
            df = pd.read_csv(filepath)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(filepath, engine='openpyxl' if file_ext == '.xlsx' else None)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_').str.replace('/', '_')
        
        print(f"Available columns: {list(df.columns)}")
        
        records_count = 0
        
        if file_type == 'GL':
            records_count = process_general_ledger(df, file_upload_id)
        elif file_type == 'TB':
            records_count = process_trial_balance(df, file_upload_id)
        elif file_type == 'INVOICE':
            records_count = process_invoices(df, file_upload_id)
        else:
            raise ValueError(f"Unknown file type: {file_type}")
        
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return records_count
        
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise e


def read_pdf_file(filepath, file_type):
    """Extract data from PDF file with improved invoice handling"""
    import pdfplumber
    
    print(f"📄 Processing PDF for {file_type}...")
    
    with pdfplumber.open(filepath) as pdf:
        all_text = ""
        all_tables = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"  📖 Page {page_num}...")
            
            # Extract text
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"
            
            # Extract tables
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    if table and len(table) > 0:
                        all_tables.append(table)
        
        print(f"  ✓ Found {len(all_tables)} tables in PDF")
        
        # For invoices, try multiple extraction methods
        if file_type == 'INVOICE':
            return extract_invoice_data(all_text, all_tables, filepath)
        else:
            # For GL/TB, use table extraction
            if not all_tables:
                raise ValueError("No tables found in PDF. For GL/TB, please upload Excel/CSV format.")
            
            table = all_tables[0]
            df = pd.DataFrame(table[1:], columns=table[0])
            print(f"  ✓ Extracted {len(df)} rows")
            return df


def extract_invoice_data(text, tables, filepath):
    """Extract invoice data using multiple methods"""
    print("  🔍 Extracting invoice information...")
    
    # Method 1: Try to use tables if available
    if tables:
        for table in tables:
            df = try_table_as_invoice(table)
            if df is not None:
                print(f"  ✓ Extracted invoice from table format")
                return df
    
    # Method 2: Extract from text using patterns
    invoice_data = extract_invoice_from_text(text)
    if invoice_data:
        df = pd.DataFrame([invoice_data])
        print(f"  ✓ Extracted invoice from text: {invoice_data['invoice_number']}")
        return df
    
    # Method 3: Create manual entry from filename
    print("  ⚠ Could not auto-extract invoice details")
    filename = os.path.basename(filepath)
    
    # Try to extract any numbers from filename as invoice number
    invoice_num = re.search(r'(\d+)', filename)
    invoice_number = invoice_num.group(1) if invoice_num else filename.replace('.pdf', '')
    
    # Try to find any dollar amount in the text
    amounts = re.findall(r'\$[\d,]+\.?\d*', text)
    amount = amounts[-1] if amounts else '$0.00'  # Use last amount found (usually total)
    
    # Try to find any date
    dates = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    date = dates[0] if dates else datetime.now().strftime('%m/%d/%Y')
    
    data = {
        'invoice_number': invoice_number,
        'date': date,
        'amount': amount.replace('$', '').replace(',', ''),
        'category': 'Manual Entry - Please Review'
    }
    
    print(f"  ℹ Created manual entry: Invoice #{data['invoice_number']}, Amount: {data['amount']}")
    return pd.DataFrame([data])


def try_table_as_invoice(table):
    """Try to interpret a table as invoice line items"""
    if not table or len(table) < 2:
        return None
    
    df = pd.DataFrame(table[1:], columns=table[0])
    df.columns = df.columns.str.strip().str.lower()
    
    # Check if table looks like invoice items (has amount/description columns)
    has_amount = any('amount' in str(col).lower() or 'total' in str(col).lower() or 'due' in str(col).lower() for col in df.columns)
    has_description = any('description' in str(col).lower() or 'item' in str(col).lower() for col in df.columns)
    
    if has_amount and has_description:
        # This looks like line items - extract as separate invoices
        invoice_data = []
        for idx, row in df.iterrows():
            # Find amount column
            amount_col = next((col for col in df.columns if 'amount' in str(col).lower() or 'total' in str(col).lower()), None)
            desc_col = next((col for col in df.columns if 'description' in str(col).lower() or 'item' in str(col).lower()), None)
            
            if amount_col and desc_col and pd.notna(row[amount_col]):
                invoice_data.append({
                    'invoice_number': f"Line-{idx+1}",
                    'date': datetime.now().strftime('%m/%d/%Y'),
                    'amount': str(row[amount_col]).replace('$', '').replace(',', ''),
                    'category': str(row[desc_col])
                })
        
        if invoice_data:
            return pd.DataFrame(invoice_data)
    
    return None


def extract_invoice_from_text(text):
    """Extract invoice details from text using regex patterns"""
    
    # Pattern library for various invoice formats
    patterns = {
        'invoice_number': [
            r'invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
            r'invoice\s*number\s*:?\s*([A-Z0-9-]+)',
            r'inv\s*#?\s*:?\s*([A-Z0-9-]+)',
            r'#\s*([A-Z0-9]{5,})',
        ],
        'date': [
            r'invoice\s*date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        ],
        'amount': [
            r'total.*?\$\s*([\d,]+\.?\d{0,2})',
            r'amount\s*due.*?\$\s*([\d,]+\.?\d{0,2})',
            r'balance.*?\$\s*([\d,]+\.?\d{0,2})',
            r'grand\s*total.*?\$\s*([\d,]+\.?\d{0,2})',
            r'\$\s*([\d,]+\.?\d{0,2})\s*(?:total|due)',
        ]
    }
    
    extracted = {}
    
    # Try each pattern type
    for field, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted[field] = match.group(1)
                break
    
    # Must have at least invoice number and amount
    if 'invoice_number' in extracted and 'amount' in extracted:
        return {
            'invoice_number': extracted['invoice_number'],
            'date': extracted.get('date', datetime.now().strftime('%m/%d/%Y')),
            'amount': extracted['amount'].replace(',', ''),
            'category': 'Extracted from PDF'
        }
    
    return None


def clean_amount(value):
    """Clean and convert amount string to Decimal"""
    if pd.isna(value):
        return Decimal('0')
    
    amount_str = str(value).strip()
    amount_str = amount_str.replace(',', '').replace('$', '').replace('₹', '')
    
    if '(' in amount_str and ')' in amount_str:
        amount_str = '-' + amount_str.replace('(', '').replace(')', '')
    
    amount_str = amount_str.strip()
    
    try:
        return Decimal(amount_str)
    except:
        return Decimal('0')


def find_column(df, possible_names):
    """Find a column by checking multiple possible names"""
    for col in df.columns:
        for name in possible_names:
            if name in col:
                return col
    return None


def process_general_ledger(df, file_upload_id):
    """Process General Ledger data"""
    account_number_col = find_column(df, [
        'account_code', 'account_number', 'account_no', 'acct_no', 
        'acc_no', 'code', 'number', 'account_no.'
    ])
    
    account_name_col = find_column(df, [
        'account_details', 'account_name', 'account_description', 
        'description', 'name', 'details'
    ])
    
    balance_col = find_column(df, [
        'ending_balance', 'balance', 'amount', 'debit', 'credit', 
        'bal', 'end_balance', 'closing_balance'
    ])
    
    if not account_number_col:
        raise ValueError(f"Could not find Account Number. Available: {list(df.columns)}")
    if not account_name_col:
        raise ValueError(f"Could not find Account Name. Available: {list(df.columns)}")
    if not balance_col:
        raise ValueError(f"Could not find Balance. Available: {list(df.columns)}")
    
    print(f"✓ Columns - Number: '{account_number_col}', Name: '{account_name_col}', Balance: '{balance_col}'")
    
    prepaid_mask = (
        df[account_number_col].astype(str).str.startswith('1') |
        df[account_name_col].astype(str).str.contains('prepaid', case=False, na=False) |
        df[account_name_col].astype(str).str.contains('deferred', case=False, na=False)
    )
    
    prepaid_df = df[prepaid_mask].copy()
    
    if len(prepaid_df) == 0:
        print("⚠ No prepaid accounts found. Processing all rows.")
        prepaid_df = df.copy()
    
    records_count = 0
    for _, row in prepaid_df.iterrows():
        try:
            if pd.isna(row[account_number_col]) or str(row[account_number_col]).strip() == '':
                continue
                
            balance = clean_amount(row[balance_col])
            
            gl_entry = GeneralLedger(
                account_number=str(row[account_number_col]).strip(),
                account_name=str(row[account_name_col]).strip() if pd.notna(row[account_name_col]) else '',
                balance=balance,
                file_upload_id=ObjectId(file_upload_id)
            )
            gl_entry.save()
            records_count += 1
            
        except Exception as e:
            print(f"⚠ Skipping row: {e}")
            continue
    
    print(f"✓ Imported {records_count} GL records")
    return records_count


def process_trial_balance(df, file_upload_id):
    """Process Trial Balance data"""
    account_number_col = find_column(df, [
        'account_code', 'account_number', 'account_no', 'acct_no', 
        'acc_no', 'code', 'number', 'account_no.'
    ])
    
    account_name_col = find_column(df, [
        'account_details', 'account_name', 'account_description', 
        'description', 'name', 'details'
    ])
    
    balance_col = find_column(df, [
        'ending_balance', 'balance', 'amount', 'debit', 'credit', 
        'bal', 'end_balance', 'closing_balance'
    ])
    
    if not account_number_col:
        raise ValueError(f"Could not find Account Number. Available: {list(df.columns)}")
    if not account_name_col:
        raise ValueError(f"Could not find Account Name. Available: {list(df.columns)}")
    if not balance_col:
        raise ValueError(f"Could not find Balance. Available: {list(df.columns)}")
    
    print(f"✓ Columns - Number: '{account_number_col}', Name: '{account_name_col}', Balance: '{balance_col}'")
    
    prepaid_mask = (
        df[account_number_col].astype(str).str.startswith('1') |
        df[account_name_col].astype(str).str.contains('prepaid', case=False, na=False) |
        df[account_name_col].astype(str).str.contains('deferred', case=False, na=False)
    )
    
    prepaid_df = df[prepaid_mask].copy()
    
    if len(prepaid_df) == 0:
        print("⚠ No prepaid accounts found. Processing all rows.")
        prepaid_df = df.copy()
    
    records_count = 0
    for _, row in prepaid_df.iterrows():
        try:
            if pd.isna(row[account_number_col]) or str(row[account_number_col]).strip() == '':
                continue
                
            balance = clean_amount(row[balance_col])
            
            tb_entry = TrialBalance(
                account_number=str(row[account_number_col]).strip(),
                account_name=str(row[account_name_col]).strip() if pd.notna(row[account_name_col]) else '',
                balance=balance,
                file_upload_id=ObjectId(file_upload_id)
            )
            tb_entry.save()
            records_count += 1
            
        except Exception as e:
            print(f"⚠ Skipping row: {e}")
            continue
    
    print(f"✓ Imported {records_count} TB records")
    return records_count


def process_invoices(df, file_upload_id):
    """Process Invoice data"""
    invoice_number_col = find_column(df, [
        'invoice_number', 'invoice_no', 'inv_no', 'number', 'num', 'invoice'
    ])
    
    date_col = find_column(df, [
        'date', 'invoice_date', 'inv_date', 'transaction_date'
    ])
    
    amount_col = find_column(df, [
        'amount', 'total', 'invoice_amount', 'ending_balance', 'balance', 'due'
    ])
    
    category_col = find_column(df, [
        'category', 'prepaid_expense_category', 'expense_category', 
        'type', 'description', 'item'
    ])
    
    account_number_col = find_column(df, [
        'account_code', 'account_number', 'account_no', 'acct_no', 'code'
    ])
    
    if not invoice_number_col:
        raise ValueError(f"Could not find Invoice Number. Available: {list(df.columns)}")
    if not date_col:
        raise ValueError(f"Could not find Date. Available: {list(df.columns)}")
    if not amount_col:
        raise ValueError(f"Could not find Amount. Available: {list(df.columns)}")
    
    if not category_col:
        print("⚠ No category column. Using 'Uncategorized'")
        df['category'] = 'Uncategorized'
        category_col = 'category'
    
    print(f"✓ Columns - Invoice#: '{invoice_number_col}', Date: '{date_col}', Amount: '{amount_col}', Category: '{category_col}'")
    
    records_count = 0
    for _, row in df.iterrows():
        try:
            if pd.isna(row[invoice_number_col]) or str(row[invoice_number_col]).strip() == '':
                continue
                
            date_value = row[date_col]
            invoice_date = pd.to_datetime(date_value).date()
            amount = clean_amount(row[amount_col])
            
            account_number = None
            if account_number_col and pd.notna(row[account_number_col]):
                account_number = str(row[account_number_col]).strip()
            
            invoice = Invoice(
                invoice_number=str(row[invoice_number_col]).strip(),
                invoice_date=invoice_date,
                amount=amount,
                prepaid_expense_category=str(row[category_col]).strip() if pd.notna(row[category_col]) else 'Uncategorized',
                account_number=account_number,
                file_upload_id=ObjectId(file_upload_id)
            )
            invoice.save()
            records_count += 1
            
        except Exception as e:
            print(f"⚠ Skipping invoice: {e}")
            continue
    
    print(f"✓ Imported {records_count} Invoices")
    return records_count
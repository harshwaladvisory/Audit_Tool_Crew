# Excel VBA Macro Replacement Tool

## Overview
Web application and CLI tool that replicates Excel VBA formatting macros using pandas and openpyxl. Transforms financial data by splitting account codes, calculating fiscal years, categorizing transactions, and applying professional styling.

## Recent Changes
- **2025-10-01**: Large file optimization and Balance calculation fix
  - Optimized for files with 20,000+ rows (smart styling to avoid timeouts)
  - Fixed header detection to handle blank rows in Excel files
  - Fixed Balance column calculation to work for all rows (not just first 764)
  - Added progress indicators for large file processing
  - Balance column now recalculates properly even if it exists in source file
- **2025-09-30**: Web application implementation
  - Created Flask web app with file upload/download interface
  - Fixed critical data loss bug (removed last row deletion)
  - Implemented UUID-based filenames for security
  - Added session-based download verification
  - Restricted uploads to .xlsx files only
- **2025-09-30**: Initial project setup
  - Created main.py with complete Excel processing pipeline
  - Installed pandas and openpyxl dependencies
  - Configured Python 3.11 environment

## Project Architecture

### Main Components
- **main.py**: Core script handling all Excel transformations and formatting
  - Data cleanup (delete row 1, remove Total rows)
  - Account splitting (Fund, Dept, MEPA, GL Code)
  - Fiscal year calculation (Oct-Sept logic)
  - Type categorization based on GL Code
  - Balance calculations with subtotals
  - Professional styling (borders, fonts, number formats, AutoFilter)

### Dependencies
- Flask: Web framework for file upload/download interface
- pandas: Data manipulation and Excel reading
- openpyxl: Excel styling, borders, number formats, workbook operations
- argparse: CLI argument parsing

## Usage

### Web Application (Primary)
The web app is now running and accessible in the webview. Simply:
1. Click "Choose Excel File" to select your .xlsx file
2. Click "Upload & Format" to process the file
3. Download your formatted file from the results page

Features:
- Beautiful, user-friendly interface
- Secure file handling with UUID-based filenames
- Session-based download verification
- Automatic file processing and formatting

### Command Line (Alternative)
```bash
python main.py --file <path_to_excel_file>
```

Default file: `input.xlsx`

### Expected Input Format
The Excel file should have:
- **Row 1**: Disposable header row (will be deleted)
- **Row 2**: Column headers (Account, Date, Description, Debit, Credit, etc.)
- **Row 3+**: Data rows

### What It Does
1. **Cleanup**: Deletes row 1, treats row 2 as headers
2. **Filter**: Removes rows containing "Total" in Account column
3. **Account Splitting**: Splits Account column (e.g., "101-2001-3001-4001") into:
   - Fund (101)
   - Dept (2001)
   - MEPA (3001)
   - GL Code (4001)
4. **Column Management**: Deletes "Demo Desc" column if present
5. **Fiscal Year**: Calculates F.Y. based on Date column (Oct-Sept logic)
   - Oct-Dec: `YYYY-(YYYY+1)`
   - Jan-Sep: `(YYYY-1)-YYYY`
6. **Type Categorization**: Maps GL Code first digit to:
   - 1 → Asset
   - 2 → Liabilities
   - 3 → Equities
   - 4 → Revenue
   - 5,6,7,8,9 → Expenditure
7. **Balance**: Calculates Balance = Debit - Credit
8. **Totals**: Adds subtotal row with sums for Debit, Credit, Balance
9. **Formatting**: Applies professional styling:
   - Medium borders and outer border
   - Random header shading (light colors)
   - Calibri 11pt font
   - Accounting number format (#,##0.00) for financial columns
   - AutoFilter on all columns
   - Auto-fit column widths
10. **Output**: Saves to new "#Formatted" worksheet (overwrites if exists)

### Output Structure
The `#Formatted` worksheet contains:
- **Row 1**: Column headers
- **Row 2**: Totals row with subtotals
- **Row 3+**: Processed data rows

Column order: Account, Fund, Dept, MEPA, GL Code, Type, F.Y., Date, Description, Debit, Credit, Balance

### Example
```bash
python main.py --file financial_data.xlsx
```

Output:
```
Processing file: financial_data.xlsx

✓ Processing complete!
  - Rows processed: 150
  - Rows removed (containing 'Total'): 5
  - Columns added: Fund, Dept, MEPA, GL Code, Type, F.Y., Balance
  - Output: Sheet '#Formatted' in financial_data.xlsx
```

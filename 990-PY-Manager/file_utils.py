import re
import streamlit as st

def increment_year_in_filename(filename):
    """Increment the year in the filename by 1"""
    try:
        # Look for 4-digit years (2020-2099)
        year_pattern = r'(20\d{2})'
        
        def increment_year(match):
            year = int(match.group(1))
            return str(year + 1)
        
        # Replace the first occurrence of a year
        new_filename = re.sub(year_pattern, increment_year, filename, count=1)
        
        # If no year was found, append current year + 1
        if new_filename == filename:
            from datetime import datetime
            current_year = datetime.now().year
            name_part, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            new_filename = f"{name_part}_{current_year + 1}"
            if ext:
                new_filename += f".{ext}"
        
        return new_filename
        
    except Exception as e:
        st.warning(f"Could not increment year in filename {filename}: {str(e)}")
        return filename

def validate_excel_file(file):
    """Validate that the uploaded file is a valid Excel file"""
    try:
        if not file:
            return False
        
        # Check file extension
        valid_extensions = ['.xlsx', '.xls']
        if not any(file.name.lower().endswith(ext) for ext in valid_extensions):
            return False
        
        # Try to read the file header to verify it's a valid Excel file
        file.seek(0)
        header = file.read(8)
        file.seek(0)  # Reset file pointer
        
        # Excel file signatures
        xlsx_signature = b'\x50\x4b\x03\x04'  # ZIP signature (XLSX files are ZIP archives)
        xls_signature = b'\xd0\xcf\x11\xe0'   # OLE signature (XLS files)
        
        return header.startswith(xlsx_signature) or header.startswith(xls_signature)
        
    except Exception as e:
        st.error(f"Error validating file {file.name}: {str(e)}")
        return False

def get_file_info(file):
    """Get basic information about the uploaded file"""
    try:
        return {
            'name': file.name,
            'size': len(file.getvalue()),
            'type': file.type if hasattr(file, 'type') else 'unknown'
        }
    except Exception as e:
        st.error(f"Error getting file info: {str(e)}")
        return None

"""
PDF Extractor - Inline PDF Form Field Extraction
Replaces N8N webhook dependency
"""

import logging
from pypdf import PdfReader
import re

logger = logging.getLogger(__name__)


class RRFPDFExtractor:
    """Extract data from RRF-1 PDF forms"""
    
    def __init__(self):
        self.field_mapping = {
            # Map PDF form field names to our data model
            'Signing Person': ['signing_person', 'signer_name', 'name_of_signer', 'Printed Name', 'Name'],
            'Title': ['title', 'signer_title', 'position', 'Position'],
            'Client name': ['client_name', 'organization_name', 'org_name', 'entity_name', 'Organization', 'Name of Organization'],
            'Address Line 1': ['address1', 'address_line_1', 'street_address', 'Street', 'Address'],
            'Address Line 2': ['address2', 'address_line_2', 'suite_apt', 'Suite', 'Apt'],
            'Fiscal Year': ['fiscal_year', 'tax_year', 'year_ending', 'Year', 'Tax Year'],
            'Total Revenue': ['total_revenue', 'gross_receipts', 'revenue', 'Revenue', 'Gross Receipts']
        }
    
    def extract(self, pdf_path: str) -> dict:
        """
        Extract data from RRF-1 PDF form
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            dict: Extracted data with standardized keys
        """
        try:
            logger.info(f"📄 Extracting data from PDF: {pdf_path}")
            
            reader = PdfReader(pdf_path)
            
            # Try form field extraction first (fastest)
            extracted_data = self._extract_form_fields(reader)
            
            # If no form fields, try text extraction with patterns
            if not extracted_data or len(extracted_data) < 3:
                logger.info("No form fields found, trying text extraction...")
                extracted_data = self._extract_from_text(reader)
            
            # Validate required fields
            required_fields = ['Signing Person', 'Client name', 'Total Revenue']
            missing_fields = [f for f in required_fields if not extracted_data.get(f)]
            
            if missing_fields:
                logger.warning(f"⚠️ Missing required fields: {missing_fields}")
            
            logger.info(f"✅ Extracted {len(extracted_data)} fields from PDF")
            logger.info(f"   Extracted data: {extracted_data}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ PDF extraction error: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to extract data from PDF: {str(e)}")
    
    def _extract_form_fields(self, reader: PdfReader) -> dict:
        """Extract data from PDF form fields"""
        extracted = {}
        
        try:
            # Get form fields from PDF
            if reader.get_fields():
                fields = reader.get_fields()
                logger.info(f"Found {len(fields)} form fields")
                
                for field_name, field_data in fields.items():
                    value = field_data.get('/V', '')
                    
                    if value:
                        # Match against our field mapping
                        matched_key = self._match_field_name(field_name)
                        if matched_key:
                            extracted[matched_key] = str(value).strip()
                            logger.info(f"  ✓ {matched_key}: {value}")
        
        except Exception as e:
            logger.warning(f"Form field extraction failed: {str(e)}")
        
        return extracted
    
    def _extract_from_text(self, reader: PdfReader) -> dict:
        """Extract data from PDF text using patterns (fallback)"""
        extracted = {}
        
        try:
            # Extract all text from PDF
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
            
            logger.info(f"Extracted {len(full_text)} characters of text")
            
            # Define extraction patterns
            patterns = {
                'Signing Person': r'(?:Signing Person|Printed Name|Name)[:\s]+([A-Za-z\s\.]+)',
                'Title': r'(?:Title|Position)[:\s]+([A-Za-z\s\.]+)',
                'Client name': r'(?:Client Name|Organization|Entity)[:\s]+([A-Za-z0-9\s\.,\-]+)',
                'Address Line 1': r'(?:Address|Street)[:\s]+([A-Za-z0-9\s\.,\-]+)',
                'Fiscal Year': r'(?:Fiscal Year|Tax Year|Year Ending)[:\s]+(\d{4})',
                'Total Revenue': r'(?:Total Revenue|Gross Receipts|Revenue)[:\s]+\$?([\d,\.]+)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    extracted[key] = value
                    logger.info(f"  ✓ {key}: {value}")
        
        except Exception as e:
            logger.warning(f"Text extraction failed: {str(e)}")
        
        return extracted
    
    def _match_field_name(self, field_name: str) -> str:
        """Match PDF field name to our standardized keys"""
        field_name_lower = field_name.lower().replace('_', ' ').replace('-', ' ')
        
        for standard_key, variations in self.field_mapping.items():
            for variation in variations:
                if variation.lower() in field_name_lower:
                    return standard_key
        
        # If no match, return original field name
        return field_name
    
    def calculate_fee(self, total_revenue: str) -> float:
        """Calculate fee based on total revenue"""
        try:
            # Remove commas and dollar signs
            revenue_str = str(total_revenue).replace(',', '').replace('$', '').strip()
            revenue = float(revenue_str)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid revenue value: {total_revenue}, defaulting to $25")
            return 25.0
        
        # Fee schedule (from RRFGenerator.py)
        if revenue < 50000:
            return 25.0
        elif revenue < 100000:
            return 50.0
        elif revenue < 250000:
            return 75.0
        elif revenue < 1000000:
            return 100.0
        elif revenue < 5000000:
            return 200.0
        elif revenue < 20000000:
            return 400.0
        elif revenue < 100000000:
            return 800.0
        elif revenue < 500000000:
            return 1000.0
        else:
            return 1200.0
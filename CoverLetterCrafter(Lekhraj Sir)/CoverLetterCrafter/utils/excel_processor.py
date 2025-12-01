import pandas as pd
import logging
from typing import List, Dict, Any

class ExcelProcessor:
    """Process Excel files and extract cover letter data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_excel(self, filepath: str, client_name: str, draft_type: str, tax_year: str) -> Dict[str, Any]:
        """
        Process Excel file and return structured cover letter data
        
        Args:
            filepath: Path to the Excel file
            client_name: Name of the client
            draft_type: Type of draft (Preliminary Draft / Revised Draft)
            tax_year: Tax year for the return
            
        Returns:
            Dictionary containing processed cover letter data
        """
        try:
            # Read Excel file
            df = pd.read_excel(filepath)
            self.logger.debug(f"Loaded Excel file with {len(df)} rows")
            
            # Validate required columns
            required_columns = [
                'Applicability', 'Prefill Status', 'Header',
                'Instruction – Prefilled', 'Instruction – Data Required',
                'Instruction – Applicability Unknown'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
            # Process rows and group by header
            cover_letter_sections = []
            grouped_sections = {}
            section_number = 1
            
            for index, row in df.iterrows():
                try:
                    # Check applicability and prefill status
                    applicability = str(row['Applicability']).strip().lower()
                    prefill_status = str(row['Prefill Status']).strip().lower()
                    
                    # Only process applicable rows
                    if applicability == 'applicable':
                        section_data = self._process_row(row, section_number, client_name, draft_type, tax_year)
                        if section_data:
                            header = section_data['header']
                            
                            # Group sections by header
                            if header not in grouped_sections:
                                grouped_sections[header] = {
                                    'number': section_number,
                                    'header': header,
                                    'instructions': [],
                                    'custom_numbering': section_data.get('custom_numbering', '')
                                }
                                section_number += 1
                            
                            grouped_sections[header]['instructions'].append({
                                'instruction': section_data['instruction'],
                                'prefill_status': section_data['prefill_status']
                            })

                    # FIXED: Handle typo in Excel data - "Confirm Applicabilty" (missing 'i')
                    elif ('confirm applicabilty' in applicability or 'confirm applicability' in applicability) and prefill_status == 'unknown':
                        # Process rows with "Confirm Applicability" (or its typo variant) and "Unknown" prefill status
                        k_column_value = row.get('Instruction – Applicability Unknown', None)
                        
                        # Check if K column has meaningful content (not NaN, not "N/A", not empty)
                        if (not pd.isna(k_column_value) and 
                            str(k_column_value).strip() not in ['', 'N/A', 'n/a', 'nan']):
                            
                            self.logger.debug(f"Processing row {index} with Confirm Applicability + Unknown. K column value: {k_column_value}")
                            
                            section_data = self._process_row(row, section_number, client_name, draft_type, tax_year)
                            if section_data:
                                header = section_data['header']
                                if header not in grouped_sections:
                                    grouped_sections[header] = {
                                        'number': section_number,
                                        'header': header,
                                        'instructions': [],
                                        'custom_numbering': section_data.get('custom_numbering', '')
                                    }
                                    section_number += 1
                                grouped_sections[header]['instructions'].append({
                                    'instruction': section_data['instruction'],
                                    'prefill_status': section_data['prefill_status']
                                })
                        else:
                            self.logger.debug(f"Skipping row {index} - K column is empty or N/A: {k_column_value}")
                    
                except Exception as e:
                    self.logger.warning(f"Error processing row {index}: {str(e)}")
                    continue
            
            # Convert grouped sections to list, maintaining order
            for header, section in grouped_sections.items():
                cover_letter_sections.append(section)
            
            if not cover_letter_sections:
                raise ValueError("No applicable sections found in the Excel file")
            
            return {
                'client_name': client_name,
                'draft_type': draft_type,
                'tax_year': tax_year,
                'sections': cover_letter_sections,
                'total_sections': len(cover_letter_sections)
            }
            
        except Exception as e:
            self.logger.error(f"Error processing Excel file: {str(e)}")
            raise
    
    def _process_row(self, row: pd.Series, section_number: int, client_name: str, draft_type: str, tax_year: str) -> Dict[str, Any]:
        """
        Process a single row and return section data
        
        Args:
            row: Pandas Series representing a row
            section_number: Current section number
            client_name: Name of the client
            draft_type: Type of draft (Preliminary Draft / Revised Draft)
            tax_year: Tax year for the return
            
        Returns:
            Dictionary containing section data
        """
        try:
            # Get header  
            header_value = row['Header']
            header = str(header_value).strip() if str(header_value) != 'nan' else f"Section {section_number}"
            
            # Get prefill status and corresponding instruction
            prefill_status = str(row['Prefill Status']).strip().lower()
            applicability = str(row['Applicability']).strip().lower()

            instruction = ""
            
            if prefill_status == 'prefilled':
                instruction = str(row['Instruction – Prefilled']).strip()
            elif prefill_status == 'data required' or 'data reuired' in prefill_status:  # Handle typo in "Required"
                instruction = str(row['Instruction – Data Required']).strip()
            elif prefill_status == 'unknown' or prefill_status == 'applicability unknown':
                # FIXED: Handle both correct spelling and typo
                if ('confirm applicabilty' in applicability or 'confirm applicability' in applicability):
                    # Pull from the K column (Instruction – Applicability Unknown)
                    k_column_instruction = row.get('Instruction – Applicability Unknown', None)
                    if not pd.isna(k_column_instruction) and str(k_column_instruction).strip() not in ['', 'N/A', 'n/a']:
                        instruction = str(k_column_instruction).strip()
                        self.logger.debug(f"Using K column instruction: {instruction}")
                    else:
                        # Fallback instruction if K is empty or N/A
                        instruction = "Please confirm if this section is applicable and provide any necessary information."
                else:
                    # Use the standard unknown instruction column
                    instruction = str(row['Instruction – Applicability Unknown']).strip() if 'Instruction – Applicability Unknown' in row else "Please confirm if this section is applicable and provide any necessary information."
            else:
                # Default to data required if status is unclear
                instruction = str(row['Instruction – Data Required']).strip()

            # Handle NaN values
            if pd.isna(instruction) or instruction == 'nan' or instruction.strip() == '':
                instruction = "Please provide additional information for this section."

            # Replace placeholders in instruction
            instruction = instruction.replace('[Client Name]', client_name)
            instruction = instruction.replace('2023', tax_year)
            instruction = instruction.replace('preliminary draft', draft_type.lower())
            
            return {
                'number': section_number,
                'header': header,
                'instruction': instruction,
                'prefill_status': prefill_status
            }
    
        except Exception as e:
            self.logger.error(f"Error processing row: {str(e)}")
            return {}

    
    def validate_excel_structure(self, filepath: str) -> bool:
        """
        Validate that the Excel file has the correct structure
        
        Args:
            filepath: Path to the Excel file
            
        Returns:
            True if structure is valid, False otherwise
        """
        try:
            df = pd.read_excel(filepath)
            
            # Core required columns (must be present)
            core_required_columns = [
                'Applicability', 'Prefill Status', 'Header',
                'Instruction – Prefilled', 'Instruction – Data Required'
            ]
            
            # Check if core columns exist
            core_columns_present = all(col in df.columns for col in core_required_columns)
            
            # Check if there's an Unknown instruction column (flexible naming)
            unknown_instruction_exists = any(
                'unknown' in str(col).lower() and 'instruction' in str(col).lower() 
                for col in df.columns
            )
            
            # Also check for exact match as fallback
            exact_unknown_col = 'Instruction – Applicability Unknown' in df.columns
            
            return core_columns_present and (unknown_instruction_exists or exact_unknown_col)
            
        except Exception as e:
            self.logger.error(f"Error validating Excel structure: {str(e)}")
            return False
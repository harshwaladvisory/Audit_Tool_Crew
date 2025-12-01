from datetime import datetime
import base64

class ProcessingRecord:
    """Data model for processing records"""
    
    def __init__(self, job_id, status='PENDING'):
        self.job_id = job_id
        self.run_timestamp = datetime.now()
        self.status = status
        
        # Input files
        self.input_pdf_name = None
        self.input_pdf_path = None
        self.input_pdf_content = None
        
        self.input_word_name = None
        self.input_word_path = None
        self.input_word_content = None
        
        # Output file
        self.output_word_name = None
        self.output_word_path = None
        self.output_word_content = None
        
        # Metadata
        self.approval_date = None
        self.log_message = ""
        self.extracted_data = {}
    
    def set_input_pdf(self, filename, filepath, content):
        """Set input PDF data"""
        self.input_pdf_name = filename
        self.input_pdf_path = filepath
        self.input_pdf_content = base64.b64encode(content).decode('utf-8') if content else None
    
    def set_input_word(self, filename, filepath, content):
        """Set input Word template data"""
        self.input_word_name = filename
        self.input_word_path = filepath
        self.input_word_content = base64.b64encode(content).decode('utf-8') if content else None
    
    def set_output_word(self, filename, filepath, content):
        """Set output Word document data"""
        self.output_word_name = filename
        self.output_word_path = filepath
        self.output_word_content = base64.b64encode(content).decode('utf-8') if content else None
    
    def set_extracted_data(self, data):
        """Store extracted data from PDF"""
        self.extracted_data = data
    
    def to_dict(self):
        """Convert model to dictionary for MongoDB storage"""
        return {
            'job_id': self.job_id,
            'run_timestamp': self.run_timestamp,
            'status': self.status,
            'input_pdf_name': self.input_pdf_name,
            'input_pdf_path': self.input_pdf_path,
            'input_pdf_content': self.input_pdf_content,
            'input_word_name': self.input_word_name,
            'input_word_path': self.input_word_path,
            'input_word_content': self.input_word_content,
            'output_word_name': self.output_word_name,
            'output_word_path': self.output_word_path,
            'output_word_content': self.output_word_content,
            'approval_date': self.approval_date,
            'log_message': self.log_message,
            'extracted_data': self.extracted_data
        }
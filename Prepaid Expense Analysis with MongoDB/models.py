import mongoengine as me
from datetime import datetime
from decimal import Decimal


class GeneralLedger(me.Document):
    """Model for General Ledger entries"""
    account_number = me.StringField(required=True, max_length=50)
    account_name = me.StringField(required=True, max_length=255)
    balance = me.DecimalField(required=True, precision=2)
    file_upload_id = me.ObjectIdField()
    created_at = me.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'general_ledger',
        'indexes': ['account_number', 'file_upload_id']
    }
    
    def __repr__(self):
        return f'<GeneralLedger {self.account_number}: {self.account_name}>'


class TrialBalance(me.Document):
    """Model for Trial Balance entries"""
    account_number = me.StringField(required=True, max_length=50)
    account_name = me.StringField(required=True, max_length=255)
    balance = me.DecimalField(required=True, precision=2)
    file_upload_id = me.ObjectIdField()
    created_at = me.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'trial_balance',
        'indexes': ['account_number', 'file_upload_id']
    }
    
    def __repr__(self):
        return f'<TrialBalance {self.account_number}: {self.account_name}>'


class Invoice(me.Document):
    """Model for Invoice data"""
    invoice_number = me.StringField(required=True, max_length=100)
    invoice_date = me.DateField(required=True)
    amount = me.DecimalField(required=True, precision=2)
    prepaid_expense_category = me.StringField(required=True, max_length=255)
    account_number = me.StringField(max_length=50)
    file_upload_id = me.ObjectIdField()
    created_at = me.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'invoices',
        'indexes': ['invoice_number', 'file_upload_id', 'account_number']
    }
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}: {self.amount}>'


class PrepaidExpenseAnalysis(me.Document):
    """Model for storing prepaid expense analysis results"""
    account_number = me.StringField(required=True, max_length=50)
    account_name = me.StringField(required=True, max_length=255)
    gl_balance = me.DecimalField(precision=2)
    tb_balance = me.DecimalField(precision=2)
    recalculated_balance = me.DecimalField(required=True, precision=2)
    discrepancy_gl = me.DecimalField(precision=2)
    discrepancy_tb = me.DecimalField(precision=2)
    analysis_date = me.DateTimeField(default=datetime.utcnow)
    notes = me.StringField()
    file_upload_id = me.ObjectIdField()
    
    meta = {
        'collection': 'prepaid_expense_analysis',
        'indexes': ['account_number', 'analysis_date', 'file_upload_id']
    }
    
    def __repr__(self):
        return f'<Analysis {self.account_number}: {self.account_name}>'


class Discrepancy(me.Document):
    """Model for tracking discrepancies found during analysis"""
    account_number = me.StringField(required=True, max_length=50)
    account_name = me.StringField(required=True, max_length=255)
    discrepancy_type = me.StringField(required=True, max_length=50, choices=['GL', 'TB', 'BOTH'])
    recorded_amount = me.DecimalField(required=True, precision=2)
    calculated_amount = me.DecimalField(required=True, precision=2)
    difference = me.DecimalField(required=True, precision=2)
    status = me.StringField(default='OPEN', choices=['OPEN', 'RESOLVED'])
    analysis_id = me.ObjectIdField()
    created_at = me.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'discrepancies',
        'indexes': ['status', 'account_number', 'created_at']
    }
    
    def __repr__(self):
        return f'<Discrepancy {self.account_number}: {self.difference}>'


class JournalEntry(me.Document):
    """Model for suggested journal entries (AJEs)"""
    entry_number = me.StringField(required=True, max_length=50)
    account_number = me.StringField(required=True, max_length=50)
    account_name = me.StringField(required=True, max_length=255)
    debit_amount = me.DecimalField(default=Decimal('0'), precision=2)
    credit_amount = me.DecimalField(default=Decimal('0'), precision=2)
    description = me.StringField(required=True)
    discrepancy_id = me.ObjectIdField()
    status = me.StringField(default='PROPOSED', choices=['PROPOSED', 'APPROVED', 'POSTED'])
    created_at = me.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'journal_entries',
        'indexes': ['entry_number', 'status', 'created_at']
    }
    
    def __repr__(self):
        return f'<JournalEntry {self.entry_number}: {self.account_number}>'


class FileUpload(me.Document):
    """Model for tracking file uploads"""
    filename = me.StringField(required=True, max_length=255)
    file_type = me.StringField(required=True, max_length=20, choices=['GL', 'TB', 'INVOICE'])
    file_path = me.StringField(required=True, max_length=500)
    upload_date = me.DateTimeField(default=datetime.utcnow)
    processed = me.BooleanField(default=False)
    records_count = me.IntField(default=0)
    error_message = me.StringField()
    
    meta = {
        'collection': 'file_uploads',
        'indexes': ['file_type', 'upload_date', 'processed']
    }
    
    def __repr__(self):
        return f'<FileUpload {self.filename}: {self.file_type}>'
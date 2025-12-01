"""
Database models for Securities Deposits Analysis (MongoDB version)
UPDATED with all required fields
"""

from mongoengine import Document, EmbeddedDocument, fields
from datetime import datetime


class FileUpload(Document):
    """File upload tracking."""
    filename = fields.StringField(required=True)
    file_path = fields.StringField(required=True)
    file_size = fields.IntField()
    upload_date = fields.DateTimeField(default=datetime.now)
    status = fields.StringField(default='uploaded')
    records_processed = fields.IntField(default=0)
    error_message = fields.StringField()
    created_at = fields.DateTimeField(default=datetime.now)
    updated_at = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'file_uploads',
        'indexes': ['filename', 'upload_date', 'status']
    }


class Deposit(Document):
    """Deposit record."""
    account_number = fields.StringField(required=True)
    customer_name = fields.StringField(required=True)
    deposit_type = fields.StringField(required=True)
    amount = fields.FloatField(required=True)
    interest_rate = fields.FloatField(default=0.0)
    deposit_date = fields.DateField(required=True)
    maturity_date = fields.DateField()
    last_activity_date = fields.DateField()
    branch_code = fields.StringField()
    product_code = fields.StringField()
    status = fields.StringField(default='active')
    file_upload = fields.ReferenceField(FileUpload)
    created_at = fields.DateTimeField(default=datetime.now)
    updated_at = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'deposits',
        'indexes': ['account_number', 'customer_name', 'deposit_date', 'status', 'file_upload']
    }


class AgingAnalysis(Document):
    """Aging analysis results - UPDATED with compliance_status."""
    deposit = fields.ReferenceField(Deposit, required=True)
    analysis_date = fields.DateField(required=True)
    days_to_maturity = fields.IntField(required=True)
    aging_bucket = fields.StringField(required=True)
    risk_level = fields.StringField(required=True)
    amount = fields.FloatField(required=True)
    
    # ⭐ ADDED FIELD
    compliance_status = fields.StringField(default='compliant')  # compliant, under-review, non-compliant
    notes = fields.StringField()
    
    created_at = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'aging_analysis',
        'indexes': ['deposit', 'analysis_date', 'aging_bucket', 'risk_level', 'compliance_status']
    }


class InterestCalculation(Document):
    """Interest calculation results - UPDATED with all fields."""
    deposit = fields.ReferenceField(Deposit, required=True)
    calculation_date = fields.DateField(required=True)
    interest_rate = fields.FloatField(required=True)
    days_held = fields.IntField(required=True)
    
    # ⭐ ADDED FIELDS
    principal_amount = fields.FloatField(default=0.0)
    interest_earned = fields.FloatField(default=0.0)
    interest_accrued = fields.FloatField(required=True)
    cumulative_interest = fields.FloatField(default=0.0)
    total_value = fields.FloatField(required=True)
    
    created_at = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'interest_calculations',
        'indexes': ['deposit', 'calculation_date']
    }


class AuditProgram(Document):
    """Audit program."""
    name = fields.StringField(required=True)
    description = fields.StringField()
    procedures = fields.ListField(fields.DictField())
    status = fields.StringField(default='draft')
    created_at = fields.DateTimeField(default=datetime.now)
    updated_at = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'audit_programs',
        'indexes': ['name', 'status', 'created_at']
    }


class Report(Document):
    """Generated report - UPDATED."""
    report_type = fields.StringField(required=True)
    title = fields.StringField(required=True)
    
    # Changed to DictField for flexible JSON storage
    report_data = fields.DictField()  # Store full report as JSON
    content = fields.DictField()  # Legacy field
    
    file_path = fields.StringField()
    created_at = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'reports',
        'indexes': ['report_type', 'created_at']
    }


class AuditLog(Document):
    """Audit log entry."""
    action = fields.StringField(required=True)
    entity_type = fields.StringField()
    entity_id = fields.StringField()
    details = fields.DictField()
    created_at = fields.DateTimeField(default=datetime.now)
    
    meta = {
        'collection': 'audit_logs',
        'indexes': ['action', 'entity_type', 'created_at']
    }
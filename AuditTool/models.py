from mongoengine import Document, fields, CASCADE, NULLIFY
from datetime import datetime
import json

class AuditSession(Document):
    session_name = fields.StringField(required=True, max_length=200)
    client_name = fields.StringField(required=True, max_length=200)
    fiscal_year_end = fields.DateField(required=True)
    materiality_threshold = fields.FloatField(default=10000.0)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    status = fields.StringField(default='pending', max_length=50)
    
    meta = {
        'collection': 'audit_sessions',
        'indexes': ['created_at', 'client_name']
    }

class UploadedFile(Document):
    filename = fields.StringField(required=True, max_length=255)
    file_type = fields.StringField(required=True, max_length=50)  # 'check_register' or 'subsequent_gl'
    file_path = fields.StringField(required=True, max_length=500)
    upload_date = fields.DateTimeField(default=datetime.utcnow)
    processed = fields.BooleanField(default=False)
    session = fields.ReferenceField('AuditSession', required=True, reverse_delete_rule=CASCADE)
    
    meta = {
        'collection': 'uploaded_files',
        'indexes': ['session']
    }

class Transaction(Document):
    session = fields.ReferenceField('AuditSession', required=True, reverse_delete_rule=CASCADE)
    transaction_date = fields.DateField(required=True)
    vendor_name = fields.StringField(max_length=200)
    amount = fields.FloatField(required=True)
    description = fields.StringField()
    check_number = fields.StringField(max_length=50)
    account_code = fields.StringField(max_length=50)
    payment_type = fields.StringField(max_length=50)
    is_sampled = fields.BooleanField(default=False)
    sample_month = fields.IntField()  # 1=first month, 2=second, 3=third
    
    meta = {
        'collection': 'transactions',
        'indexes': [
            'session',
            'transaction_date',
            'is_sampled',
            'sample_month',
            ('session', 'is_sampled')
        ]
    }

class Finding(Document):
    session = fields.ReferenceField('AuditSession', required=True, reverse_delete_rule=CASCADE)
    transaction = fields.ReferenceField('Transaction', reverse_delete_rule=NULLIFY)
    finding_type = fields.StringField(required=True, max_length=100)
    description = fields.StringField(required=True)
    amount = fields.FloatField()
    risk_level = fields.StringField(default='medium', max_length=20)  # low, medium, high
    status = fields.StringField(default='open', max_length=50)  # open, resolved, dismissed
    created_at = fields.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'findings',
        'indexes': ['session', 'risk_level']
    }

class AuditReport(Document):
    session = fields.ReferenceField('AuditSession', required=True, reverse_delete_rule=CASCADE)
    report_data = fields.StringField()  # JSON string containing report details
    generated_at = fields.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'audit_reports',
        'indexes': ['session']
    }
    
    def get_report_data(self):
        return json.loads(self.report_data) if self.report_data else {}
    
    def set_report_data(self, data):
        self.report_data = json.dumps(data)
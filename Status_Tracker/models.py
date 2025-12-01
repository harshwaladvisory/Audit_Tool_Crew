from mongoengine import Document, fields
from datetime import datetime

class CharityCheck(Document):
    """Model to store charity registration check results"""
    ein = fields.StringField(required=True, max_length=20)
    status = fields.StringField(required=True, max_length=200)
    check_date = fields.DateTimeField(default=datetime.utcnow)
    monday_item_id = fields.StringField(max_length=50)
    monday_updated = fields.BooleanField(default=False)
    file_name = fields.StringField(max_length=255)
    task_id = fields.StringField(max_length=100)
    
    meta = {
        'collection': 'charity_checks',
        'indexes': [
            'ein',
            'check_date',
            'task_id',
            ('ein', '-check_date')  # Compound index for EIN with latest check first
        ]
    }
    
    def __str__(self):
        return f"CharityCheck(EIN={self.ein}, Status={self.status})"


class ProcessingTask(Document):
    """Model to track file processing tasks"""
    task_id = fields.StringField(required=True, unique=True, max_length=100)
    file_name = fields.StringField(required=True, max_length=255)
    status = fields.StringField(default='pending', max_length=50)  # pending, processing, completed, error
    total_eins = fields.IntField(default=0)
    processed_eins = fields.IntField(default=0)
    started_at = fields.DateTimeField(default=datetime.utcnow)
    completed_at = fields.DateTimeField()
    error_message = fields.StringField()
    
    meta = {
        'collection': 'processing_tasks',
        'indexes': ['task_id', 'status', 'started_at']
    }
    
    def __str__(self):
        return f"ProcessingTask(ID={self.task_id}, Status={self.status}, Progress={self.processed_eins}/{self.total_eins})"
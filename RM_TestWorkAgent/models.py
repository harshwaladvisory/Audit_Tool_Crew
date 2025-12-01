from datetime import datetime
from mongoengine import Document, EmbeddedDocument
from mongoengine import StringField, FloatField, DateTimeField, IntField, ListField, DictField, ReferenceField, EmbeddedDocumentField

class Run(Document):
    meta = {'collection': 'runs'}
    
    name = StringField(required=True, max_length=255)
    status = StringField(default='draft', max_length=50)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    finalized_at = DateTimeField()
    
    capitalization_threshold = FloatField(default=5000)
    materiality = FloatField(default=25000)
    fy_start = StringField(max_length=10)
    fy_end = StringField(max_length=10)
    allowed_accounts = ListField(StringField())
    
    metrics = DictField()
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(Run, self).save(*args, **kwargs)


class GLPopulation(Document):
    meta = {'collection': 'gl_population'}
    
    run = ReferenceField(Run, required=True, reverse_delete_rule=2)
    
    account_code = StringField(max_length=50)
    account_name = StringField(max_length=255)
    description = StringField()
    amount = FloatField()
    date = StringField(max_length=50)
    reference = StringField(max_length=100)
    vendor_name = StringField(max_length=255)
    
    row_number = IntField()
    created_at = DateTimeField(default=datetime.utcnow)


class TBMapping(Document):
    meta = {'collection': 'tb_mappings'}
    
    run = ReferenceField(Run, required=True, reverse_delete_rule=2)
    
    account_code = StringField(max_length=50)
    account_name = StringField(max_length=255)
    tb_amount = FloatField()
    
    created_at = DateTimeField(default=datetime.utcnow)


class SupportDocument(EmbeddedDocument):
    filename = StringField(required=True, max_length=255)
    original_filename = StringField(required=True, max_length=255)
    file_type = StringField(max_length=50)
    file_size = IntField()
    file_hash = StringField(max_length=64)
    file_path = StringField(max_length=500)
    document_type = StringField(max_length=50)
    uploaded_at = DateTimeField(default=datetime.utcnow)


class AttributeCheck(EmbeddedDocument):
    attribute_number = IntField(required=True)
    status = StringField(default='pending', max_length=20)
    comment = StringField()
    checked_at = DateTimeField()
    checked_by = StringField(max_length=100)


class Sample(Document):
    meta = {'collection': 'samples'}
    
    run = ReferenceField(Run, required=True, reverse_delete_rule=2)
    gl_item = ReferenceField(GLPopulation, required=True)
    
    sample_type = StringField(max_length=50)
    stratum = StringField(max_length=50)
    selection_reason = StringField()
    
    support_status = StringField(default='pending', max_length=50)
    attributes_status = StringField(default='pending', max_length=50)
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    support_docs = ListField(EmbeddedDocumentField(SupportDocument))
    attribute_checks = ListField(EmbeddedDocumentField(AttributeCheck))


class Exception(Document):
    meta = {'collection': 'exceptions'}
    
    run = ReferenceField(Run, required=True, reverse_delete_rule=2)
    sample = ReferenceField(Sample)
    
    exception_type = StringField(max_length=50)
    severity = StringField(max_length=20)
    title = StringField(max_length=255)
    description = StringField()
    recommended_action = StringField()
    
    status = StringField(default='open', max_length=20)
    
    created_at = DateTimeField(default=datetime.utcnow)
    resolved_at = DateTimeField()


class AuditLog(Document):
    meta = {'collection': 'audit_logs'}
    
    run = ReferenceField(Run)
    
    user_id = StringField(default='system', max_length=100)
    action = StringField(required=True, max_length=100)
    resource_type = StringField(max_length=50)
    resource_id = StringField(max_length=50)
    
    payload_digest = StringField(max_length=64)
    details = DictField()
    
    timestamp = DateTimeField(default=datetime.utcnow)
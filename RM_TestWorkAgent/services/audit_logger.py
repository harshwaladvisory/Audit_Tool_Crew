import hashlib
import json
from typing import Dict, Any, Optional
from models import AuditLog, db
from datetime import datetime
import logging

class AuditLogger:
    """Handle audit trail logging"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_action(self, run_id: Optional[int], action: str, resource_type: str, 
                   resource_id: str, details: Optional[Dict[str, Any]] = None, 
                   user_id: str = 'system') -> bool:
        """Log an action to the audit trail"""
        try:
            # Generate payload digest if details provided
            payload_digest = None
            if details:
                payload_json = json.dumps(details, sort_keys=True, default=str)
                payload_digest = hashlib.sha256(payload_json.encode()).hexdigest()
            
            # Create audit log entry
            audit_entry = AuditLog(
                run_id=run_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                payload_digest=payload_digest,
                details=details,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(audit_entry)
            db.session.commit()
            
            self.logger.info(f'Audit log created: {action} on {resource_type}:{resource_id}')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to create audit log: {str(e)}')
            db.session.rollback()
            return False
    
    def log_file_upload(self, run_id: int, filename: str, file_hash: str, 
                       file_size: int, user_id: str = 'system') -> bool:
        """Log file upload with hash"""
        return self.log_action(
            run_id=run_id,
            action='file_uploaded',
            resource_type='file',
            resource_id=filename,
            details={
                'filename': filename,
                'file_hash': file_hash,
                'file_size': file_size,
                'upload_timestamp': datetime.utcnow().isoformat()
            },
            user_id=user_id
        )
    
    def log_sample_creation(self, run_id: int, sample_id: int, sample_type: str, 
                          amount: float, user_id: str = 'system') -> bool:
        """Log sample creation"""
        return self.log_action(
            run_id=run_id,
            action='sample_created',
            resource_type='sample',
            resource_id=str(sample_id),
            details={
                'sample_type': sample_type,
                'amount': amount,
                'creation_timestamp': datetime.utcnow().isoformat()
            },
            user_id=user_id
        )
    
    def log_attribute_check(self, run_id: int, sample_id: int, attribute_number: int, 
                          status: str, comment: str = '', user_id: str = 'system') -> bool:
        """Log attribute check update"""
        return self.log_action(
            run_id=run_id,
            action='attribute_check_updated',
            resource_type='attribute',
            resource_id=f'{sample_id}_{attribute_number}',
            details={
                'sample_id': sample_id,
                'attribute_number': attribute_number,
                'status': status,
                'comment': comment,
                'check_timestamp': datetime.utcnow().isoformat()
            },
            user_id=user_id
        )
    
    def log_exception_creation(self, run_id: int, exception_id: int, exception_type: str, 
                             severity: str, sample_id: Optional[int] = None, 
                             user_id: str = 'system') -> bool:
        """Log exception creation"""
        return self.log_action(
            run_id=run_id,
            action='exception_created',
            resource_type='exception',
            resource_id=str(exception_id),
            details={
                'exception_type': exception_type,
                'severity': severity,
                'sample_id': sample_id,
                'creation_timestamp': datetime.utcnow().isoformat()
            },
            user_id=user_id
        )
    
    def log_report_generation(self, run_id: int, report_type: str, 
                            report_path: str, user_id: str = 'system') -> bool:
        """Log report generation"""
        return self.log_action(
            run_id=run_id,
            action='report_generated',
            resource_type='report',
            resource_id=report_type,
            details={
                'report_type': report_type,
                'report_path': report_path,
                'generation_timestamp': datetime.utcnow().isoformat()
            },
            user_id=user_id
        )
    
    def get_audit_trail(self, run_id: int, limit: int = 100) -> list:
        """Get audit trail for a run"""
        try:
            audit_entries = (AuditLog.query
                           .filter_by(run_id=run_id)
                           .order_by(AuditLog.timestamp.desc())
                           .limit(limit)
                           .all())
            
            return [{
                'id': entry.id,
                'timestamp': entry.timestamp.isoformat(),
                'user_id': entry.user_id,
                'action': entry.action,
                'resource_type': entry.resource_type,
                'resource_id': entry.resource_id,
                'payload_digest': entry.payload_digest,
                'details': entry.details
            } for entry in audit_entries]
            
        except Exception as e:
            self.logger.error(f'Failed to get audit trail: {str(e)}')
            return []
    
    def verify_data_integrity(self, run_id: int) -> Dict[str, Any]:
        """Verify data integrity using audit logs"""
        try:
            # Get all audit entries with payload digests
            entries_with_digests = (AuditLog.query
                                  .filter_by(run_id=run_id)
                                  .filter(AuditLog.payload_digest.isnot(None))
                                  .all())
            
            integrity_results = {
                'total_entries': len(entries_with_digests),
                'verified_entries': 0,
                'failed_entries': [],
                'integrity_score': 0.0
            }
            
            for entry in entries_with_digests:
                if entry.details:
                    # Recalculate digest
                    payload_json = json.dumps(entry.details, sort_keys=True, default=str)
                    calculated_digest = hashlib.sha256(payload_json.encode()).hexdigest()
                    
                    if calculated_digest == entry.payload_digest:
                        integrity_results['verified_entries'] += 1
                    else:
                        integrity_results['failed_entries'].append({
                            'entry_id': entry.id,
                            'action': entry.action,
                            'timestamp': entry.timestamp.isoformat(),
                            'expected_digest': entry.payload_digest,
                            'calculated_digest': calculated_digest
                        })
            
            # Calculate integrity score
            if integrity_results['total_entries'] > 0:
                integrity_results['integrity_score'] = (
                    integrity_results['verified_entries'] / 
                    integrity_results['total_entries'] * 100
                )
            
            return integrity_results
            
        except Exception as e:
            self.logger.error(f'Failed to verify data integrity: {str(e)}')
            return {
                'error': str(e),
                'integrity_score': 0.0
            }
    
    def generate_integrity_report(self, run_id: int) -> str:
        """Generate human-readable integrity report"""
        integrity_results = self.verify_data_integrity(run_id)
        
        if 'error' in integrity_results:
            return f"Integrity verification failed: {integrity_results['error']}"
        
        report = f"""
Data Integrity Report - Run {run_id}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Total audit entries with digests: {integrity_results['total_entries']}
Verified entries: {integrity_results['verified_entries']}
Failed entries: {len(integrity_results['failed_entries'])}
Integrity Score: {integrity_results['integrity_score']:.2f}%

Status: {'PASS' if integrity_results['integrity_score'] == 100.0 else 'FAIL'}
"""
        
        if integrity_results['failed_entries']:
            report += "\nFailed Entries:\n"
            for failed in integrity_results['failed_entries']:
                report += f"- Entry {failed['entry_id']}: {failed['action']} at {failed['timestamp']}\n"
        
        return report

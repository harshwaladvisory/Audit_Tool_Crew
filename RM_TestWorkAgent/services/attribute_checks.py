from typing import Dict, Any
from models import Sample, AttributeCheck, Exception, db
from config import Config
from datetime import datetime
import logging

class AttributeCheckService:
    """Handle attribute checking and exception creation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = Config()
    
    def initialize_sample_attributes(self, sample_id: int) -> Dict[str, Any]:
        """Initialize all 7 attribute checks for a sample"""
        try:
            sample = Sample.query.get(sample_id)
            if not sample:
                return {'success': False, 'error': 'Sample not found'}
            
            # Check if attributes already exist
            existing_checks = AttributeCheck.query.filter_by(sample_id=sample_id).count()
            if existing_checks > 0:
                return {'success': True, 'message': 'Attributes already initialized'}
            
            # Create all 7 attribute checks
            for attr_num in range(1, 8):
                attribute_check = AttributeCheck(
                    sample_id=sample_id,
                    attribute_number=attr_num,
                    status='pending'
                )
                db.session.add(attribute_check)
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Initialized 7 attribute checks for sample'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f'Initialize sample attributes error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_attribute_check(self, sample_id: int, attribute_number: int, 
                             status: str, comment: str = '') -> Dict[str, Any]:
        """Update a specific attribute check"""
        try:
            if attribute_number < 1 or attribute_number > 7:
                return {'success': False, 'error': 'Invalid attribute number (1-7)'}
            
            if status not in ['pass', 'fail', 'na', 'pending']:
                return {'success': False, 'error': 'Invalid status'}
            
            # Get or create attribute check
            attribute_check = AttributeCheck.query.filter_by(
                sample_id=sample_id,
                attribute_number=attribute_number
            ).first()
            
            if not attribute_check:
                # Initialize all attributes if none exist
                self.initialize_sample_attributes(sample_id)
                attribute_check = AttributeCheck.query.filter_by(
                    sample_id=sample_id,
                    attribute_number=attribute_number
                ).first()
            
            # Update the check
            attribute_check.status = status
            attribute_check.comment = comment
            attribute_check.checked_at = datetime.utcnow()
            attribute_check.checked_by = 'system'  # TODO: Get from session
            
            # Create exception if failed
            if status == 'fail':
                self.create_exception(sample_id, attribute_number, comment)
            
            # Update sample status
            self.update_sample_status(sample_id)
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Attribute {attribute_number} updated to {status}'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f'Update attribute check error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_exception(self, sample_id: int, attribute_number: int, comment: str):
        """Create exception for failed attribute check"""
        try:
            sample = Sample.query.get(sample_id)
            if not sample:
                return
            
            # Get attribute description
            attribute_desc = self.config.ATTRIBUTE_CHECKS.get(attribute_number, f'Attribute {attribute_number}')
            
            # Determine severity based on attribute type
            severity = self._get_attribute_severity(attribute_number)
            
            # Get recommended action
            recommended_action = self._get_recommended_action(attribute_number)
            
            exception = Exception(
                run_id=sample.run_id,
                sample_id=sample_id,
                exception_type='attribute_failure',
                severity=severity,
                title=f'Attribute {attribute_number} Failed - {sample.gl_item.account_name}',
                description=f'{attribute_desc}: {comment}',
                recommended_action=recommended_action,
                status='open'
            )
            
            db.session.add(exception)
            
        except Exception as e:
            self.logger.error(f'Create exception error: {str(e)}')
    
    def update_sample_status(self, sample_id: int):
        """Update sample attributes status based on individual checks"""
        try:
            # Get all attribute checks for sample
            checks = AttributeCheck.query.filter_by(sample_id=sample_id).all()
            
            if len(checks) < 7:
                # Not all attributes initialized
                status = 'pending'
            else:
                pending_count = len([c for c in checks if c.status == 'pending'])
                if pending_count > 0:
                    status = 'in_progress'
                else:
                    status = 'complete'
            
            # Update sample status
            sample = Sample.query.get(sample_id)
            if sample:
                sample.attributes_status = status
            
        except Exception as e:
            self.logger.error(f'Update sample status error: {str(e)}')
    
    def _get_attribute_severity(self, attribute_number: int) -> str:
        """Determine severity level for attribute failure"""
        # High severity attributes (financial accuracy and controls)
        high_severity = [1, 2, 6, 7]  # Amount accuracy, authorization, controls, accounting
        # Medium severity attributes (process compliance)
        medium_severity = [3, 4, 5]  # Documentation, timing, approvals
        
        if attribute_number in high_severity:
            return 'high'
        elif attribute_number in medium_severity:
            return 'medium'
        else:
            return 'low'
    
    def _get_recommended_action(self, attribute_number: int) -> str:
        """Get recommended action for attribute failure"""
        actions = {
            1: 'Verify calculation accuracy and obtain corrected documentation. Review voucher processing controls.',
            2: 'Obtain proper authorization documentation. Review approval hierarchy and delegation of authority.',
            3: 'Ensure documents are properly marked to prevent reprocessing. Review payment system controls.',
            4: 'Verify transaction relates to current fiscal year. Review accrual and cutoff procedures.',
            5: 'Obtain evidence of pre-approval. Review purchase order system and approval workflows.',
            6: 'Review segregation of duties and approval processes. Assess control design and operating effectiveness.',
            7: 'Review capitalization policy and ensure proper expense/capital classification. Consult with accounting team.'
        }
        
        return actions.get(attribute_number, 'Review and remediate identified deficiency.')
    
    def get_sample_attributes_summary(self, sample_id: int) -> Dict[str, Any]:
        """Get summary of all attribute checks for a sample"""
        try:
            sample = Sample.query.get(sample_id)
            if not sample:
                return {'success': False, 'error': 'Sample not found'}
            
            # Get all attribute checks
            checks = AttributeCheck.query.filter_by(sample_id=sample_id).order_by(AttributeCheck.attribute_number).all()
            
            # Build summary
            attributes = []
            status_counts = {'pending': 0, 'pass': 0, 'fail': 0, 'na': 0}
            
            for attr_num in range(1, 8):
                check = next((c for c in checks if c.attribute_number == attr_num), None)
                
                attr_data = {
                    'attribute_number': attr_num,
                    'description': self.config.ATTRIBUTE_CHECKS.get(attr_num, f'Attribute {attr_num}'),
                    'status': check.status if check else 'pending',
                    'comment': check.comment if check else '',
                    'checked_at': check.checked_at.isoformat() if check and check.checked_at else None,
                    'checked_by': check.checked_by if check else None
                }
                
                attributes.append(attr_data)
                status_counts[attr_data['status']] += 1
            
            return {
                'success': True,
                'sample_id': sample_id,
                'attributes': attributes,
                'status_counts': status_counts,
                'completion_percentage': ((7 - status_counts['pending']) / 7 * 100) if status_counts['pending'] < 7 else 0
            }
            
        except Exception as e:
            self.logger.error(f'Get sample attributes summary error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def bulk_update_attributes(self, sample_id: int, updates: Dict[int, Dict[str, str]]) -> Dict[str, Any]:
        """Update multiple attribute checks at once"""
        try:
            sample = Sample.query.get(sample_id)
            if not sample:
                return {'success': False, 'error': 'Sample not found'}
            
            updated_attributes = []
            
            for attr_num, update_data in updates.items():
                if attr_num < 1 or attr_num > 7:
                    continue
                
                status = update_data.get('status', 'pending')
                comment = update_data.get('comment', '')
                
                result = self.update_attribute_check(sample_id, attr_num, status, comment)
                if result['success']:
                    updated_attributes.append(attr_num)
            
            return {
                'success': True,
                'updated_attributes': updated_attributes,
                'message': f'Updated {len(updated_attributes)} attribute checks'
            }
            
        except Exception as e:
            self.logger.error(f'Bulk update attributes error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }

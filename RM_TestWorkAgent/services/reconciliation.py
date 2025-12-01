from typing import Dict, Any
from models import GLPopulation, TBMapping, Run, Exception, db
from sqlalchemy import func
import logging

class ReconciliationService:
    """Handle GL to TB reconciliation and validation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def reconcile_gl_to_tb(self, run_id: int) -> Dict[str, Any]:
        """Perform GL to TB reconciliation for a run"""
        try:
            run = Run.query.get(run_id)
            if not run:
                return {'success': False, 'error': 'Run not found'}
            
            # Get GL totals by account
            gl_totals = (db.session.query(
                GLPopulation.account_code,
                func.sum(GLPopulation.amount).label('gl_total')
            ).filter_by(run_id=run_id)
            .group_by(GLPopulation.account_code)
            .all())
            
            # Get TB totals by account
            tb_totals = (db.session.query(
                TBMapping.account_code,
                func.sum(TBMapping.tb_amount).label('tb_total')
            ).filter_by(run_id=run_id)
            .group_by(TBMapping.account_code)
            .all())
            
            # Convert to dictionaries for easy lookup
            gl_dict = {account: float(total) for account, total in gl_totals}
            tb_dict = {account: float(total) for account, total in tb_totals}
            
            # Perform reconciliation
            reconciliation_results = []
            exceptions_created = 0
            
            all_accounts = set(gl_dict.keys()) | set(tb_dict.keys())
            
            for account in all_accounts:
                gl_amount = gl_dict.get(account, 0.0)
                tb_amount = tb_dict.get(account, 0.0)
                difference = gl_amount - tb_amount
                
                reconciliation_item = {
                    'account_code': account,
                    'gl_amount': gl_amount,
                    'tb_amount': tb_amount,
                    'difference': difference,
                    'status': 'matched' if abs(difference) < 0.01 else 'variance'
                }
                
                reconciliation_results.append(reconciliation_item)
                
                # Create exception for significant variances
                if abs(difference) >= run.materiality * 0.05:  # 5% of materiality
                    self._create_reconciliation_exception(
                        run_id, account, gl_amount, tb_amount, difference
                    )
                    exceptions_created += 1
            
            # Calculate summary metrics
            total_gl = sum(gl_dict.values())
            total_tb = sum(tb_dict.values())
            total_difference = total_gl - total_tb
            
            matched_accounts = len([r for r in reconciliation_results if r['status'] == 'matched'])
            variance_accounts = len([r for r in reconciliation_results if r['status'] == 'variance'])
            
            metrics = {
                'reconciliation': {
                    'total_accounts': len(all_accounts),
                    'matched_accounts': matched_accounts,
                    'variance_accounts': variance_accounts,
                    'total_gl_amount': total_gl,
                    'total_tb_amount': total_tb,
                    'total_difference': total_difference,
                    'reconciliation_percentage': (matched_accounts / len(all_accounts) * 100) if all_accounts else 100,
                    'exceptions_created': exceptions_created
                },
                'details': reconciliation_results
            }
            
            return {
                'success': True,
                'metrics': metrics,
                'message': f'Reconciliation completed. {matched_accounts}/{len(all_accounts)} accounts matched.'
            }
            
        except Exception as e:
            self.logger.error(f'Reconciliation error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_reconciliation_exception(self, run_id: int, account_code: str, 
                                       gl_amount: float, tb_amount: float, difference: float):
        """Create exception for reconciliation variance"""
        try:
            severity = 'high' if abs(difference) >= 25000 else 'medium'
            
            exception = Exception(
                run_id=run_id,
                exception_type='reconciliation_variance',
                severity=severity,
                title=f'Reconciliation variance for account {account_code}',
                description=f'GL amount ({gl_amount:,.2f}) does not match TB amount ({tb_amount:,.2f}). Difference: {difference:,.2f}',
                recommended_action='Review account postings and TB mapping for accuracy. Investigate source of variance.',
                status='open'
            )
            
            db.session.add(exception)
            
        except Exception as e:
            self.logger.error(f'Error creating reconciliation exception: {str(e)}')
    
    def get_reconciliation_summary(self, run_id: int) -> Dict[str, Any]:
        """Get reconciliation summary for a run"""
        try:
            run = Run.query.get(run_id)
            if not run or not run.metrics:
                return {'success': False, 'error': 'No reconciliation data available'}
            
            reconciliation_metrics = run.metrics.get('reconciliation', {})
            
            return {
                'success': True,
                'summary': reconciliation_metrics
            }
            
        except Exception as e:
            self.logger.error(f'Get reconciliation summary error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_account_mappings(self, run_id: int) -> Dict[str, Any]:
        """Validate that all GL accounts have corresponding TB mappings"""
        try:
            # Get unique GL accounts
            gl_accounts = (db.session.query(GLPopulation.account_code)
                          .filter_by(run_id=run_id)
                          .distinct()
                          .all())
            
            # Get unique TB accounts
            tb_accounts = (db.session.query(TBMapping.account_code)
                          .filter_by(run_id=run_id)
                          .distinct()
                          .all())
            
            gl_account_set = {acc[0] for acc in gl_accounts}
            tb_account_set = {acc[0] for acc in tb_accounts}
            
            # Find unmapped accounts
            gl_only = gl_account_set - tb_account_set
            tb_only = tb_account_set - gl_account_set
            
            validation_result = {
                'gl_accounts_count': len(gl_account_set),
                'tb_accounts_count': len(tb_account_set),
                'common_accounts': len(gl_account_set & tb_account_set),
                'gl_only_accounts': list(gl_only),
                'tb_only_accounts': list(tb_only),
                'mapping_complete': len(gl_only) == 0 and len(tb_only) == 0
            }
            
            return {
                'success': True,
                'validation': validation_result
            }
            
        except Exception as e:
            self.logger.error(f'Validate account mappings error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }

import pandas as pd
import os
from datetime import datetime
from typing import Dict, Any
from models import AuditSession, Transaction, Finding

class ReportGenerator:
    def __init__(self, session: AuditSession):
        self.session = session
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive audit report data
        """
        report_data = {
            'session_info': self._get_session_info(),
            'summary_statistics': self._get_summary_statistics(),
            'sampling_details': self._get_sampling_details(),
            'findings_summary': self._get_findings_summary(),
            'recommendations': self._get_recommendations(),
            'detailed_findings': self._get_detailed_findings(),
            'generated_at': datetime.now().isoformat()
        }
        
        return report_data
    
    def _get_session_info(self) -> Dict[str, Any]:
        """
        Get basic session information
        """
        return {
            'session_name': self.session.session_name,
            'client_name': self.session.client_name,
            'fiscal_year_end': self.session.fiscal_year_end.isoformat(),
            'materiality_threshold': self.session.materiality_threshold,
            'created_at': self.session.created_at.isoformat(),
            'status': self.session.status
        }
    
    def _get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics for the analysis
        """
        transactions = Transaction.objects(session=self.session)
        sampled_transactions = Transaction.objects(session=self.session, is_sampled=True)
        
        total_amount = sum(t.amount for t in transactions)
        sampled_amount = sum(t.amount for t in sampled_transactions)
        
        total_count = transactions.count()
        sampled_count = sampled_transactions.count()
        
        return {
            'total_transactions': total_count,
            'total_amount': total_amount,
            'sampled_transactions': sampled_count,
            'sampled_amount': sampled_amount,
            'sampling_percentage': (sampled_count / total_count * 100) if total_count > 0 else 0
        }
    
    def _get_sampling_details(self) -> Dict[str, Any]:
        """
        Get detailed sampling information by month
        """
        monthly_details = {}
        
        for month in [1, 2, 3]:
            month_transactions = Transaction.objects(session=self.session, sample_month=month)
            sampled = Transaction.objects(session=self.session, sample_month=month, is_sampled=True)
            
            monthly_details[f'month_{month}'] = {
                'total_transactions': month_transactions.count(),
                'sampled_transactions': sampled.count(),
                'total_amount': sum(t.amount for t in month_transactions),
                'sampled_amount': sum(t.amount for t in sampled)
            }
        
        return monthly_details
    
    def _get_findings_summary(self) -> Dict[str, Any]:
        """
        Get summary of audit findings
        """
        findings = Finding.objects(session=self.session)
        
        high_risk = Finding.objects(session=self.session, risk_level='high')
        medium_risk = Finding.objects(session=self.session, risk_level='medium')
        low_risk = Finding.objects(session=self.session, risk_level='low')
        
        total_amount = sum(f.amount for f in findings if f.amount)
        
        summary = {
            'total_findings': findings.count(),
            'high_risk': high_risk.count(),
            'medium_risk': medium_risk.count(),
            'low_risk': low_risk.count(),
            'total_amount_at_risk': total_amount
        }
        
        return summary
    
    def _get_recommendations(self) -> list[Dict[str, Any]]:
        """
        Generate audit recommendations based on findings
        """
        recommendations = []
        findings = Finding.objects(session=self.session)
        
        has_high_risk = Finding.objects(session=self.session, risk_level='high').count() > 0
        has_medium_low = Finding.objects(session=self.session, risk_level__in=['medium', 'low']).count() > 0
        
        if has_high_risk:
            recommendations.append({
                'priority': 'High',
                'recommendation': 'Review high-risk findings with management immediately.',
                'action_items': [
                    'Propose adjusting entries for prior year liabilities.',
                    'Obtain supporting documentation from vendors.'
                ]
            })
        
        if has_medium_low:
            recommendations.append({
                'priority': 'Medium',
                'recommendation': 'Evaluate medium and low-risk findings for potential adjustments.',
                'action_items': [
                    'Review current cut-off procedures.',
                    'Consider enhancing month-end accruals.'
                ]
            })
        
        return recommendations
    
    def _get_detailed_findings(self) -> list[Dict[str, Any]]:
        """
        Get detailed audit findings with transaction information
        """
        findings = Finding.objects(session=self.session)
        detailed_findings = []
        
        for finding in findings:
            finding_detail = {
                'finding_type': finding.finding_type,
                'description': finding.description,
                'amount': finding.amount,
                'risk_level': finding.risk_level,
                'status': finding.status
            }
            
            if finding.transaction:
                transaction = finding.transaction
                finding_detail['transaction_details'] = {
                    'date': transaction.transaction_date.isoformat(),
                    'vendor': transaction.vendor_name,
                    'amount': transaction.amount,
                    'description': transaction.description,
                    'check_number': transaction.check_number,
                    'payment_type': transaction.payment_type
                }
            
            detailed_findings.append(finding_detail)
        
        return detailed_findings
    
    def export_to_excel(self) -> str:
        """
        Export report to Excel file
        """
        report_data = self.generate_report()
        
        # Create Excel writer
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"audit_report_{self.session.client_name}_{timestamp}.xlsx"
        filepath = os.path.join('exports', filename)
        
        # Create exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([report_data['summary_statistics']])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Findings sheet
            if report_data['detailed_findings']:
                findings_data = []
                for finding in report_data['detailed_findings']:
                    row = {
                        'Finding Type': finding['finding_type'],
                        'Risk Level': finding['risk_level'],
                        'Amount': finding['amount'],
                        'Description': finding['description'],
                        'Status': finding['status']
                    }
                    
                    if 'transaction_details' in finding:
                        row.update({
                            'Transaction Date': finding['transaction_details']['date'],
                            'Vendor': finding['transaction_details']['vendor'],
                            'Transaction Amount': finding['transaction_details']['amount'],
                            'Transaction Description': finding['transaction_details']['description']
                        })
                    
                    findings_data.append(row)
                
                findings_df = pd.DataFrame(findings_data)
                findings_df.to_excel(writer, sheet_name='Findings', index=False)
            
            # Sampled transactions sheet
            sampled_transactions = Transaction.objects(session=self.session, is_sampled=True)
            
            if sampled_transactions.count() > 0:
                trans_data = [{
                    'Date': t.transaction_date,
                    'Vendor': t.vendor_name,
                    'Amount': t.amount,
                    'Description': t.description,
                    'Check Number': t.check_number,
                    'Payment Type': t.payment_type,
                    'Sample Month': t.sample_month
                } for t in sampled_transactions]
                
                trans_df = pd.DataFrame(trans_data)
                trans_df.to_excel(writer, sheet_name='Sampled Transactions', index=False)
        
        return filepath
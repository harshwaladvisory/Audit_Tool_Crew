"""
Report generation service for securities deposits analysis (MongoDB version)
"""

import json
import os
from datetime import datetime, timedelta
from models import Deposit, InterestCalculation, AgingAnalysis, Report


class ReportGenerator:
    """Service for generating various types of reports."""
    
    def __init__(self):
        self.report_types = {
            'summary': self._generate_summary_report,
            'aging': self._generate_aging_report,
            'interest': self._generate_interest_report,
            'exception': self._generate_exception_report,
            'compliance': self._generate_compliance_report,
            'unclaimed': self._generate_unclaimed_report
        }
    
    def generate_report(self, report_type, parameters=None):
        """
        Generate a report of the specified type.
        
        Args:
            report_type (str): Type of report to generate
            parameters (dict): Optional parameters for report generation
            
        Returns:
            dict: Generated report data
        """
        if report_type not in self.report_types:
            raise ValueError(f"Unsupported report type: {report_type}")
        
        return self.report_types[report_type](parameters or {})
    
    def _generate_summary_report(self, parameters):
        """Generate summary report of all deposits."""
        try:
            current_date = datetime.now().date()
            
            # Basic statistics using MongoDB aggregation
            total_deposits = Deposit.objects.count()
            
            # Calculate total amount
            pipeline = [
                {'$group': {
                    '_id': None,
                    'total': {'$sum': '$amount'}
                }}
            ]
            result = list(Deposit.objects.aggregate(pipeline))
            total_amount = result[0]['total'] if result else 0
            
            # Status breakdown
            status_pipeline = [
                {'$group': {
                    '_id': '$status',
                    'count': {'$sum': 1},
                    'amount': {'$sum': '$amount'}
                }}
            ]
            status_data = list(Deposit.objects.aggregate(status_pipeline))
            
            status_summary = {}
            for item in status_data:
                status_summary[item['_id']] = {
                    'count': item['count'],
                    'amount': float(item['amount'])
                }
            
            # Deposit type breakdown
            type_pipeline = [
                {'$group': {
                    '_id': '$deposit_type',
                    'count': {'$sum': 1},
                    'amount': {'$sum': '$amount'}
                }}
            ]
            type_data = list(Deposit.objects.aggregate(type_pipeline))
            
            type_summary = {}
            for item in type_data:
                type_summary[item['_id']] = {
                    'count': item['count'],
                    'amount': float(item['amount'])
                }
            
            # Recent activity (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_deposits = Deposit.objects(created_at__gte=thirty_days_ago).count()
            
            return {
                'report_type': 'summary',
                'report_date': current_date.isoformat(),
                'summary_stats': {
                    'total_deposits': total_deposits,
                    'total_amount': float(total_amount),
                    'recent_deposits_30_days': recent_deposits
                },
                'status_breakdown': status_summary,
                'type_breakdown': type_summary,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error generating summary report: {str(e)}")
    
    def _generate_aging_report(self, parameters):
        """Generate aging analysis report."""
        try:
            current_date = datetime.now().date()
            
            # Get recent aging analysis
            aging_records = AgingAnalysis.objects(analysis_date=current_date)
            
            # Aging bucket summary
            aging_summary = {}
            for record in aging_records:
                bucket = record.aging_bucket
                if bucket not in aging_summary:
                    aging_summary[bucket] = {'count': 0, 'amount': 0}
                aging_summary[bucket]['count'] += 1
                aging_summary[bucket]['amount'] += float(record.deposit.amount)
            
            # Risk level distribution
            risk_summary = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            for record in aging_records:
                if record.risk_level in risk_summary:
                    risk_summary[record.risk_level] += 1
            
            # High-risk deposits details
            high_risk_deposits = AgingAnalysis.objects(
                analysis_date=current_date,
                risk_level__in=['high', 'critical']
            ).limit(50)
            
            high_risk_details = []
            for record in high_risk_deposits:
                high_risk_details.append({
                    'account_number': record.deposit.account_number,
                    'customer_name': record.deposit.customer_name,
                    'amount': float(record.deposit.amount),
                    'aging_bucket': record.aging_bucket,
                    'risk_level': record.risk_level,
                    'days_since_maturity': record.days_since_maturity
                })
            
            total_analyzed = sum(v['count'] for v in aging_summary.values()) if aging_summary else 0
            
            return {
                'report_type': 'aging',
                'report_date': current_date.isoformat(),
                'aging_summary': aging_summary,
                'risk_distribution': risk_summary,
                'high_risk_deposits': high_risk_details,
                'total_analyzed': total_analyzed,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error generating aging report: {str(e)}")
    
    def _generate_interest_report(self, parameters):
        """Generate interest accrual report."""
        try:
            current_date = datetime.now().date()
            
            # Interest calculations summary
            calculations = InterestCalculation.objects(calculation_date=current_date)
            
            total_earned = 0
            total_cumulative = 0
            calculations_count = 0
            
            for calc in calculations:
                total_earned += float(calc.interest_earned)
                total_cumulative += float(calc.cumulative_interest)
                calculations_count += 1
            
            # Top earning deposits
            top_earners = InterestCalculation.objects(
                calculation_date=current_date
            ).order_by('-interest_earned').limit(20)
            
            top_earners_details = []
            for calc in top_earners:
                top_earners_details.append({
                    'account_number': calc.deposit.account_number,
                    'customer_name': calc.deposit.customer_name,
                    'principal_amount': float(calc.principal_amount),
                    'interest_earned': float(calc.interest_earned),
                    'cumulative_interest': float(calc.cumulative_interest)
                })
            
            return {
                'report_type': 'interest',
                'report_date': current_date.isoformat(),
                'summary': {
                    'total_interest_earned': total_earned,
                    'total_cumulative_interest': total_cumulative,
                    'deposits_calculated': calculations_count
                },
                'top_earners': top_earners_details,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error generating interest report: {str(e)}")
    
    def _generate_exception_report(self, parameters):
        """Generate exception report for unusual or problematic deposits."""
        try:
            current_date = datetime.now().date()
            
            exceptions = []
            
            # Large deposits (over $100,000)
            large_deposits = Deposit.objects(amount__gt=100000).limit(50)
            
            for deposit in large_deposits:
                exceptions.append({
                    'type': 'large_amount',
                    'account_number': deposit.account_number,
                    'customer_name': deposit.customer_name,
                    'amount': float(deposit.amount),
                    'description': f'Large deposit amount: ${deposit.amount:,.2f}',
                    'severity': 'medium'
                })
            
            # Deposits with zero interest rate but should have interest
            zero_interest = Deposit.objects(
                interest_rate=0,
                deposit_type__in=['certificate', 'cd', 'time_deposit']
            ).limit(50)
            
            for deposit in zero_interest:
                exceptions.append({
                    'type': 'zero_interest',
                    'account_number': deposit.account_number,
                    'customer_name': deposit.customer_name,
                    'deposit_type': deposit.deposit_type,
                    'description': 'Interest-bearing deposit type with zero interest rate',
                    'severity': 'low'
                })
            
            # Very old deposits (over 10 years)
            old_threshold = current_date - timedelta(days=3650)
            old_deposits = Deposit.objects(deposit_date__lt=old_threshold).limit(50)
            
            for deposit in old_deposits:
                years_old = (current_date - deposit.deposit_date).days // 365
                exceptions.append({
                    'type': 'very_old',
                    'account_number': deposit.account_number,
                    'customer_name': deposit.customer_name,
                    'deposit_date': deposit.deposit_date.isoformat(),
                    'description': f'Very old deposit: {years_old} years',
                    'severity': 'high'
                })
            
            # Group exceptions by severity
            severity_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            for exception in exceptions:
                severity_counts[exception['severity']] += 1
            
            return {
                'report_type': 'exception',
                'report_date': current_date.isoformat(),
                'total_exceptions': len(exceptions),
                'severity_breakdown': severity_counts,
                'exceptions': exceptions,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error generating exception report: {str(e)}")
    
    def _generate_compliance_report(self, parameters):
        """Generate compliance report based on regulatory requirements."""
        try:
            current_date = datetime.now().date()
            
            # Compliance status summary
            compliance_records = AgingAnalysis.objects(analysis_date=current_date)
            
            compliance_summary = {}
            for record in compliance_records:
                status = record.compliance_status
                if status not in compliance_summary:
                    compliance_summary[status] = 0
                compliance_summary[status] += 1
            
            # Non-compliant deposits details
            non_compliant = AgingAnalysis.objects(
                analysis_date=current_date,
                compliance_status__ne='compliant'
            )
            
            non_compliant_details = []
            for record in non_compliant:
                non_compliant_details.append({
                    'account_number': record.deposit.account_number,
                    'customer_name': record.deposit.customer_name,
                    'amount': float(record.deposit.amount),
                    'compliance_status': record.compliance_status,
                    'notes': record.notes
                })
            
            return {
                'report_type': 'compliance',
                'report_date': current_date.isoformat(),
                'compliance_summary': compliance_summary,
                'non_compliant_deposits': non_compliant_details,
                'total_reviewed': sum(compliance_summary.values()),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error generating compliance report: {str(e)}")
    
    def _generate_unclaimed_report(self, parameters):
        """Generate unclaimed deposits report."""
        try:
            # Get unclaimed deposits
            unclaimed_deposits = Deposit.objects(status='unclaimed')
            
            unclaimed_details = []
            total_unclaimed_amount = 0
            
            for deposit in unclaimed_deposits:
                activity_date = deposit.last_activity_date or deposit.deposit_date
                days_dormant = (datetime.now().date() - activity_date).days
                
                unclaimed_details.append({
                    'account_number': deposit.account_number,
                    'customer_name': deposit.customer_name,
                    'amount': float(deposit.amount),
                    'deposit_date': deposit.deposit_date.isoformat(),
                    'last_activity_date': activity_date.isoformat(),
                    'days_dormant': days_dormant
                })
                
                total_unclaimed_amount += float(deposit.amount)
            
            return {
                'report_type': 'unclaimed',
                'report_date': datetime.now().date().isoformat(),
                'total_unclaimed_deposits': len(unclaimed_details),
                'total_unclaimed_amount': total_unclaimed_amount,
                'unclaimed_deposits': unclaimed_details,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error generating unclaimed report: {str(e)}")
    
    def save_report_to_file(self, report):
        """
        Save report data to file for download.
        
        Args:
            report: Report database object
            
        Returns:
            str: Path to saved report file
        """
        try:
            # Parse report_data if it's a string
            if isinstance(report.report_data, str):
                report_data = json.loads(report.report_data)
            else:
                report_data = report.report_data
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{report.report_type}_report_{timestamp}.json"
            file_path = os.path.join('reports', filename)
            
            # Ensure reports directory exists
            os.makedirs('reports', exist_ok=True)
            
            # Save report data to file
            with open(file_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            # Update report with file path
            report.file_path = file_path
            report.save()
            
            return file_path
            
        except Exception as e:
            raise Exception(f"Error saving report to file: {str(e)}")
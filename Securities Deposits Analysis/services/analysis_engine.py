"""
Analysis engine for deposits aging and risk assessment
Updated with proper field names and compliance tracking
"""

from models import Deposit, AgingAnalysis, InterestCalculation
from datetime import datetime, timedelta
from mongoengine import Q


class AnalysisEngine:
    """Engine for analyzing deposits."""
    
    def __init__(self):
        self.aging_buckets = [
            {'name': '0-30', 'min': 0, 'max': 30, 'risk': 'low'},
            {'name': '31-60', 'min': 31, 'max': 60, 'risk': 'low'},
            {'name': '61-90', 'min': 61, 'max': 90, 'risk': 'medium'},
            {'name': '91-180', 'min': 91, 'max': 180, 'risk': 'medium'},
            {'name': '181-365', 'min': 181, 'max': 365, 'risk': 'high'},
            {'name': '365+', 'min': 366, 'max': 999999, 'risk': 'high'}
        ]
    
    def perform_aging_analysis(self):
        """Perform aging analysis on all deposits."""
        try:
            # Delete existing aging analysis
            AgingAnalysis.objects.delete()
            
            deposits = Deposit.objects.all()
            
            if not deposits:
                return {
                    'status': 'error',
                    'message': 'No deposits found',
                    'total_deposits': 0,
                    'bucket_summary': {},
                    'risk_distribution': {},
                    'detailed_results': []
                }
            
            today = datetime.now().date()
            detailed_results = []
            
            for deposit in deposits:
                if not deposit.maturity_date:
                    # If no maturity date, use 1 year from deposit date
                    maturity_date = deposit.deposit_date + timedelta(days=365)
                else:
                    maturity_date = deposit.maturity_date
                
                # Calculate days to/since maturity
                days_to_maturity = (maturity_date - today).days
                
                # Determine aging bucket and risk level
                if days_to_maturity < 0:
                    # Past maturity - use absolute value for aging
                    days_since_maturity = abs(days_to_maturity)
                    aging_bucket = self._get_aging_bucket(days_since_maturity)
                    risk_level = 'high' if days_since_maturity > 90 else 'medium'
                else:
                    # Not yet matured
                    aging_bucket = '0-30'  # Current
                    risk_level = 'low'
                
                # Determine compliance status
                compliance_status = self._determine_compliance(days_to_maturity, deposit)
                
                # Calculate days since last activity
                last_activity = deposit.last_activity_date or deposit.deposit_date
                days_since_activity = (today - last_activity).days
                
                # Create aging analysis record
                aging = AgingAnalysis(
                    deposit=deposit,
                    analysis_date=today,
                    days_to_maturity=days_to_maturity,
                    aging_bucket=aging_bucket,
                    risk_level=risk_level,
                    amount=deposit.amount,
                    compliance_status=compliance_status,
                    notes=f"Days since activity: {days_since_activity}"
                )
                aging.save()
                
                detailed_results.append({
                    'account_number': deposit.account_number,
                    'customer_name': deposit.customer_name,
                    'amount': deposit.amount,
                    'deposit_date': deposit.deposit_date.isoformat(),
                    'maturity_date': maturity_date.isoformat(),
                    'days_since_maturity': abs(days_to_maturity) if days_to_maturity < 0 else None,
                    'days_since_last_activity': days_since_activity,
                    'aging_bucket': aging_bucket,
                    'risk_level': risk_level,
                    'compliance_status': compliance_status
                })
            
            # Generate summary
            summary = self._generate_aging_summary()
            
            return {
                'status': 'success',
                'total_deposits': len(deposits),
                'total_analyzed': len(detailed_results),
                'bucket_summary': summary.get('by_bucket', {}),
                'risk_distribution': summary.get('by_risk', {}),
                'detailed_results': detailed_results
            }
            
        except Exception as e:
            print(f"Aging analysis error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': str(e),
                'total_deposits': 0,
                'bucket_summary': {},
                'risk_distribution': {},
                'detailed_results': []
            }
    
    def _get_aging_bucket(self, days):
        """Get aging bucket name based on days."""
        for bucket in self.aging_buckets:
            if bucket['min'] <= days <= bucket['max']:
                return bucket['name']
        return '365+'
    
    def _determine_compliance(self, days_to_maturity, deposit):
        """Determine compliance status based on various factors."""
        # Past maturity by more than 90 days
        if days_to_maturity < -90:
            return 'non-compliant'
        
        # Past maturity but within 90 days
        if days_to_maturity < 0:
            return 'under-review'
        
        # Check for unclaimed deposits (no activity for 180+ days)
        if deposit.last_activity_date:
            days_inactive = (datetime.now().date() - deposit.last_activity_date).days
            if days_inactive > 180:
                return 'under-review'
        
        return 'compliant'
    
    def _generate_aging_summary(self):
        """Generate aging summary statistics."""
        try:
            summary = {
                'by_bucket': {},
                'by_risk': {
                    'low': 0,
                    'medium': 0,
                    'high': 0,
                    'critical': 0
                }
            }
            
            # Group by bucket
            aging_records = AgingAnalysis.objects.all()
            
            for record in aging_records:
                bucket = record.aging_bucket
                risk = record.risk_level
                amount = float(record.amount)
                
                # By bucket
                if bucket not in summary['by_bucket']:
                    summary['by_bucket'][bucket] = {'count': 0, 'amount': 0}
                summary['by_bucket'][bucket]['count'] += 1
                summary['by_bucket'][bucket]['amount'] += amount
                
                # By risk
                if risk in summary['by_risk']:
                    summary['by_risk'][risk] += 1
            
            return summary
            
        except Exception as e:
            print(f"Summary generation error: {str(e)}")
            return {'by_bucket': {}, 'by_risk': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}}
    
    def calculate_interest_accruals(self):
        """Calculate interest accruals with proper field names."""
        try:
            InterestCalculation.objects.delete()
            
            deposits = Deposit.objects.filter(interest_rate__gt=0)
            
            if not deposits:
                return {
                    'status': 'success',
                    'message': 'No deposits with interest rates found',
                    'total_calculated': 0,
                    'interest_data': []
                }
            
            today = datetime.now().date()
            interest_data = []
            
            for deposit in deposits:
                days_held = (today - deposit.deposit_date).days
                years_held = days_held / 365.0
                
                # Simple interest calculation
                principal = deposit.amount
                rate = deposit.interest_rate
                interest_earned = principal * rate * years_held
                
                # For first calculation, cumulative equals earned
                cumulative = interest_earned
                total_value = principal + cumulative
                
                interest_calc = InterestCalculation(
                    deposit=deposit,
                    calculation_date=today,
                    interest_rate=rate,
                    days_held=days_held,
                    principal_amount=principal,
                    interest_earned=interest_earned,
                    interest_accrued=interest_earned,  # Same as earned
                    cumulative_interest=cumulative,
                    total_value=total_value
                )
                interest_calc.save()
                
                interest_data.append({
                    'account_number': deposit.account_number,
                    'customer_name': deposit.customer_name,
                    'principal': principal,
                    'interest_rate': rate * 100,  # Convert to percentage
                    'days_held': days_held,
                    'interest_earned': interest_earned,
                    'cumulative_interest': cumulative,
                    'total_value': total_value
                })
            
            return {
                'status': 'success',
                'total_calculated': len(interest_data),
                'interest_data': interest_data
            }
            
        except Exception as e:
            print(f"Interest calculation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': str(e),
                'total_calculated': 0
            }
    
    def identify_unclaimed_deposits(self, inactivity_days=180):
        """Identify unclaimed deposits."""
        try:
            cutoff_date = datetime.now().date() - timedelta(days=inactivity_days)
            
            unclaimed = Deposit.objects.filter(
                Q(last_activity_date__lt=cutoff_date) | Q(last_activity_date=None),
                status='active'
            )
            
            unclaimed_data = []
            total_amount = 0
            
            for deposit in unclaimed:
                days_inactive = (datetime.now().date() - (deposit.last_activity_date or deposit.deposit_date)).days
                
                unclaimed_data.append({
                    'account_number': deposit.account_number,
                    'customer_name': deposit.customer_name,
                    'amount': deposit.amount,
                    'deposit_date': deposit.deposit_date,
                    'last_activity_date': deposit.last_activity_date,
                    'days_inactive': days_inactive
                })
                
                total_amount += deposit.amount
            
            return {
                'status': 'success',
                'total_unclaimed': len(unclaimed_data),
                'total_amount': total_amount,
                'unclaimed_data': unclaimed_data
            }
            
        except Exception as e:
            print(f"Unclaimed deposits error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
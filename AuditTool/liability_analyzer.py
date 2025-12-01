import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import re
from models import AuditSession, Transaction

class LiabilityAnalyzer:
    def __init__(self, session: AuditSession):
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    def analyze_transactions(self) -> List[Dict[str, Any]]:
        """
        Analyze transactions for unrecorded liabilities
        """
        findings = []
        
        # Sample transactions based on materiality
        sampled_transactions = self._sample_transactions()
        
        self.logger.info(f"Analyzing {len(sampled_transactions)} sampled transactions")
        
        # Analyze each sampled transaction
        for transaction in sampled_transactions:
            # Check for prior year services
            if self._is_prior_year_service(transaction):
                findings.append(self._create_finding(
                    transaction,
                    'prior_year_service',
                    f'Transaction appears to be for services from prior fiscal year: {transaction.description}',
                    'high'
                ))
            
            # Check for large unrecorded liabilities
            if self._is_large_liability(transaction):
                findings.append(self._create_finding(
                    transaction,
                    'large_liability',
                    f'Large payment that may indicate unrecorded liability: ${transaction.amount:,.2f}',
                    'medium'
                ))
            
            # Check for recurring service payments
            if self._is_recurring_service(transaction):
                findings.append(self._create_finding(
                    transaction,
                    'recurring_service',
                    f'Recurring service payment that may have prior year component: {transaction.description}',
                    'medium'
                ))
        
        self.logger.info(f"Created {len(findings)} findings")
        return findings
    
    def _sample_transactions(self) -> List[Transaction]:
        """
        Sample transactions based on materiality and risk assessment
        """
        # Get all transactions for this session, ordered by amount descending
        all_transactions = list(Transaction.objects(session=self.session).order_by('-amount'))
        
        self.logger.info(f"Total transactions available for sampling: {len(all_transactions)}")
        
        if not all_transactions:
            self.logger.warning("No transactions found for sampling")
            return []
        
        sampled = []
        materiality = self.session.materiality_threshold
        
        # Sample strategy: majority from month 1, some from months 2 and 3
        month1_transactions = [t for t in all_transactions if t.sample_month == 1]
        month2_transactions = [t for t in all_transactions if t.sample_month == 2]
        month3_transactions = [t for t in all_transactions if t.sample_month == 3]
        
        self.logger.info(f"Month 1 transactions: {len(month1_transactions)}, "
                        f"Month 2: {len(month2_transactions)}, "
                        f"Month 3: {len(month3_transactions)}")
        
        # Sample from month 1 (60% of samples)
        month1_sample_size = min(len(month1_transactions), max(10, int(len(month1_transactions) * 0.6)))
        sampled.extend(self._select_sample(month1_transactions, month1_sample_size, materiality))
        
        # Sample from month 2 (25% of samples)
        month2_sample_size = min(len(month2_transactions), max(3, int(len(month2_transactions) * 0.25)))
        sampled.extend(self._select_sample(month2_transactions, month2_sample_size, materiality))
        
        # Sample from month 3 (15% of samples)
        month3_sample_size = min(len(month3_transactions), max(2, int(len(month3_transactions) * 0.15)))
        sampled.extend(self._select_sample(month3_transactions, month3_sample_size, materiality))
        
        self.logger.info(f"Sampled {len(sampled)} transactions total")
        
        # CRITICAL: Mark transactions as sampled and save to MongoDB
        for transaction in sampled:
            transaction.is_sampled = True
            transaction.save()
            self.logger.debug(f"Marked transaction {transaction.id} as sampled: {transaction.vendor_name} - ${transaction.amount}")
        
        self.logger.info(f"Successfully marked {len(sampled)} transactions as sampled in MongoDB")
        
        return sampled
    
    def _select_sample(self, transactions, sample_size, materiality):
        """
        Select a sample based on amount, materiality, and risk indicators
        """
        if not transactions or sample_size <= 0:
            return []
        
        # Score transactions based on amount and risk
        scored_transactions = []
        for transaction in transactions:
            score = transaction.amount / materiality
            if self._has_risk_indicators(transaction):
                score *= 1.5  # Boost score for risky transactions
            scored_transactions.append((score, transaction))
        
        # Sort by score (highest first) and take top samples
        scored_transactions.sort(key=lambda x: x[0], reverse=True)
        
        selected = [t[1] for t in scored_transactions[:sample_size]]
        self.logger.debug(f"Selected {len(selected)} transactions from pool of {len(transactions)}")
        
        return selected
    
    def _has_risk_indicators(self, transaction: Transaction) -> bool:
        """
        Check if transaction has risk indicators for unrecorded liabilities
        """
        if not transaction.description:
            return False
        
        desc = transaction.description.lower()
        
        # Risk indicators in description
        risk_words = [
            'consulting', 'service', 'professional', 'legal', 'audit',
            'maintenance', 'subscription', 'license', 'insurance',
            'rent', 'utilities', 'telephone', 'internet', 'software'
        ]
        
        return any(word in desc for word in risk_words)
    
    def _is_prior_year_service(self, transaction: Transaction) -> bool:
        """
        Check if transaction description indicates prior year services
        """
        if not transaction.description:
            return False
        
        desc = transaction.description.lower()
        
        # Look for date references in description
        prior_year = self.session.fiscal_year_end.year
        prior_year_patterns = [
            str(prior_year),
            f'{prior_year-1}-{str(prior_year)[-2:]}',  # e.g., "2022-23"
            'prior year', 'previous year', 'year end'
        ]
        
        # Look for service period indicators
        period_indicators = [
            'for period', 'period ending', 'services rendered',
            'month of', 'quarter ending', 'annual'
        ]
        
        has_prior_year_ref = any(pattern in desc for pattern in prior_year_patterns)
        has_period_indicator = any(indicator in desc for indicator in period_indicators)
        
        return has_prior_year_ref or has_period_indicator
    
    def _is_large_liability(self, transaction: Transaction) -> bool:
        """
        Check if transaction represents a large potential liability
        """
        return transaction.amount > self.session.materiality_threshold
    
    def _is_recurring_service(self, transaction: Transaction) -> bool:
        """
        Check if transaction appears to be for recurring services
        """
        if not transaction.description:
            return False
        
        desc = transaction.description.lower()
        
        recurring_indicators = [
            'monthly', 'quarterly', 'annual', 'subscription',
            'maintenance', 'support', 'hosting', 'license'
        ]
        
        return any(indicator in desc for indicator in recurring_indicators)
    
    def _create_finding(self, transaction: Transaction, finding_type: str, 
                       description: str, risk_level: str) -> Dict[str, Any]:
        """
        Create a finding dictionary
        """
        return {
            'transaction': transaction,
            'finding_type': finding_type,
            'description': description,
            'amount': transaction.amount,
            'risk_level': risk_level
        }
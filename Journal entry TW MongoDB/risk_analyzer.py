import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class RiskAnalyzer:
    """Analyzes journal entries for risk factors"""
    
    def __init__(self):
        self.default_keywords = ['adjusting', 'reversal', 'year-end', 'correction', 'accrual', 'manual']
        self.suspense_accounts = ['suspense', 'clearing', 'temp', 'temporary', 'unassigned']
        self.high_risk_accounts = ['revenue', 'sales', 'equity', 'retained earnings']
    
    def build_population(self, gl_data, high_risk_keywords=None, period_end_window=7, investigate_threshold=1000):
        """
        Add risk flags to journal entry population
        Returns: DataFrame with risk assessment columns
        """
        if high_risk_keywords is None:
            high_risk_keywords = self.default_keywords
        
        df = gl_data.copy()
        
        # Initialize risk flags
        df['keyword_hit'] = False
        df['period_end_window'] = False
        df['manual_or_admin_user'] = False
        df['round_amount'] = False
        df['suspense_account'] = False
        df['large_amount'] = False
        df['high_risk_account'] = False
        df['unusual_timing'] = False
        df['split_entry'] = False
        
        # Apply risk heuristics
        df = self._flag_keyword_hits(df, high_risk_keywords)
        df = self._flag_period_end_entries(df, period_end_window)
        df = self._flag_manual_entries(df)
        df = self._flag_round_amounts(df)
        df = self._flag_suspense_accounts(df)
        df = self._flag_large_amounts(df, investigate_threshold)
        df = self._flag_high_risk_accounts(df)
        df = self._flag_unusual_timing(df)
        df = self._flag_split_entries(df)
        
        # Calculate overall risk score
        df['risk_score'] = self._calculate_risk_score(df)
        df['risk_category'] = self._categorize_risk(df)
        
        logger.info(f"Risk analysis complete. {len(df)} entries analyzed.")
        logger.info(f"Risk breakdown: {df['risk_category'].value_counts().to_dict()}")
        
        return df
    
    def _flag_keyword_hits(self, df, keywords):
        """Flag entries with high-risk keywords in description"""
        if 'description' in df.columns:
            pattern = '|'.join(keywords)
            # Convert to string first to handle NaN and numeric values
            df['keyword_hit'] = df['description'].astype(str).str.contains(pattern, case=False, na=False)
            logger.info(f"Keyword hits: {df['keyword_hit'].sum()}")
        return df
    
    def _flag_period_end_entries(self, df, window_days):
        """Flag entries posted near period end"""
        if 'date' in df.columns and not df['date'].isna().all():
            # Assume period end is last day of month for each entry's month
            df['month_end'] = df['date'].dt.to_period('M').dt.end_time
            df['days_from_period_end'] = (df['date'] - df['month_end']).dt.days
            df['period_end_window'] = df['days_from_period_end'].abs() <= window_days
            logger.info(f"Period-end entries: {df['period_end_window'].sum()}")
        return df
    
    def _flag_manual_entries(self, df):
        """Flag entries by manual/admin users"""
        if 'user' in df.columns:
            manual_patterns = ['manual', 'admin', 'system', 'auto', 'batch']
            pattern = '|'.join(manual_patterns)
            # Convert to string first to handle NaN and numeric values
            df['manual_or_admin_user'] = df['user'].astype(str).str.contains(pattern, case=False, na=False)
            logger.info(f"Manual/admin entries: {df['manual_or_admin_user'].sum()}")
        return df
    
    def _flag_round_amounts(self, df):
        """Flag entries with round amounts (ending in 00 or 000)"""
        if 'net' in df.columns:
            abs_net = df['net'].abs()
            df['round_amount'] = (
                (abs_net % 1000 == 0) & (abs_net > 0) |  # Round thousands
                (abs_net % 100 == 0) & (abs_net >= 500)   # Round hundreds above $500
            )
            logger.info(f"Round amount entries: {df['round_amount'].sum()}")
        return df
    
    def _flag_suspense_accounts(self, df):
        """Flag entries to/from suspense accounts"""
        if 'account' in df.columns:
            pattern = '|'.join(self.suspense_accounts)
            # Already has astype(str) - keep it
            df['suspense_account'] = df['account'].astype(str).str.contains(pattern, case=False, na=False)
            logger.info(f"Suspense account entries: {df['suspense_account'].sum()}")
        return df
    
    def _flag_large_amounts(self, df, threshold):
        """Flag entries above materiality threshold"""
        if 'net' in df.columns:
            df['large_amount'] = df['net'].abs() >= threshold
            logger.info(f"Large amount entries (>= ${threshold:,}): {df['large_amount'].sum()}")
        return df
    
    def _flag_high_risk_accounts(self, df):
        """Flag entries affecting high-risk accounts"""
        if 'account' in df.columns:
            pattern = '|'.join(self.high_risk_accounts)
            # Already has astype(str) - keep it
            df['high_risk_account'] = df['account'].astype(str).str.contains(pattern, case=False, na=False)
            logger.info(f"High-risk account entries: {df['high_risk_account'].sum()}")
        return df
    
    def _flag_unusual_timing(self, df):
        """Flag entries posted at unusual times (weekends, after hours)"""
        if 'date' in df.columns and not df['date'].isna().all():
            # Flag weekend postings
            df['unusual_timing'] = df['date'].dt.weekday >= 5  # Saturday=5, Sunday=6
            logger.info(f"Unusual timing entries: {df['unusual_timing'].sum()}")
        return df
    
    def _flag_split_entries(self, df):
        """Flag potentially split entries (same doc_no, different accounts)"""
        if 'doc_no' in df.columns and 'account' in df.columns:
            # Convert to string to handle NaN values
            doc_account_counts = df.groupby(df['doc_no'].astype(str))['account'].nunique()
            split_docs = doc_account_counts[doc_account_counts > 2].index
            df['split_entry'] = df['doc_no'].astype(str).isin(split_docs)
            logger.info(f"Split entries: {df['split_entry'].sum()}")
        return df
    
    def _calculate_risk_score(self, df):
        """Calculate overall risk score based on flags"""
        risk_weights = {
            'keyword_hit': 3,
            'period_end_window': 2,
            'manual_or_admin_user': 1,
            'round_amount': 2,
            'suspense_account': 3,
            'large_amount': 2,
            'high_risk_account': 2,
            'unusual_timing': 1,
            'split_entry': 1
        }
        
        risk_score = pd.Series(0, index=df.index)
        
        for flag, weight in risk_weights.items():
            if flag in df.columns:
                risk_score += df[flag].astype(int) * weight
        
        return risk_score
    
    def _categorize_risk(self, df):
        """Categorize entries by risk level"""
        conditions = [
            (df['risk_score'] >= 8),
            (df['risk_score'] >= 4),
            (df['risk_score'] >= 1),
            (df['risk_score'] == 0)
        ]
        
        choices = ['Critical', 'High Risk', 'Medium Risk', 'Low Risk']
        
        return pd.Series(
            np.select(conditions, choices, default='Low Risk'),
            index=df.index
        )

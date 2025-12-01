import pandas as pd
import numpy as np
import logging
from sklearn.utils import resample

logger = logging.getLogger(__name__)

class SampleSelector:
    """Selects journal entry samples using risk-based and random selection"""
    
    def __init__(self):
        self.random_state = 42  # For reproducible sampling
    
    def select_samples(self, population, coverage_target=0.8, materiality=10000, max_sample_size=150):
        """
        Select samples from population using risk-based approach
        
        Args:
            population: DataFrame with risk flags and scores
            coverage_target: Target coverage percentage (0.0-1.0)
            materiality: Materiality threshold
            max_sample_size: Maximum number of samples to select
        
        Returns:
            DataFrame of selected samples with selection rationale
        """
        if population.empty:
            logger.warning("Empty population provided")
            return pd.DataFrame()
        
        samples = []
        selection_rationale = []
        
        # Step 1: Select all critical and high-risk items
        high_risk_items = population[
            population['risk_category'].isin(['Critical', 'High Risk'])
        ].copy()
        
        if not high_risk_items.empty:
            high_risk_items['selection_method'] = 'High Risk - All Selected'
            high_risk_items['selection_rationale'] = high_risk_items.apply(
                self._create_risk_rationale, axis=1
            )
            samples.append(high_risk_items)
            logger.info(f"Selected {len(high_risk_items)} high-risk items")
        
        # Step 2: Calculate remaining sample size needed for coverage
        remaining_population = population[
            ~population['risk_category'].isin(['Critical', 'High Risk'])
        ]
        
        current_sample_count = len(high_risk_items) if not high_risk_items.empty else 0
        remaining_sample_needed = min(
            max_sample_size - current_sample_count,
            int(len(remaining_population) * coverage_target)
        )
        
        if remaining_sample_needed > 0 and not remaining_population.empty:
            # Step 3: Stratified random sampling from remaining population
            stratified_samples = self._stratified_random_selection(
                remaining_population,
                remaining_sample_needed
            )
            
            if not stratified_samples.empty:
                samples.append(stratified_samples)
                logger.info(f"Selected {len(stratified_samples)} additional random samples")
        
        # Combine all samples
        if samples:
            final_samples = pd.concat(samples, ignore_index=True)
            
            # Add sample sequence numbers
            final_samples['sample_id'] = range(1, len(final_samples) + 1)
            final_samples['sample_id'] = final_samples['sample_id'].apply(lambda x: f"S{x:03d}")
            
        else:
            final_samples = pd.DataFrame()
        
        # Log summary
        if not final_samples.empty:
            logger.info(f"Total samples selected: {len(final_samples)}")
            logger.info(f"Coverage achieved: {len(final_samples)/len(population)*100:.1f}%")
            logger.info(f"Selection breakdown: {final_samples['selection_method'].value_counts().to_dict()}")
        
        return final_samples
    
    def _create_risk_rationale(self, row):
        """Create rationale text for high-risk selection"""
        risk_flags = []
        
        flag_descriptions = {
            'keyword_hit': 'Contains high-risk keywords',
            'period_end_window': 'Posted near period-end',
            'manual_or_admin_user': 'Manual/admin user entry',
            'round_amount': 'Round dollar amount',
            'suspense_account': 'Suspense account involved',
            'large_amount': 'Above materiality threshold',
            'high_risk_account': 'High-risk account affected',
            'unusual_timing': 'Unusual posting timing',
            'split_entry': 'Part of split entry'
        }
        
        for flag, description in flag_descriptions.items():
            if flag in row.index and row[flag]:
                risk_flags.append(description)
        
        if risk_flags:
            return f"Risk Score: {row.get('risk_score', 0)}. Flags: {'; '.join(risk_flags)}"
        else:
            return f"Risk Score: {row.get('risk_score', 0)}"
    
    def _stratified_random_selection(self, population, sample_size):
        """Perform stratified random sampling"""
        
        # Define strata based on amount ranges
        population = population.copy()
        population['amount_stratum'] = self._create_amount_strata(population)
        
        samples = []
        
        # Calculate samples per stratum
        stratum_counts = population['amount_stratum'].value_counts()
        stratum_proportions = stratum_counts / len(population)
        
        for stratum, proportion in stratum_proportions.items():
            stratum_data = population[population['amount_stratum'] == stratum]
            stratum_sample_size = max(1, int(sample_size * proportion))
            
            # Ensure we don't sample more than available
            stratum_sample_size = min(stratum_sample_size, len(stratum_data))
            
            if stratum_sample_size > 0:
                stratum_sample = resample(
                    stratum_data,
                    n_samples=stratum_sample_size,
                    random_state=self.random_state,
                    replace=False
                )
                
                stratum_sample['selection_method'] = f'Random - {stratum} Stratum'
                stratum_sample['selection_rationale'] = f'Randomly selected from {stratum.lower()} amount stratum'
                
                samples.append(stratum_sample)
        
        if samples:
            return pd.concat(samples, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def _create_amount_strata(self, population):
        """Create amount-based strata for stratified sampling"""
        if 'net' not in population.columns:
            return pd.Series('Single Stratum', index=population.index)
        
        abs_amounts = population['net'].abs()
        
        conditions = [
            (abs_amounts >= 100000),
            (abs_amounts >= 25000),
            (abs_amounts >= 5000),
            (abs_amounts >= 1000),
            (abs_amounts < 1000)
        ]
        
        choices = [
            'Very Large (≥$100K)',
            'Large ($25K-$100K)',
            'Medium ($5K-$25K)',
            'Small ($1K-$5K)',
            'Very Small (<$1K)'
        ]
        
        return pd.Series(
            np.select(conditions, choices, default='Very Small (<$1K)'),
            index=population.index
        )

import random
from typing import Dict, Any, List, Tuple
from models import GLPopulation, Sample, Run, db
from config import Config
import logging

class SamplingService:
    """Handle sample selection and stratification"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = Config()
    
    def generate_samples(self, run_id: int) -> Dict[str, Any]:
        """Generate stratified samples for a run"""
        try:
            run = Run.query.get(run_id)
            if not run:
                return {'success': False, 'error': 'Run not found'}
            
            # Clear existing samples
            Sample.query.filter_by(run_id=run_id).delete()
            db.session.commit()
            
            # Get R&M population
            rm_population = self._filter_rm_population(run_id)
            
            if not rm_population:
                return {'success': False, 'error': 'No R&M items found in population'}
            
            # Apply capitalization threshold
            auto_include_items, remaining_items = self._apply_threshold(rm_population, run.capitalization_threshold)
            
            # Automatically include items above threshold
            auto_samples = self._create_auto_samples(run_id, auto_include_items)
            
            # Stratify remaining items
            stratified_samples = self._create_stratified_samples(run_id, remaining_items)
            
            total_samples = len(auto_samples) + len(stratified_samples)
            
            # Calculate metrics
            total_population = len(rm_population)
            total_amount = sum(item.amount for item in rm_population)
            sampled_amount = sum(sample.gl_item.amount for sample in auto_samples + stratified_samples)
            
            metrics = {
                'sampling': {
                    'total_population': total_population,
                    'rm_population': len(rm_population),
                    'auto_included': len(auto_samples),
                    'stratified_samples': len(stratified_samples),
                    'total_samples': total_samples,
                    'population_amount': total_amount,
                    'sampled_amount': sampled_amount,
                    'coverage_percentage': (sampled_amount / total_amount * 100) if total_amount > 0 else 0,
                    'sampling_rate': (total_samples / len(rm_population) * 100) if rm_population else 0
                }
            }
            
            return {
                'success': True,
                'metrics': metrics,
                'message': f'Generated {total_samples} samples ({len(auto_samples)} auto-included, {len(stratified_samples)} stratified)'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f'Sampling error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def _filter_rm_population(self, run_id: int) -> List[GLPopulation]:
        """Filter GL population for R&M accounts"""
        run = Run.query.get(run_id)
        allowed_accounts = run.allowed_accounts.split(';') if run.allowed_accounts else self.config.ALLOWED_ACCOUNTS
        
        # Build filter conditions for account names containing R&M terms
        rm_items = []
        all_items = GLPopulation.query.filter_by(run_id=run_id).all()
        
        for item in all_items:
            account_name = (item.account_name or '').lower()
            description = (item.description or '').lower()
            
            # Check if account name or description contains any allowed account terms
            for allowed_term in allowed_accounts:
                if allowed_term.lower() in account_name or allowed_term.lower() in description:
                    rm_items.append(item)
                    break
        
        return rm_items
    
    def _apply_threshold(self, population: List[GLPopulation], threshold: float) -> Tuple[List[GLPopulation], List[GLPopulation]]:
        """Split population by capitalization threshold"""
        auto_include = [item for item in population if item.amount >= threshold]
        remaining = [item for item in population if item.amount < threshold]
        
        return auto_include, remaining
    
    def _create_auto_samples(self, run_id: int, items: List[GLPopulation]) -> List[Sample]:
        """Create samples for auto-included items"""
        samples = []
        
        for item in items:
            sample = Sample(
                run_id=run_id,
                gl_id=item.id,
                sample_type='auto_included',
                stratum='above_threshold',
                selection_reason=f'Amount {item.amount:,.2f} exceeds capitalization threshold'
            )
            
            db.session.add(sample)
            samples.append(sample)
        
        db.session.commit()
        return samples
    
    def _create_stratified_samples(self, run_id: int, items: List[GLPopulation]) -> List[Sample]:
        """Create stratified samples from remaining items"""
        if not items:
            return []
        
        # Group items by strata
        strata = {}
        for item in items:
            stratum = self._get_stratum(item.amount)
            if stratum not in strata:
                strata[stratum] = []
            strata[stratum].append(item)
        
        samples = []
        
        # Sample from each stratum
        for stratum_key, stratum_items in strata.items():
            sample_size = self._get_sample_size(stratum_key)
            
            # Deterministic sampling using amount as seed for consistency
            stratum_items.sort(key=lambda x: x.amount, reverse=True)
            random.seed(sum(int(item.amount * 100) for item in stratum_items[:10]))  # Use top 10 amounts as seed
            
            selected_items = random.sample(stratum_items, min(sample_size, len(stratum_items)))
            
            for item in selected_items:
                sample = Sample(
                    run_id=run_id,
                    gl_id=item.id,
                    sample_type='stratified',
                    stratum=f'{stratum_key[0]:.0f}-{stratum_key[1]:.0f}' if stratum_key[1] != float('inf') else f'{stratum_key[0]:.0f}+',
                    selection_reason=f'Stratified sampling from {len(stratum_items)} items in stratum'
                )
                
                db.session.add(sample)
                samples.append(sample)
        
        db.session.commit()
        return samples
    
    def _get_stratum(self, amount: float) -> Tuple[float, float]:
        """Determine stratum for an amount"""
        for low, high in self.config.STRATIFICATION_BANDS:
            if low <= amount < high:
                return (low, high)
        return self.config.STRATIFICATION_BANDS[-1]  # Default to highest stratum
    
    def _get_sample_size(self, stratum: Tuple[float, float]) -> int:
        """Get sample size for a stratum"""
        return self.config.SAMPLE_SIZES.get(stratum, 5)  # Default to 5 if not found
    
    def get_sampling_summary(self, run_id: int) -> Dict[str, Any]:
        """Get sampling summary for a run"""
        try:
            run = Run.query.get(run_id)
            if not run or not run.metrics:
                return {'success': False, 'error': 'No sampling data available'}
            
            sampling_metrics = run.metrics.get('sampling', {})
            
            # Get sample details
            samples = Sample.query.filter_by(run_id=run_id).all()
            
            # Group by type and stratum
            sample_breakdown = {}
            for sample in samples:
                key = f"{sample.sample_type}_{sample.stratum}"
                if key not in sample_breakdown:
                    sample_breakdown[key] = {
                        'type': sample.sample_type,
                        'stratum': sample.stratum,
                        'count': 0,
                        'total_amount': 0
                    }
                sample_breakdown[key]['count'] += 1
                sample_breakdown[key]['total_amount'] += sample.gl_item.amount
            
            return {
                'success': True,
                'summary': sampling_metrics,
                'breakdown': list(sample_breakdown.values())
            }
            
        except Exception as e:
            self.logger.error(f'Get sampling summary error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_sample_selection(self, run_id: int) -> Dict[str, Any]:
        """Validate that sample selection follows business rules"""
        try:
            run = Run.query.get(run_id)
            samples = Sample.query.filter_by(run_id=run_id).all()
            
            validation_results = {
                'threshold_compliance': True,
                'stratification_coverage': True,
                'issues': []
            }
            
            # Check threshold compliance
            for sample in samples:
                if sample.sample_type == 'auto_included':
                    if sample.gl_item.amount < run.capitalization_threshold:
                        validation_results['threshold_compliance'] = False
                        validation_results['issues'].append(
                            f'Sample {sample.id} marked as auto-included but amount {sample.gl_item.amount} below threshold'
                        )
            
            # Check for items above threshold not included
            rm_population = self._filter_rm_population(run_id)
            above_threshold = [item for item in rm_population if item.amount >= run.capitalization_threshold]
            sampled_above_threshold = [s for s in samples if s.sample_type == 'auto_included']
            
            if len(above_threshold) != len(sampled_above_threshold):
                validation_results['threshold_compliance'] = False
                validation_results['issues'].append(
                    f'Mismatch in above-threshold items: {len(above_threshold)} found, {len(sampled_above_threshold)} sampled'
                )
            
            validation_results['valid'] = validation_results['threshold_compliance'] and validation_results['stratification_coverage']
            
            return {
                'success': True,
                'validation': validation_results
            }
            
        except Exception as e:
            self.logger.error(f'Validate sample selection error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }

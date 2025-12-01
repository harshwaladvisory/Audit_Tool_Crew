import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GeminiIntegration:
    """Optional Gemini API integration for memo generation"""
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Gemini API client initialized")
            except ImportError:
                logger.warning("Gemini API library not available")
            except Exception as e:
                logger.error(f"Error initializing Gemini client: {str(e)}")
    
    def generate_summary_memo(self, population, samples, output_files):
        """Generate audit summary memo using Gemini API"""
        
        if not self.client:
            logger.info("Gemini API not available - generating basic memo")
            return self._generate_basic_memo(population, samples, output_files)
        
        try:
            # Prepare data summary for Gemini
            summary_data = self._prepare_summary_data(population, samples)
            
            prompt = self._create_memo_prompt(summary_data)
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            if response.text:
                memo_content = self._format_memo_output(response.text, summary_data)
                logger.info("Generated memo using Gemini API")
                return memo_content
            else:
                logger.warning("Empty response from Gemini API")
                return self._generate_basic_memo(population, samples, output_files)
                
        except Exception as e:
            logger.error(f"Error using Gemini API: {str(e)}")
            return self._generate_basic_memo(population, samples, output_files)
    
    def _prepare_summary_data(self, population, samples):
        """Prepare factual data summary for memo generation"""
        return {
            'population_count': len(population),
            'sample_count': len(samples) if not samples.empty else 0,
            'risk_breakdown': population['risk_category'].value_counts().to_dict() if 'risk_category' in population.columns else {},
            'selection_methods': samples['selection_method'].value_counts().to_dict() if not samples.empty and 'selection_method' in samples.columns else {},
            'date_range': {
                'start': population['date'].min().strftime('%Y-%m-%d') if 'date' in population.columns and not population['date'].isna().all() else 'N/A',
                'end': population['date'].max().strftime('%Y-%m-%d') if 'date' in population.columns and not population['date'].isna().all() else 'N/A'
            },
            'amount_summary': {
                'total': float(population['net'].sum()) if 'net' in population.columns else 0,
                'average': float(population['net'].mean()) if 'net' in population.columns else 0,
                'largest': float(population['net'].abs().max()) if 'net' in population.columns else 0
            }
        }
    
    def _create_memo_prompt(self, summary_data):
        """Create prompt for Gemini memo generation"""
        return f"""
        Write a professional audit summary memo for journal entry sampling and testing work. Use only the factual data provided below - do not create or assume any additional numbers or results.

        FACTUAL DATA:
        - Population: {summary_data['population_count']} journal entries
        - Sample Size: {summary_data['sample_count']} entries selected
        - Risk Categories: {summary_data['risk_breakdown']}
        - Selection Methods: {summary_data['selection_methods']}
        - Date Range: {summary_data['date_range']['start']} to {summary_data['date_range']['end']}
        - Total Amount: ${summary_data['amount_summary']['total']:,.2f}
        - Average Entry: ${summary_data['amount_summary']['average']:,.2f}
        - Largest Entry: ${summary_data['amount_summary']['largest']:,.2f}

        The memo should:
        1. Summarize the scope and approach
        2. Present the factual findings using only the data above
        3. Note that detailed testing results are pending
        4. Be professional and suitable for audit documentation
        5. Not speculate about test results or create fictional exceptions

        Format as a standard business memo with proper headings.
        """
    
    def _format_memo_output(self, gemini_response, summary_data):
        """Format the Gemini response into final memo"""
        current_date = datetime.now().strftime('%B %d, %Y')
        
        memo_header = f"""# MEMORANDUM

**TO:** Audit File
**FROM:** Journal Entry Sampling & Testwork Agent
**DATE:** {current_date}
**RE:** Journal Entry Population Analysis and Sample Selection

---

"""
        
        memo_footer = f"""

---

## Supporting Documentation
The following workpapers have been prepared to support this analysis:
- JE_Population.xlsx - Complete population analysis
- JE_Sample_Selection.xlsx - Sample selection details
- JE_Request_List.xlsx - PBC requests for selected samples
- JE_Test_Workpaper.xlsx - Testing template
- JE_Exceptions_Log.xlsx - Exception tracking
- Proposed_AJEs.xlsx - Adjusting entries template

## Next Steps
1. Obtain supporting documentation from client
2. Perform detailed attribute testing on selected samples
3. Document exceptions and proposed adjusting entries
4. Complete supervisory review

---
*This memo was generated on {current_date} using automated journal entry analysis tools.*
"""
        
        return memo_header + gemini_response + memo_footer
    
    def _generate_basic_memo(self, population, samples, output_files):
        """Generate basic memo without Gemini API"""
        current_date = datetime.now().strftime('%B %d, %Y')
        
        # Calculate basic statistics
        pop_count = len(population)
        sample_count = len(samples) if not samples.empty else 0
        
        risk_breakdown = population['risk_category'].value_counts().to_dict() if 'risk_category' in population.columns else {}
        
        date_range = "N/A"
        if 'date' in population.columns and not population['date'].isna().all():
            start_date = population['date'].min().strftime('%Y-%m-%d')
            end_date = population['date'].max().strftime('%Y-%m-%d')
            date_range = f"{start_date} to {end_date}"
        
        total_amount = population['net'].sum() if 'net' in population.columns else 0
        
        memo_content = f"""# MEMORANDUM

**TO:** Audit File
**FROM:** Journal Entry Sampling & Testwork Agent
**DATE:** {current_date}
**RE:** Journal Entry Population Analysis and Sample Selection

---

## Executive Summary

This memo summarizes the journal entry population analysis and sample selection procedures performed for the current audit period.

## Scope and Approach

We analyzed the general ledger data to identify journal entries and applied risk-based sampling procedures to select items for detailed testing. Our approach included:

1. **Population Building:** Identified {pop_count:,} journal entries from the general ledger
2. **Risk Assessment:** Applied automated risk heuristics to flag high-risk entries
3. **Sample Selection:** Selected {sample_count} entries using risk-based and random selection methods

## Population Analysis

**Period Covered:** {date_range}
**Total Journal Entries:** {pop_count:,}
**Total Net Amount:** ${total_amount:,.2f}

### Risk Classification:
"""
        
        for risk_level, count in risk_breakdown.items():
            memo_content += f"- **{risk_level}:** {count:,} entries\n"
        
        memo_content += f"""

## Sample Selection Results

**Total Samples Selected:** {sample_count}
**Selection Approach:** Risk-based with random supplemental selection

All high-risk and critical entries were selected for testing, with additional random samples to achieve appropriate coverage of the population.

## Status and Next Steps

**Current Status:** Sample selection complete, testing procedures ready to begin

**Immediate Next Steps:**
1. Request supporting documentation from client (PBC list generated)
2. Perform attribute testing on selected samples
3. Document any exceptions or findings
4. Prepare adjusting journal entries as needed

## Supporting Documentation

The following workpapers support this analysis:
"""
        
        for file in output_files:
            memo_content += f"- {file}\n"
        
        memo_content += f"""

---
*This memo was generated on {current_date} using automated journal entry analysis procedures.*
"""
        
        return memo_content

import os
import logging
from typing import Optional

# Optional Gemini integration
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GEMINI_AVAILABLE = False
    logging.warning("Gemini integration not available - install google-genai package")

class GeminiIntegrator:
    """Integration with Google Gemini for memo drafting and text polishing"""
    
    def __init__(self):
        self.client = None
        
        if GEMINI_AVAILABLE:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key and genai:
                try:
                    self.client = genai.Client(api_key=api_key)
                    logging.info("Gemini client initialized successfully")
                except Exception as e:
                    logging.warning(f"Gemini client initialization failed: {str(e)}")
            else:
                logging.info("GEMINI_API_KEY not found - Gemini features disabled")
    
    def polish_memo(self, memo_content: str) -> Optional[str]:
        """Polish the summary memo using Gemini"""
        if not self.client:
            return None
        
        try:
            prompt = f"""Please polish the following audit memo to improve clarity and professional tone while maintaining all financial figures and technical content exactly as provided. Do not invent or modify any numbers:

{memo_content}

Instructions:
- Maintain all numerical values exactly as provided
- Improve sentence structure and flow
- Use professional audit terminology
- Keep the same structure and sections
- Do not add new financial data or conclusions"""

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for more conservative output
                    max_output_tokens=4000
                ) if types else None
            )

            if response.text:
                logging.info("Memo successfully polished using Gemini")
                return response.text
            
        except Exception as e:
            logging.error(f"Gemini memo polishing error: {str(e)}")
        
        return None
    
    def generate_test_narrative(self, test_results: list) -> Optional[str]:
        """Generate narrative descriptions of test results"""
        if not self.client:
            return None
        
        try:
            # Prepare test summary for Gemini
            test_summary = []
            for result in test_results:
                for test_name, test_data in result.get('Tests', {}).items():
                    test_summary.append({
                        'test': test_name,
                        'status': test_data.get('Status', 'N/A'),
                        'exception': test_data.get('Exception', False)
                    })
            
            prompt = f"""Based on the following audit test results, write a professional narrative summary for inclusion in audit workpapers. Focus on the procedures performed and results obtained:

Test Results Summary: {test_summary}

Write 2-3 paragraphs describing:
1. The testing procedures that were performed
2. Overall results and any patterns observed
3. Exceptions noted and their significance

Use professional audit language and maintain objectivity."""

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1000
                ) if types else None
            )

            if response.text:
                logging.info("Test narrative generated using Gemini")
                return response.text
                
        except Exception as e:
            logging.error(f"Gemini test narrative error: {str(e)}")
        
        return None
    
    def is_available(self) -> bool:
        """Check if Gemini integration is available and configured"""
        return self.client is not None

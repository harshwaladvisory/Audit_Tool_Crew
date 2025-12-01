import json
import logging
import os
from typing import Optional, Dict, Any
import requests

from google import genai
from google.genai import types
from pydantic import BaseModel


# IMPORTANT: KEEP THIS COMMENT
# Follow these instructions when using this blueprint:
# - Note that the newest Gemini model series is "gemini-2.5-flash" or gemini-2.5-pro"
#   - do not change this unless explicitly requested by the user
# - Sometimes the google genai SDK has occasional type errors. You might need to run to validate, at time.  
# The SDK was recently renamed from google-generativeai to google-genai. This file reflects the new name and the new APIs.

# This API key is from Gemini Developer API Key, not vertex AI API Key
def get_gemini_client():
    """Get Gemini client with proper API key from environment"""
    # FIXED: Read from GEMINI_API_KEY environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        logging.warning("GEMINI_API_KEY not found in environment variables")
        return None
    
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        logging.error(f"Failed to create Gemini client: {e}")
        return None


class VendorClassificationResult(BaseModel):
    classification: str
    form: str
    reason: str
    confidence: float


def classify_vendor_with_gemini(vendor_name: str, vendor_id: str, total_paid: float, accounts: str) -> Optional[VendorClassificationResult]:
    """Classify vendor using Gemini AI with 2024 IRS 1099 rules"""
    try:
        client = get_gemini_client()
        if not client:
            logging.info("Gemini client not available, skipping Gemini classification")
            return None
            
        prompt = f"""
        You are an AI-powered 1099 Vendor Eligibility Assistant. Analyze this vendor for accurate 2024 IRS 1099 form classification:
        
        Vendor Name: {vendor_name}
        SSN/EIN No.: {vendor_id}
        Total Paid: ${total_paid:,.2f}
        Accounts: {accounts}
        
        **STRICT 1099-ELIGIBLE REQUIREMENTS - ALL MUST BE MET:**
        1. **MUST have SSN/EIN/Tax ID present** (not empty/missing)
        2. **MUST be $600+ payment**
        3. **MUST be for SERVICES only** (not goods/products/equipment)
        
        Apply these 2024 IRS 1099 rules with STRICT service-only focus:
        
        1099-ELIGIBLE (1099-NEC) - ALL requirements must be met:
        - Has SSN/EIN/Tax ID provided
        - $600+ threshold 
        - SERVICE PROVIDERS ONLY: consultants, contractors, freelancers, professional services
        - Sole proprietors providing services
        - Single-member LLCs providing services
        - Partnerships providing services
        - ATTORNEYS/LAW FIRMS (even if corporations - exception for legal services)
        
        1099-ELIGIBLE (1099-MISC) - ALL requirements must be met:
        - Has SSN/EIN/Tax ID provided
        - $600+ for rents, prizes, awards (service-related payments)
        - $10+ for royalties or broker payments
        - Medical/healthcare SERVICE payments to corporations
        
        **ACCOUNT CODE ANALYSIS FOR SERVICES vs GOODS:**
        - SERVICES: consulting, professional fees, maintenance, repair, legal, accounting, marketing, advertising, rent, utilities-service
        - GOODS/PRODUCTS (exclude from 1099): inventory, equipment, supplies, materials, merchandise, products, parts, tools, furniture, software licenses
        
        **AUTOMATICALLY NON-REPORTABLE (never need W9):**
        - C-Corporations and S-Corporations: Inc., Corp., Corporation, Incorporated (except attorney fees)
        - Government entities: EFTPS, IRS, State, Federal, Treasury, Government
        - Banks and financial institutions: PNC, Chase, Bank of America, Wells Fargo, etc.
        - Payroll services: QuickBooks Payroll, ADP, Paychex, Gusto, etc.
        - Insurance companies: Any insurance provider
        - Utilities: Electric, gas, water, telecom companies
        - Credit card companies and merchant services
        - Payments under $600 annually (except royalties under $10)
        - Payments for GOODS/PRODUCTS/EQUIPMENT (even if $600+)
        - Employee wages (use W-2)
        - Foreign vendors
        
        W-9 REQUIRED (ONLY when we cannot determine entity type):
        - Missing/empty Tax ID AND cannot determine if corporation/government/bank
        - Has unclear business name AND no Tax ID
        - Could be service provider but need W9 to confirm entity classification
        
        **CRITICAL:** Only classify as "1099-Eligible" if vendor has Tax ID AND payment is $600+ AND it's clearly for SERVICES (not goods/products).
        
        Classify into exactly one category:
        - "1099-Eligible": Requires 1099 filing (must meet ALL requirements above)
        - "Non-Reportable": No 1099 required
        - "W-9 Required": Need more vendor information
        
        Respond with JSON in this exact format:
        {{
            "classification": "1099-Eligible or Non-Reportable or W-9 Required",
            "form": "1099-NEC or 1099-MISC or Not Required or W-9 Needed",
            "reason": "specific explanation including Tax ID status, amount, and service vs goods analysis",
            "confidence": 0.95
        }}
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VendorClassificationResult,
            ),
        )

        raw_json = response.text
        if raw_json:
            data = json.loads(raw_json)
            return VendorClassificationResult(**data)
        else:
            raise ValueError("Empty response from Gemini")

    except Exception as e:
        logging.error(f"Gemini classification failed for {vendor_name}: {e}")
        return None


def classify_vendor_with_ollama(vendor_name: str, vendor_id: str, total_paid: float, accounts: str) -> Optional[VendorClassificationResult]:
    """Fallback classification using local Ollama with 2024 IRS rules"""
    try:
        # Try different models in order of preference
        models = ["gpt-oss", "gemma2:7b", "mistral:7b"]
        
        prompt = f"""
        You are an AI-powered 1099 Vendor Eligibility Assistant. Analyze this vendor for accurate 2024 IRS 1099 form classification:
        
        Vendor Name: {vendor_name}
        SSN/EIN No.: {vendor_id}
        Total Paid: ${total_paid:,.2f}
        Accounts: {accounts}
        
        **STRICT 1099-ELIGIBLE REQUIREMENTS - ALL MUST BE MET:**
        1. **MUST have SSN/EIN/Tax ID present** (not empty/missing)
        2. **MUST be $600+ payment**
        3. **MUST be for SERVICES only** (not goods/products/equipment)
        
        2024 IRS 1099 Rules with STRICT service-only focus:
        
        1099-ELIGIBLE (1099-NEC) - ALL requirements must be met:
        - Has SSN/EIN/Tax ID provided
        - $600+ threshold
        - SERVICE PROVIDERS ONLY: consultants, contractors, freelancers, professional services
        - Sole proprietors providing services
        - Single-member LLCs providing services
        - ATTORNEYS/LAW FIRMS (even corporations - exception for legal services)
        
        1099-ELIGIBLE (1099-MISC) - ALL requirements must be met:
        - Has SSN/EIN/Tax ID provided
        - $600+ for rents, prizes, awards (service-related payments)
        - $10+ royalties, broker payments
        - Medical/healthcare SERVICE payments to corporations
        
        **ACCOUNT CODE ANALYSIS:**
        - SERVICES: consulting, professional fees, maintenance, repair, legal, accounting, marketing, advertising, rent
        - GOODS/PRODUCTS (exclude from 1099): inventory, equipment, supplies, materials, merchandise, products, parts, tools, furniture
        
        **AUTOMATICALLY NON-REPORTABLE (never need W9):**
        - C-Corporations and S-Corporations: Inc., Corp., Corporation, Incorporated (except attorney fees)
        - Government entities: EFTPS, IRS, State, Federal, Treasury, Government
        - Banks and financial institutions: PNC, Chase, Bank of America, Wells Fargo, etc.
        - Payroll services: QuickBooks Payroll, ADP, Paychex, Gusto, etc.
        - Insurance companies, utilities, credit card companies
        - Under $600 annually (except royalties under $10)
        - Payments for GOODS/PRODUCTS/EQUIPMENT (even if $600+)
        
        W-9 REQUIRED (ONLY when we cannot determine entity type):
        - Missing/empty Tax ID AND cannot determine if corporation/government/bank
        - Has unclear business name AND no Tax ID
        - Could be service provider but need W9 to confirm entity classification
        
        **CRITICAL:** Only classify as "1099-Eligible" if vendor has Tax ID AND payment is $600+ AND it's clearly for SERVICES (not goods/products).
        
        Classify as: "1099-Eligible", "Non-Reportable", or "W-9 Required"
        
        JSON format:
        {{
            "classification": "1099-Eligible or Non-Reportable or W-9 Required",
            "form": "1099-NEC or 1099-MISC or Not Required or W-9 Needed",
            "reason": "explanation including Tax ID status, amount, and service vs goods analysis",
            "confidence": 0.85
        }}
        """
        
        for model in models:
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    },
                    timeout=5  # REDUCED from 30 to 5 seconds
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'response' in result:
                        data = json.loads(result['response'])
                        return VendorClassificationResult(**data)
                        
            except (requests.RequestException, json.JSONDecodeError, Exception) as e:
                logging.debug(f"Ollama attempt with {model} failed: {e}")
                continue
                
        logging.info("Ollama not available, using fallback classification")
        return None
        
    except Exception as e:
        logging.error(f"Ollama classification failed: {e}")
        return None


def classify_vendor_fallback(vendor_name: str, vendor_id: str, total_paid: float, accounts: str) -> VendorClassificationResult:
    """Fallback classification using 2024 IRS rule-based logic with STRICT requirements"""
    vendor_lower = vendor_name.lower()
    accounts_lower = accounts.lower()
    
    # FIRST CHECK: SSN/EIN/Tax ID requirement for 1099-eligible
    has_tax_id = bool(vendor_id and vendor_id.strip() and vendor_id.strip() not in ['', '-', 'N/A', 'n/a', 'None', 'none'])
    
    # SECOND CHECK: Check for goods/products (exclude from 1099-eligible)
    goods_keywords = ['inventory', 'equipment', 'supplies', 'materials', 'merchandise', 'products', 'parts', 'tools', 'furniture', 'software license', 'hardware', 'computers', 'machinery', 'vehicles', 'purchase', 'procurement', 'asset']
    is_goods = any(keyword in accounts_lower or keyword in vendor_lower for keyword in goods_keywords)
    
    # THIRD CHECK: Check for services
    service_keywords = ['consulting', 'professional', 'maintenance', 'repair', 'legal', 'accounting', 'marketing', 'advertising', 'contractor', 'freelance', 'services', 'consulting', 'consultant']
    is_service = any(keyword in accounts_lower or keyword in vendor_lower for keyword in service_keywords)
    
    # If it's clearly goods/products, not 1099-eligible regardless of amount or tax ID
    if is_goods:
        return VendorClassificationResult(
            classification="Non-Reportable",
            form="Not Required",
            reason=f"Goods/products purchase: ${total_paid:,.2f} - equipment/supplies not subject to 1099 reporting",
            confidence=0.8
        )
    
    # Check for attorney/law firm exception (always 1099 eligible if has tax ID and ≥$600)
    if any(keyword in vendor_lower for keyword in ['attorney', 'law firm', 'legal', 'lawyer', 'esquire', 'esq']):
        if has_tax_id and total_paid >= 600:
            return VendorClassificationResult(
                classification="1099-Eligible",
                form="1099-NEC",
                reason=f"Attorney/legal services with Tax ID: ${total_paid:,.2f} ≥ $600 threshold (IRS exception - always reportable)",
                confidence=0.8
            )
        elif not has_tax_id and total_paid >= 600:
            return VendorClassificationResult(
                classification="W-9 Required",
                form="W-9 Needed",
                reason=f"Attorney/legal services: ${total_paid:,.2f} ≥ $600 but missing Tax ID/SSN - need W-9 to collect tax information for 1099 reporting",
                confidence=0.7
            )
        else:
            return VendorClassificationResult(
                classification="Non-Reportable",
                form="Not Required",
                reason=f"Attorney/legal services: ${total_paid:,.2f} < $600 threshold",
                confidence=0.8
            )
    
    # Check for clearly non-reportable categories - EXPANDED LIST
    non_reportable_keywords = [
        # Government
        'eftps', 'irs', 'treasury', 'government', 'federal', 'state', 'county', 'city', 'municipal',
        # Payroll services
        'quickbooks payroll', 'qb payroll', 'adp', 'paychex', 'gusto', 'payroll service',
        # Banks and financial
        'pnc bank', 'pnc', 'chase', 'bank of america', 'wells fargo', 'citibank', 'us bank', 'capital one',
        'bank', 'credit union', 'federal credit union',
        # Insurance
        'insurance', 'assurance',
        # Utilities
        'electric', 'gas', 'water', 'utilities', 'telecom', 'telephone', 'internet service',
        # Credit card processors
        'visa', 'mastercard', 'american express', 'amex', 'discover', 'square', 'stripe', 'paypal merchant'
    ]
    
    if any(keyword in vendor_lower for keyword in non_reportable_keywords):
        return VendorClassificationResult(
            classification="Non-Reportable",
            form="Not Required",
            reason="Government entity, bank, payroll service, insurance, or utility - not subject to 1099 reporting",
            confidence=0.9
        )
    
    # Check for rent payments (1099-MISC if has tax ID and ≥ $600)
    if any(keyword in vendor_lower for keyword in ['rent', 'lease', 'property', 'landlord']):
        if has_tax_id and total_paid >= 600:
            return VendorClassificationResult(
                classification="1099-Eligible",
                form="1099-MISC",
                reason=f"Rent payments with Tax ID: ${total_paid:,.2f} ≥ $600 threshold",
                confidence=0.7
            )
        elif not has_tax_id and total_paid >= 600:
            return VendorClassificationResult(
                classification="Non-Reportable",
                form="Not Required",
                reason=f"Rent payments: ${total_paid:,.2f} ≥ $600 but missing Tax ID/SSN - cannot issue 1099",
                confidence=0.6
            )
        else:
            return VendorClassificationResult(
                classification="Non-Reportable",
                form="Not Required",
                reason=f"Rent payments: ${total_paid:,.2f} < $600 threshold",
                confidence=0.7
            )
    
    # Check for corporations (generally not reportable except attorneys)
    if any(keyword in vendor_lower for keyword in ['corp', 'corporation', 'inc', 'incorporated']):
        return VendorClassificationResult(
            classification="Non-Reportable",
            form="Not Required",
            reason="Corporation - not subject to 1099 reporting (except attorney fees)",
            confidence=0.6
        )
    
    # Check for service providers - STRICT requirements: must have tax ID, $600+, and be services
    if is_service:
        if has_tax_id and total_paid >= 600:
            return VendorClassificationResult(
                classification="1099-Eligible",
                form="1099-NEC",
                reason=f"Service provider with Tax ID: ${total_paid:,.2f} ≥ $600 threshold",
                confidence=0.6
            )
        elif not has_tax_id and total_paid >= 600:
            return VendorClassificationResult(
                classification="Non-Reportable",
                form="Not Required",
                reason=f"Service provider: ${total_paid:,.2f} ≥ $600 but missing Tax ID/SSN - cannot issue 1099",
                confidence=0.5
            )
        else:
            return VendorClassificationResult(
                classification="Non-Reportable",
                form="Not Required",
                reason=f"Service provider: ${total_paid:,.2f} < $600 threshold",
                confidence=0.6
            )
    
    # Check for LLCs - if they have Tax ID, classify directly (no W-9 needed)
    if 'llc' in vendor_lower:
        if has_tax_id and total_paid >= 600 and is_service:
            return VendorClassificationResult(
                classification="1099-Eligible",
                form="1099-NEC",
                reason=f"LLC service provider with Tax ID: ${total_paid:,.2f} ≥ $600 threshold (single-member LLCs are reportable)",
                confidence=0.7
            )
        elif has_tax_id and total_paid >= 600:
            # Has Tax ID but unclear on service type - default to 1099-Eligible (user can transfer if needed)
            return VendorClassificationResult(
                classification="1099-Eligible",
                form="1099-NEC",
                reason=f"LLC with Tax ID: ${total_paid:,.2f} ≥ $600 threshold - likely reportable (review and transfer to Non-Reportable if corporation/multi-member)",
                confidence=0.5
            )
        elif not has_tax_id and total_paid >= 600:
            return VendorClassificationResult(
                classification="W-9 Required",
                form="W-9 Needed",
                reason=f"LLC entity: ${total_paid:,.2f} ≥ $600 but missing Tax ID - need W-9 to collect tax information",
                confidence=0.6
            )
        else:
            return VendorClassificationResult(
                classification="Non-Reportable",
                form="Not Required",
                reason=f"LLC entity: ${total_paid:,.2f} < $600 threshold",
                confidence=0.7
            )
    
    # Default case - if has Tax ID, classify directly; only ask W-9 if missing Tax ID
    if has_tax_id and total_paid >= 600:
        # Has Tax ID and over $600 - classify as 1099-Eligible (user can transfer if needed)
        return VendorClassificationResult(
            classification="1099-Eligible",
            form="1099-NEC",
            reason=f"Has Tax ID: ${total_paid:,.2f} ≥ $600 threshold - likely reportable (review and transfer to Non-Reportable if corporation/exempt entity)",
            confidence=0.5
        )
    elif not has_tax_id and total_paid >= 600:
        # No Tax ID and over $600 - need W-9 to get tax info
        return VendorClassificationResult(
            classification="W-9 Required",
            form="W-9 Needed",
            reason=f"${total_paid:,.2f} ≥ $600 threshold but missing Tax ID/SSN - need W-9 to collect tax information for 1099 reporting",
            confidence=0.6
        )
    else:
        return VendorClassificationResult(
            classification="Non-Reportable",
            form="Not Required",
            reason=f"${total_paid:,.2f} < $600 threshold - below IRS reporting requirements",
            confidence=0.8
        )


def classify_vendor(vendor_name: str, vendor_id: str, total_paid: float, accounts: str) -> VendorClassificationResult:
    """Main classification function with fallback chain and post-processing"""
    
    # Try Gemini first
    result = classify_vendor_with_gemini(vendor_name, vendor_id, total_paid, accounts)
    if result:
        # Post-process to enforce "no W-9 when Tax ID exists" policy
        result = enforce_tax_id_policy(result, vendor_id, total_paid)
        return result
    
    # Try Ollama as fallback (with short timeout)
    result = classify_vendor_with_ollama(vendor_name, vendor_id, total_paid, accounts)
    if result:
        # Post-process to enforce "no W-9 when Tax ID exists" policy
        result = enforce_tax_id_policy(result, vendor_id, total_paid)
        return result
    
    # Use rule-based fallback
    return classify_vendor_fallback(vendor_name, vendor_id, total_paid, accounts)


def enforce_tax_id_policy(result: VendorClassificationResult, vendor_id: str, total_paid: float) -> VendorClassificationResult:
    """Enforce policy: Never ask for W-9 if Tax ID exists"""
    has_tax_id = bool(vendor_id and vendor_id.strip() and vendor_id != '-')
    
    # If result is W-9 Required but vendor has Tax ID, override it
    if result.classification == "W-9 Required" and has_tax_id:
        if total_paid >= 600:
            # Has Tax ID and over $600 - default to 1099-Eligible (user can transfer if needed)
            return VendorClassificationResult(
                classification="1099-Eligible",
                form="1099-NEC",
                reason=f"Has Tax ID: ${total_paid:,.2f} ≥ $600 threshold - likely reportable (review and transfer to Non-Reportable if corporation/exempt entity)",
                confidence=0.5
            )
        else:
            # Has Tax ID but under $600 - Non-Reportable
            return VendorClassificationResult(
                classification="Non-Reportable",
                form="Not Required",
                reason=f"${total_paid:,.2f} < $600 threshold - below IRS reporting requirements",
                confidence=0.8
            )
    
    return result
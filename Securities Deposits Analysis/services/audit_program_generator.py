"""
Audit Program Generator Service
Generates comprehensive audit programs based on organization type
"""

from datetime import datetime
from typing import Dict, List, Any


class AuditProgramGenerator:
    """Generate audit programs for different organization types"""
    
    def __init__(self):
        self.program_templates = {
            'NPO': self._get_npo_template(),
            'Government': self._get_government_template(),
            'Commercial': self._get_commercial_template()
        }
    
    def generate_program(self, org_type: str, program_type: str) -> Dict[str, Any]:
        """
        Generate audit program based on organization type
        
        Args:
            org_type: Organization type (NPO, Government, Commercial)
            program_type: Program template code (e.g., ALG/NPO-AP-90)
            
        Returns:
            Complete audit program dictionary
        """
        if org_type not in self.program_templates:
            raise ValueError(f"Invalid organization type: {org_type}")
        
        template = self.program_templates[org_type]
        
        # Add metadata
        template['program_code'] = program_type
        template['version'] = '1.0'
        template['effective_date'] = datetime.now().strftime('%Y-%m-%d')
        template['generated_date'] = datetime.now().isoformat()
        
        return template
    
    def _get_npo_template(self) -> Dict[str, Any]:
        """Non-Profit Organization audit program template"""
        return {
            'name': 'Securities Deposits Audit Program - Non-Profit Organizations',
            'description': 'Comprehensive audit program for NPO securities deposits with focus on donor restrictions and fund compliance',
            'objectives': [
                'Verify existence and accuracy of all securities deposits',
                'Ensure compliance with donor restrictions and fund designations',
                'Evaluate internal controls over deposit management',
                'Assess proper recording and classification in financial statements',
                'Verify compliance with applicable FASB standards (ASC 958)'
            ],
            'audit_procedures': [
                {
                    'step': '1',
                    'category': 'Planning',
                    'procedure': 'Obtain and review list of all securities deposits held by the organization',
                    'objectives': ['Completeness', 'Understanding'],
                    'working_paper_ref': 'WP-SD-1'
                },
                {
                    'step': '2',
                    'category': 'Existence',
                    'procedure': 'Confirm securities deposits directly with financial institutions holding the deposits',
                    'objectives': ['Existence', 'Rights and Obligations'],
                    'working_paper_ref': 'WP-SD-2'
                },
                {
                    'step': '3',
                    'category': 'Valuation',
                    'procedure': 'Verify deposit amounts, interest rates, and maturity dates with supporting documentation',
                    'objectives': ['Accuracy', 'Valuation'],
                    'working_paper_ref': 'WP-SD-3'
                },
                {
                    'step': '4',
                    'category': 'Compliance',
                    'procedure': 'Review donor agreements and restrictions to ensure deposits comply with donor intent',
                    'objectives': ['Compliance', 'Rights and Obligations'],
                    'working_paper_ref': 'WP-SD-4'
                },
                {
                    'step': '5',
                    'category': 'Classification',
                    'procedure': 'Verify proper classification of deposits as restricted, temporarily restricted, or unrestricted net assets',
                    'objectives': ['Classification', 'Presentation'],
                    'working_paper_ref': 'WP-SD-5'
                },
                {
                    'step': '6',
                    'category': 'Interest Income',
                    'procedure': 'Test calculation of interest income accruals and verify proper recording',
                    'objectives': ['Completeness', 'Accuracy'],
                    'working_paper_ref': 'WP-SD-6'
                },
                {
                    'step': '7',
                    'category': 'Internal Controls',
                    'procedure': 'Evaluate internal controls over deposit authorization, monitoring, and reconciliation',
                    'objectives': ['Control Environment'],
                    'working_paper_ref': 'WP-SD-7'
                },
                {
                    'step': '8',
                    'category': 'Maturity Analysis',
                    'procedure': 'Perform aging analysis on deposits to identify matured or inactive deposits',
                    'objectives': ['Completeness', 'Accuracy'],
                    'working_paper_ref': 'WP-SD-8'
                },
                {
                    'step': '9',
                    'category': 'Disclosure',
                    'procedure': 'Review financial statement disclosures for completeness and accuracy',
                    'objectives': ['Disclosure', 'Presentation'],
                    'working_paper_ref': 'WP-SD-9'
                },
                {
                    'step': '10',
                    'category': 'Conclusion',
                    'procedure': 'Document conclusions and communicate findings to management',
                    'objectives': ['All Objectives'],
                    'working_paper_ref': 'WP-SD-10'
                }
            ]
        }
    
    def _get_government_template(self) -> Dict[str, Any]:
        """Government entity audit program template"""
        return {
            'name': 'Securities Deposits Audit Program - Government Entities',
            'description': 'Comprehensive audit program for government securities deposits with focus on GASB compliance and public fund management',
            'objectives': [
                'Verify existence and accuracy of all government securities deposits',
                'Ensure compliance with GASB requirements and public fund regulations',
                'Evaluate investment policy compliance and authorization',
                'Assess custodial and collateralization requirements',
                'Verify proper recording per GASB 72 and other applicable standards'
            ],
            'audit_procedures': [
                {
                    'step': '1',
                    'category': 'Planning',
                    'procedure': 'Obtain investment policy and list of all securities deposits',
                    'objectives': ['Understanding', 'Completeness'],
                    'working_paper_ref': 'WP-GD-1'
                },
                {
                    'step': '2',
                    'category': 'Authorization',
                    'procedure': 'Verify all deposits are authorized per investment policy and governing body approval',
                    'objectives': ['Rights and Obligations', 'Compliance'],
                    'working_paper_ref': 'WP-GD-2'
                },
                {
                    'step': '3',
                    'category': 'Existence',
                    'procedure': 'Confirm securities deposits with custodial banks and verify physical custody arrangements',
                    'objectives': ['Existence', 'Rights and Obligations'],
                    'working_paper_ref': 'WP-GD-3'
                },
                {
                    'step': '4',
                    'category': 'Collateralization',
                    'procedure': 'Verify deposits exceeding FDIC limits are properly collateralized per state/local requirements',
                    'objectives': ['Compliance', 'Rights and Obligations'],
                    'working_paper_ref': 'WP-GD-4'
                },
                {
                    'step': '5',
                    'category': 'Valuation',
                    'procedure': 'Test deposit amounts, interest rates, and fair value measurements per GASB 72',
                    'objectives': ['Valuation', 'Accuracy'],
                    'working_paper_ref': 'WP-GD-5'
                },
                {
                    'step': '6',
                    'category': 'Fund Classification',
                    'procedure': 'Verify proper fund classification and segregation of restricted deposits',
                    'objectives': ['Classification', 'Presentation'],
                    'working_paper_ref': 'WP-GD-6'
                },
                {
                    'step': '7',
                    'category': 'Interest Allocation',
                    'procedure': 'Test interest income allocation to appropriate funds and verify calculations',
                    'objectives': ['Completeness', 'Accuracy'],
                    'working_paper_ref': 'WP-GD-7'
                },
                {
                    'step': '8',
                    'category': 'Controls',
                    'procedure': 'Evaluate internal controls including segregation of duties and periodic reconciliations',
                    'objectives': ['Control Environment'],
                    'working_paper_ref': 'WP-GD-8'
                },
                {
                    'step': '9',
                    'category': 'Disclosure',
                    'procedure': 'Review CAFR disclosures for deposit and investment risks per GASB 40',
                    'objectives': ['Disclosure', 'Presentation'],
                    'working_paper_ref': 'WP-GD-9'
                },
                {
                    'step': '10',
                    'category': 'Conclusion',
                    'procedure': 'Prepare audit findings report and communicate with management and governing body',
                    'objectives': ['All Objectives'],
                    'working_paper_ref': 'WP-GD-10'
                }
            ]
        }
    
    def _get_commercial_template(self) -> Dict[str, Any]:
        """Commercial entity audit program template"""
        return {
            'name': 'Securities Deposits Audit Program - Commercial Entities',
            'description': 'Comprehensive audit program for commercial securities deposits with focus on GAAP compliance and SEC requirements',
            'objectives': [
                'Verify existence, completeness, and accuracy of securities deposits',
                'Ensure compliance with GAAP and SEC reporting requirements',
                'Evaluate investment policy compliance and risk management',
                'Assess fair value measurements and impairment considerations',
                'Verify proper presentation and disclosure in financial statements'
            ],
            'audit_procedures': [
                {
                    'step': '1',
                    'category': 'Planning',
                    'procedure': 'Obtain and review investment policy, list of deposits, and prior year audit workpapers',
                    'objectives': ['Understanding', 'Completeness'],
                    'working_paper_ref': 'WP-CD-1'
                },
                {
                    'step': '2',
                    'category': 'Existence',
                    'procedure': 'Confirm securities deposits directly with financial institutions',
                    'objectives': ['Existence', 'Rights and Obligations'],
                    'working_paper_ref': 'WP-CD-2'
                },
                {
                    'step': '3',
                    'category': 'Authorization',
                    'procedure': 'Verify deposits are properly authorized per board resolutions and investment policy',
                    'objectives': ['Rights and Obligations', 'Compliance'],
                    'working_paper_ref': 'WP-CD-3'
                },
                {
                    'step': '4',
                    'category': 'Valuation',
                    'procedure': 'Test fair value measurements per ASC 820 and verify pricing sources',
                    'objectives': ['Valuation', 'Accuracy'],
                    'working_paper_ref': 'WP-CD-4'
                },
                {
                    'step': '5',
                    'category': 'Classification',
                    'procedure': 'Verify classification as cash equivalents, short-term, or long-term investments per ASC 210',
                    'objectives': ['Classification', 'Presentation'],
                    'working_paper_ref': 'WP-CD-5'
                },
                {
                    'step': '6',
                    'category': 'Interest Income',
                    'procedure': 'Test interest income accruals, verify calculations, and review revenue recognition',
                    'objectives': ['Completeness', 'Accuracy'],
                    'working_paper_ref': 'WP-CD-6'
                },
                {
                    'step': '7',
                    'category': 'Impairment',
                    'procedure': 'Assess whether any deposits show indicators of impairment or credit risk',
                    'objectives': ['Valuation', 'Accuracy'],
                    'working_paper_ref': 'WP-CD-7'
                },
                {
                    'step': '8',
                    'category': 'Controls',
                    'procedure': 'Evaluate and test internal controls over investment activities and deposit management',
                    'objectives': ['Control Environment'],
                    'working_paper_ref': 'WP-CD-8'
                },
                {
                    'step': '9',
                    'category': 'Disclosure',
                    'procedure': 'Review financial statement disclosures including risks, fair value hierarchy, and maturity analysis',
                    'objectives': ['Disclosure', 'Presentation'],
                    'working_paper_ref': 'WP-CD-9'
                },
                {
                    'step': '10',
                    'category': 'SEC Compliance',
                    'procedure': 'For public companies, verify compliance with SEC reporting requirements',
                    'objectives': ['Compliance', 'Disclosure'],
                    'working_paper_ref': 'WP-CD-10'
                },
                {
                    'step': '11',
                    'category': 'Conclusion',
                    'procedure': 'Document audit conclusions and prepare summary of findings',
                    'objectives': ['All Objectives'],
                    'working_paper_ref': 'WP-CD-11'
                }
            ]
        }
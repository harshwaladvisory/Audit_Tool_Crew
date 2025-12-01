from decimal import Decimal
from bson import ObjectId
from models import GeneralLedger, TrialBalance, Invoice, PrepaidExpenseAnalysis, Discrepancy


def analyze_prepaid_expenses(gl_upload_id, tb_upload_id, invoice_upload_id):
    """
    Analyze prepaid expenses by comparing GL, TB, and recalculated amounts
    Returns a list of analysis results
    """
    try:
        # Convert string IDs to ObjectId
        gl_oid = ObjectId(gl_upload_id)
        tb_oid = ObjectId(tb_upload_id)
        invoice_oid = ObjectId(invoice_upload_id)
        
        # Get GL data
        gl_data = GeneralLedger.objects(file_upload_id=gl_oid)
        gl_dict = {entry.account_number: entry for entry in gl_data}
        
        # Get TB data
        tb_data = TrialBalance.objects(file_upload_id=tb_oid)
        tb_dict = {entry.account_number: entry for entry in tb_data}
        
        # Get Invoice data
        invoice_data = Invoice.objects(file_upload_id=invoice_oid)
        
        # Group invoices by account
        invoice_groups = group_invoices_by_account(invoice_data, gl_dict, tb_dict)
        
        analysis_results = []
        
        # Get all unique account numbers
        all_accounts = set(gl_dict.keys()) | set(tb_dict.keys())
        
        for account_number in all_accounts:
            gl_entry = gl_dict.get(account_number)
            tb_entry = tb_dict.get(account_number)
            
            account_name = (gl_entry.account_name if gl_entry else 
                           tb_entry.account_name if tb_entry else 
                           'Unknown Account')
            
            gl_balance = Decimal(str(gl_entry.balance)) if gl_entry else Decimal('0')
            tb_balance = Decimal(str(tb_entry.balance)) if tb_entry else Decimal('0')
            
            recalculated_balance = calculate_prepaid_balance(account_number, invoice_groups)
            
            discrepancy_gl = gl_balance - recalculated_balance if gl_entry else None
            discrepancy_tb = tb_balance - recalculated_balance if tb_entry else None
            
            # Create analysis record
            analysis = PrepaidExpenseAnalysis(
                account_number=account_number,
                account_name=account_name,
                gl_balance=gl_balance if gl_entry else None,
                tb_balance=tb_balance if tb_entry else None,
                recalculated_balance=recalculated_balance,
                discrepancy_gl=discrepancy_gl,
                discrepancy_tb=discrepancy_tb,
                file_upload_id=gl_oid,
                notes=generate_analysis_notes(gl_entry, tb_entry, recalculated_balance)
            )
            analysis.save()
            
            # Create discrepancy records
            create_discrepancy_records(analysis, discrepancy_gl, discrepancy_tb)
            
            analysis_results.append(analysis)
        
        return analysis_results
        
    except Exception as e:
        raise e


def group_invoices_by_account(invoice_data, gl_dict, tb_dict):
    """Group invoices by account number"""
    invoice_groups = {}
    
    for invoice in invoice_data:
        account_number = None
        
        if invoice.account_number and invoice.account_number in gl_dict:
            account_number = invoice.account_number
        else:
            account_number = match_category_to_account(invoice.prepaid_expense_category, gl_dict, tb_dict)
        
        if account_number:
            if account_number not in invoice_groups:
                invoice_groups[account_number] = []
            invoice_groups[account_number].append(invoice)
    
    return invoice_groups


def match_category_to_account(category, gl_dict, tb_dict):
    """Match invoice category to account"""
    category_lower = category.lower()
    
    for account_number, entry in gl_dict.items():
        account_name_lower = entry.account_name.lower()
        if any(keyword in account_name_lower for keyword in category_lower.split()):
            return account_number
    
    for account_number, entry in tb_dict.items():
        account_name_lower = entry.account_name.lower()
        if any(keyword in account_name_lower for keyword in category_lower.split()):
            return account_number
    
    return None


def calculate_prepaid_balance(account_number, invoice_groups):
    """Calculate expected prepaid balance"""
    if account_number not in invoice_groups:
        return Decimal('0')
    
    invoices = invoice_groups[account_number]
    total_amount = Decimal('0')
    
    for invoice in invoices:
        total_amount += Decimal(str(invoice.amount))
    
    # Simplified: assume 50% remaining
    remaining_balance = total_amount * Decimal('0.5')
    
    return remaining_balance


def create_discrepancy_records(analysis, discrepancy_gl, discrepancy_tb):
    """Create discrepancy records"""
    threshold = Decimal('100.00')
    
    if discrepancy_gl and abs(discrepancy_gl) >= threshold:
        discrepancy = Discrepancy(
            account_number=analysis.account_number,
            account_name=analysis.account_name,
            discrepancy_type='GL',
            recorded_amount=analysis.gl_balance,
            calculated_amount=analysis.recalculated_balance,
            difference=discrepancy_gl,
            analysis_id=analysis.id
        )
        discrepancy.save()
    
    if discrepancy_tb and abs(discrepancy_tb) >= threshold:
        discrepancy = Discrepancy(
            account_number=analysis.account_number,
            account_name=analysis.account_name,
            discrepancy_type='TB',
            recorded_amount=analysis.tb_balance,
            calculated_amount=analysis.recalculated_balance,
            difference=discrepancy_tb,
            analysis_id=analysis.id
        )
        discrepancy.save()


def generate_analysis_notes(gl_entry, tb_entry, recalculated_balance):
    """Generate notes for analysis"""
    notes = []
    
    if not gl_entry:
        notes.append("No GL entry found for this account")
    
    if not tb_entry:
        notes.append("No TB entry found for this account")
    
    if gl_entry and tb_entry:
        gl_bal = Decimal(str(gl_entry.balance))
        tb_bal = Decimal(str(tb_entry.balance))
        if gl_bal != tb_bal:
            notes.append(f"GL and TB balances differ: GL={gl_bal}, TB={tb_bal}")
    
    if recalculated_balance == 0:
        notes.append("No supporting invoices found for recalculation")
    
    return "; ".join(notes) if notes else None
from decimal import Decimal
from datetime import datetime
from bson import ObjectId
from models import JournalEntry, Discrepancy


def generate_journal_entries(discrepancy):
    """Generate journal entries to resolve discrepancies"""
    try:
        entry_number = f"AJE-{str(discrepancy.id)}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        journal_entries = []
        adjustment_amount = abs(Decimal(str(discrepancy.difference)))
        
        if Decimal(str(discrepancy.difference)) > 0:
            # Reduce prepaid expense
            credit_entry = JournalEntry(
                entry_number=entry_number,
                account_number=discrepancy.account_number,
                account_name=discrepancy.account_name,
                debit_amount=Decimal('0'),
                credit_amount=adjustment_amount,
                description=f"Adjustment to reduce prepaid expense per analysis - Discrepancy ID: {discrepancy.id}",
                discrepancy_id=discrepancy.id
            )
            
            expense_account = determine_expense_account(discrepancy.account_name)
            debit_entry = JournalEntry(
                entry_number=entry_number,
                account_number=expense_account['number'],
                account_name=expense_account['name'],
                debit_amount=adjustment_amount,
                credit_amount=Decimal('0'),
                description=f"Expense recognition adjustment - Discrepancy ID: {discrepancy.id}",
                discrepancy_id=discrepancy.id
            )
            
            journal_entries = [debit_entry, credit_entry]
            
        else:
            # Increase prepaid expense
            debit_entry = JournalEntry(
                entry_number=entry_number,
                account_number=discrepancy.account_number,
                account_name=discrepancy.account_name,
                debit_amount=adjustment_amount,
                credit_amount=Decimal('0'),
                description=f"Adjustment to increase prepaid expense per analysis - Discrepancy ID: {discrepancy.id}",
                discrepancy_id=discrepancy.id
            )
            
            expense_account = determine_expense_account(discrepancy.account_name)
            credit_entry = JournalEntry(
                entry_number=entry_number,
                account_number=expense_account['number'],
                account_name=expense_account['name'],
                debit_amount=Decimal('0'),
                credit_amount=adjustment_amount,
                description=f"Expense reversal adjustment - Discrepancy ID: {discrepancy.id}",
                discrepancy_id=discrepancy.id
            )
            
            journal_entries = [debit_entry, credit_entry]
        
        # Save entries
        for entry in journal_entries:
            entry.save()
        
        return journal_entries
        
    except Exception as e:
        raise e


def determine_expense_account(prepaid_account_name):
    """Determine corresponding expense account"""
    account_name_lower = prepaid_account_name.lower()
    
    mappings = {
        'insurance': {'number': '6100', 'name': 'Insurance Expense'},
        'rent': {'number': '6200', 'name': 'Rent Expense'},
        'advertising': {'number': '6300', 'name': 'Advertising Expense'},
        'software': {'number': '6400', 'name': 'Software Expense'},
        'subscription': {'number': '6400', 'name': 'Software Expense'},
        'maintenance': {'number': '6500', 'name': 'Maintenance Expense'},
        'professional': {'number': '6600', 'name': 'Professional Services Expense'},
        'consulting': {'number': '6600', 'name': 'Professional Services Expense'},
        'training': {'number': '6700', 'name': 'Training Expense'},
        'travel': {'number': '6800', 'name': 'Travel Expense'},
        'office': {'number': '6900', 'name': 'Office Expense'},
        'supplies': {'number': '6900', 'name': 'Office Expense'},
    }
    
    for keyword, account_info in mappings.items():
        if keyword in account_name_lower:
            return account_info
    
    return {'number': '6000', 'name': 'General Expense'}
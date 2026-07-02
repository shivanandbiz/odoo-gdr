import odoo
from datetime import date

def setup_opening_balance():
    print("=== Setting up Opening Balance as of 1-Apr-2025 ===")
    
    # 1. Accounts Mapping (from previous search)
    # Using codes found in the system
    map_accounts = {
        'fixed_assets': 'OB002',
        'current_assets': '101000',
        'capital_account': 'OB005',
        'loans_liability': 'OB007',
        'current_liabilities': '201000',
        'retained_earnings': '999999',
        'difference': 'OB.Difference'
    }
    
    # 2. Values Calculation (Net Balances from Tally Image)
    # Asset/Exp = Debit (+), Liability/Equity/Income = Credit (-)
    
    lines = [
        # DEBITS
        {'name': 'Opening Balance: Fixed Assets', 'code': map_accounts['fixed_assets'], 'debit': 119530482.21, 'credit': 0.0},
        {'name': 'Opening Balance: Current Assets', 'code': map_accounts['current_assets'], 'debit': 114362232.52, 'credit': 0.0},
        {'name': 'Difference in Opening Balances', 'code': map_accounts['difference'], 'debit': 2825538.95, 'credit': 0.0},
        
        # CREDITS
        {'name': 'Opening Balance: Capital Account', 'code': map_accounts['capital_account'], 'debit': 0.0, 'credit': 3279120.00},
        {'name': 'Opening Balance: Loans (Liability)', 'code': map_accounts['loans_liability'], 'debit': 0.0, 'credit': 121033641.96},
        {'name': 'Opening Balance: Current Liabilities', 'code': map_accounts['current_liabilities'], 'debit': 0.0, 'credit': 106978567.12},
        {'name': 'Opening Balance: Retained Earnings (P&L Profit)', 'code': map_accounts['retained_earnings'], 'debit': 0.0, 'credit': 5426924.60},
    ]
    
    # 3. Validation
    total_debit = sum(l['debit'] for l in lines)
    total_credit = sum(l['credit'] for l in lines)
    print(f"  Total Debit: {total_debit:,.2f}")
    print(f"  Total Credit: {total_credit:,.2f}")
    
    if abs(total_debit - total_credit) > 0.01:
        print("  ✗ ERROR: Total debits and credits do not match!")
        return
    
    # 4. Create Entry
    # Find Misc journal or Opening journal
    journal = env['account.journal'].search([('code', 'in', ['MISC', 'GEN', 'OPEN'])], limit=1)
    if not journal:
        journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
    
    line_ids = []
    for l in lines:
        acc = env['account.account'].search([('code', '=', l['code'])], limit=1)
        if not acc:
            print(f"  ✗ FATAL: Account {l['code']} not found!")
            return
            
        line_ids.append((0, 0, {
            'account_id': acc.id,
            'name': l['name'],
            'debit': l['debit'],
            'credit': l['credit'],
        }))
        
    move = env['account.move'].create({
        'move_type': 'entry',
        'date': '2025-04-01',
        'ref': 'OPENING/2025-26',
        'journal_id': journal.id,
        'line_ids': line_ids
    })
    
    move.action_post()
    env.cr.commit()
    print(f"  ➜ Successfully created and posted Opening Entry: {move.name}")

setup_opening_balance()

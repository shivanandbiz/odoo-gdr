import odoo

def setup_opening_balance_gross():
    print("=== Redoing Opening Balance with GROSS Totals (Matching Tally Exactly) ===")
    
    # 1. Cleaning up the previous "Net" opening entry
    old_move = env['account.move'].search([('ref', '=', 'OPENING/2025-26')], limit=1)
    if old_move:
        print(f"  Removing previous entry: {old_move.name}")
        old_move.button_draft()
        old_move.unlink()
        env.cr.commit()

    # 2. Account Mapping
    # I'll use specific codes found in the previous search or obvious ones.
    map_accounts = {
        'capital': 'OB005',
        'loans': 'OB007',
        'current_liab': '201000',
        'fixed_assets': 'OB002',
        'current_assets': '101000',
        'sales': '1000000', # SALES INTERSTATE GST 18%
        'purchase': '400000', # Usually 4... for expenses/purchases
        'direct_exp': 'DirectExpenses', 
        'indirect_inc': 'OtherIncome',
        'indirect_exp': 'IndirectExpenses',
        'pandl': '999999', # Retained Earnings
        'difference': 'OB.Difference'
    }
    
    # Ensure all accounts exist or use fallback
    def get_acc_id(code, name_search):
        acc = env['account.account'].search([('code', '=', code)], limit=1)
        if not acc:
            acc = env['account.account'].search([('name', 'ilike', name_search)], limit=1)
        if not acc:
            # Fallback to a general account if not found
            acc = env['account.account'].search([('account_type', '=', 'liability_current')], limit=1)
        return acc.id

    # 3. Gross Lines from Image
    raw_lines = [
        # Capital Account
        {'name': 'Opening: Capital Account (Dr)', 'acc': get_acc_id('OB005', 'Capital'), 'dr': 8220880.00, 'cr': 0.0},
        {'name': 'Opening: Capital Account (Cr)', 'acc': get_acc_id('OB005', 'Capital'), 'dr': 0.0, 'cr': 11500000.00},
        
        # Loans (Liability)
        {'name': 'Opening: Loans (Liability) (Dr)', 'acc': get_acc_id('OB007', 'Loans'), 'dr': 5513222.54, 'cr': 0.0},
        {'name': 'Opening: Loans (Liability) (Cr)', 'acc': get_acc_id('OB007', 'Loans'), 'dr': 0.0, 'cr': 126546864.50},
        
        # Current Liabilities
        {'name': 'Opening: Current Liabilities (Dr)', 'acc': get_acc_id('201000', 'Current Liabilities'), 'dr': 38295506.55, 'cr': 0.0},
        {'name': 'Opening: Current Liabilities (Cr)', 'acc': get_acc_id('201000', 'Current Liabilities'), 'dr': 0.0, 'cr': 145274073.67},
        
        # Fixed Assets
        {'name': 'Opening: Fixed Assets', 'acc': get_acc_id('OB002', 'Fixed Assets'), 'dr': 119530482.21, 'cr': 0.0},
        
        # Current Assets
        {'name': 'Opening: Current Assets (Dr)', 'acc': get_acc_id('101000', 'Current Assets'), 'dr': 137238852.15, 'cr': 0.0},
        {'name': 'Opening: Current Assets (Cr)', 'acc': get_acc_id('101000', 'Current Assets'), 'dr': 0.0, 'cr': 22876619.63},
        
        # Sales Accounts
        {'name': 'Opening: Sales Account (Dr)', 'acc': get_acc_id('1000000', 'Sales'), 'dr': 7112.00, 'cr': 0.0},
        {'name': 'Opening: Sales Account (Cr)', 'acc': get_acc_id('1000000', 'Sales'), 'dr': 0.0, 'cr': 120380582.75},
        
        # Purchase Accounts
        {'name': 'Opening: Purchase Account (Dr)', 'acc': get_acc_id('400000', 'Purchase'), 'dr': 76558567.15, 'cr': 0.0},
        {'name': 'Opening: Purchase Account (Cr)', 'acc': get_acc_id('400000', 'Purchase'), 'dr': 0.0, 'cr': 6365.00},
        
        # Direct Expenses
        {'name': 'Opening: Direct Expenses', 'acc': get_acc_id('DirectExpenses', 'Direct Expenses'), 'dr': 28076997.18, 'cr': 0.0},
        
        # Indirect Incomes
        {'name': 'Opening: Indirect Incomes', 'acc': get_acc_id('OtherIncome', 'Other Income'), 'dr': 0.0, 'cr': 2015030.20},
        
        # Indirect Expenses
        {'name': 'Opening: Indirect Expenses (Dr)', 'acc': get_acc_id('IndirectExpenses', 'Indirect Expenses'), 'dr': 9297837.51, 'cr': 0.0},
        {'name': 'Opening: Indirect Expenses (Cr)', 'acc': get_acc_id('IndirectExpenses', 'Indirect Expenses'), 'dr': 0.0, 'cr': 437304.70},
        
        # Profit & Loss A/c
        {'name': 'Opening: Profit & Loss A/c', 'acc': get_acc_id('999999', 'Retained'), 'dr': 3471844.21, 'cr': 0.0},
        
        # Difference in opening balances
        {'name': 'Opening Difference', 'acc': get_acc_id('OB.Difference', 'Difference'), 'dr': 2825538.95, 'cr': 0.0},
    ]

    total_dr = sum(l['dr'] for l in raw_lines)
    total_cr = sum(l['cr'] for l in raw_lines)
    print(f"  Final Totals -> Dr: {total_dr:,.2f} | Cr: {total_cr:,.2f}")
    
    # 4. Create Entry
    journal = env['account.journal'].search([('code', 'in', ['MISC', 'GEN', 'OPEN'])], limit=1)
    if not journal:
        journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
        
    line_ids = []
    for l in raw_lines:
        line_ids.append((0, 0, {
            'account_id': l['acc'],
            'name': l['name'],
            'debit': l['dr'],
            'credit': l['cr'],
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
    print(f"  ➜ Opening Balance Entry created: {move.name}")

setup_opening_balance_gross()

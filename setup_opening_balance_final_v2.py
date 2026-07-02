import odoo

def setup_opening_balance_final():
    print("=== Setting Up Opening Balance for 1-Apr-2025 (Ref: Image Tally Trial Balance) ===")
    
    # 1. Cleaning up any previous "OPENING/2025-26" entry
    old_move = env['account.move'].search([('ref', '=', 'OPENING/2025-26')], limit=1)
    if old_move:
        print(f"  Removing previous entry: {old_move.name}")
        old_move.button_draft()
        old_move.unlink()
        env.cr.commit()

    # 2. Helper to find/create accounts
    def get_acc(code, name, type_id):
        acc = env['account.account'].search([('code', '=', code)], limit=1)
        if not acc:
            acc = env['account.account'].search([('name', '=', name)], limit=1)
        if not acc:
            print(f"  Creating account: {name} ({code})")
            acc = env['account.account'].create({
                'code': code,
                'name': name,
                'account_type': type_id,
            })
            env.cr.commit()
        return acc.id

    # Mapping based on typical Odoo types
    acc_map = {
        'capital':      get_acc('OB001', 'Capital Account', 'equity'),
        'loans':        get_acc('OB002', 'Loans (Liability)', 'liability_non_current'),
        'current_liab': get_acc('OB003', 'Current Liabilities', 'liability_current'),
        'fixed_assets': get_acc('OB004', 'Fixed Assets', 'asset_non_current'),
        'current_assets': get_acc('OB005', 'Current Assets', 'asset_current'),
        'sales':        get_acc('OB006', 'Sales Accounts', 'income'),
        'purchase':     get_acc('OB007', 'Purchase Accounts', 'expense'),
        'direct_exp':   get_acc('OB008', 'Direct Expenses', 'expense'),
        'indirect_inc': get_acc('OB009', 'Indirect Incomes', 'income_other'),
        'indirect_exp': get_acc('OB010', 'Indirect Expenses', 'expense'),
        'difference':   get_acc('OB011', 'Difference in opening balances', 'equity'),
    }

    # 3. Data from Image
    raw_lines = [
        {'name': 'Capital Account', 'acc': acc_map['capital'], 'dr': 15569598.00, 'cr': 11500000.00},
        {'name': 'Loans (Liability)', 'acc': acc_map['loans'], 'dr': 101048.00, 'cr': 182115804.46},
        {'name': 'Current Liabilities', 'acc': acc_map['current_liab'], 'dr': 56463274.33, 'cr': 117427783.27},
        {'name': 'Fixed Assets', 'acc': acc_map['fixed_assets'], 'dr': 97660019.35, 'cr': 0.0},
        {'name': 'Current Assets', 'acc': acc_map['current_assets'], 'dr': 141981443.11, 'cr': 5794338.39},
        {'name': 'Sales Accounts', 'acc': acc_map['sales'], 'dr': 0.0, 'cr': 80869122.00},
        {'name': 'Purchase Accounts', 'acc': acc_map['purchase'], 'dr': 38361955.59, 'cr': 0.0},
        {'name': 'Direct Expenses', 'acc': acc_map['direct_exp'], 'dr': 11944126.56, 'cr': 0.0},
        {'name': 'Indirect Incomes', 'acc': acc_map['indirect_inc'], 'dr': 0.0, 'cr': 2101539.82},
        {'name': 'Indirect Expenses', 'acc': acc_map['indirect_exp'], 'dr': 37136771.00, 'cr': 0.0},
        {'name': 'Difference in opening balances', 'acc': acc_map['difference'], 'dr': 590352.00, 'cr': 0.0},
    ]

    # Verify Totals
    total_dr = sum(l['dr'] for l in raw_lines)
    total_cr = sum(l['cr'] for l in raw_lines)
    print(f"  Totals -> Dr: {total_dr:,.2f} | Cr: {total_cr:,.2f}")
    
    if abs(total_dr - total_cr) > 0.01:
        print(f"  WARNING: Difference of {abs(total_dr - total_cr):,.2f} detected!")

    # 4. Create Entry
    journal = env['account.journal'].search([('code', 'in', ['MISC', 'GEN', 'OPEN'])], limit=1)
    if not journal:
        journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
        
    line_ids = []
    for l in raw_lines:
        if l['dr'] > 0:
            line_ids.append((0, 0, {
                'account_id': l['acc'],
                'name': f"{l['name']} (Dr)",
                'debit': l['dr'],
                'credit': 0.0,
            }))
        if l['cr'] > 0:
            line_ids.append((0, 0, {
                'account_id': l['acc'],
                'name': f"{l['name']} (Cr)",
                'debit': 0.0,
                'credit': l['cr'],
            }))

    move = env['account.move'].create({
        'move_type': 'entry',
        'date': '2025-04-01',
        'ref': 'OPENING/2025-26',
        'journal_id': journal.id,
        'line_ids': line_ids
    })
    
    print(f"  ➜ Move created: {move.ref}")
    move.action_post()
    env.cr.commit()
    print(f"  ➜ Entry POSTED successfully.")

setup_opening_balance_final()

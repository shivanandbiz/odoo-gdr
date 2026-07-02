
def fix_opening_balance_v2():
    print("=== UPDATING OPENING BALANCE TO MATCH EXCEL (1-APR-2025) ===")
    
    # 1. Clear existing entry
    old_move = env['account.move'].search([('ref', '=', 'OPENING/2025-26')], limit=1)
    if old_move:
        print(f"  ➜ Found entry {old_move.name}. Deleting...")
        old_move.button_draft()
        old_move.unlink()
        env.cr.commit()

    # 2. Define Final Opening Balances from Excel Image
    opening_data = [
        {'name': 'Capital Account (Net Dr)', 'code': 'OB005', 'dr': 4069598.00, 'cr': 0.0},
        {'name': 'Fixed Assets (Net Dr)', 'code': 'OB002', 'dr': 97660019.35, 'cr': 0.0},
        {'name': 'Current Assets (Net Dr)', 'code': '101000', 'dr': 138287214.72, 'cr': 0.0},
        {'name': 'Retained Earnings (P&L Dr)', 'code': '999999', 'dr': 2372081.33, 'cr': 0.0},
        {'name': 'Difference in OB', 'code': 'OB.Difference', 'dr': 590352.00, 'cr': 0.0},
        {'name': 'Loans (Liability) (Net Cr)', 'code': 'OB007', 'dr': 0.0, 'cr': 182014756.46},
        {'name': 'Current Liabilities (Net Cr)', 'code': '201000', 'dr': 0.0, 'cr': 60964508.94},
    ]

    # 3. Create Correct Entry
    journal = env['account.journal'].search([('code', 'in', ['MISC', 'GEN', 'OPEN'])], limit=1)
    if not journal:
        journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
        
    line_ids = []
    total_dr = 0
    total_cr = 0
    
    for d in opening_data:
        acc = env['account.account'].search([('code', '=', d['code'])], limit=1)
        if not acc:
            print(f"  ❌ ERROR: Account with code {d['code']} not found!")
            continue
        
        line_ids.append((0, 0, {
            'account_id': acc.id,
            'name': d['name'],
            'debit': d['dr'],
            'credit': d['cr'],
        }))
        total_dr += d['dr']
        total_cr += d['cr']

    print(f"  ➜ Final Totals -> Dr: {total_dr:,.2f} | Cr: {total_cr:,.2f}")
    
    new_move = env['account.move'].create({
        'move_type': 'entry',
        'date': '2025-04-01',
        'ref': 'OPENING/2025-26',
        'journal_id': journal.id,
        'line_ids': line_ids
    })
    
    new_move.action_post()
    env.cr.commit()
    print(f"  ✅ SUCCESS: Opening Balance updated to match Excel: {new_move.name}")

fix_opening_balance_v2()

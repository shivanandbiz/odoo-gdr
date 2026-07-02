
def fix_opening_balance():
    print("=== STARTING FINAL OPENING BALANCE CORRECTION (1-APR-2025) ===")
    
    # 1. Clear existing incorrect entry
    old_move = env['account.move'].search([('ref', '=', 'OPENING/2025-26')], limit=1)
    if old_move:
        print(f"  ➜ Found old entry {old_move.name}. Deleting...")
        old_move.button_draft()
        old_move.unlink()
        env.cr.commit()
    else:
        print("  ➜ No existing opening entry found to delete.")

    # 2. Correct Account Types
    # Current Assets
    ca_acc = env['account.account'].search([('code', '=', '101000')], limit=1)
    if ca_acc and ca_acc.account_type != 'asset_current':
        print(f"  ➜ Updating {ca_acc.name} type to 'asset_current'")
        ca_acc.write({'account_type': 'asset_current'})
    
    # Current Liabilities
    cl_acc = env['account.account'].search([('code', '=', '201000')], limit=1)
    if cl_acc and cl_acc.account_type != 'liability_current':
        print(f"  ➜ Updating {cl_acc.name} type to 'liability_current'")
        cl_acc.write({'account_type': 'liability_current'})

    # 3. Define Clean Opening Balances (As of 31-Mar-2025 / 1-Apr-2025)
    # Net values calculated from the Tally 24-25 Image
    opening_data = [
        {'name': 'Capital Account (Net Dr)', 'code': 'OB005', 'dr': 4069598.00, 'cr': 0.0},
        {'name': 'Fixed Assets (Net Dr)', 'code': 'OB002', 'dr': 97660019.35, 'cr': 0.0},
        {'name': 'Current Assets (Net Dr)', 'code': '101000', 'dr': 136187104.72, 'cr': 0.0},
        {'name': 'Retained Earnings (Loss 24-25)', 'code': '999999', 'dr': 4472191.33, 'cr': 0.0},
        {'name': 'Difference in OB', 'code': 'OB.Difference', 'dr': 590352.00, 'cr': 0.0},
        {'name': 'Loans (Liability) (Net Cr)', 'code': 'OB007', 'dr': 0.0, 'cr': 182014756.46},
        {'name': 'Current Liabilities (Net Cr)', 'code': '201000', 'dr': 0.0, 'cr': 60964508.94},
    ]

    # 4. Create Correct Entry
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

    print(f"  ➜ Total Debit: {total_dr:,.2f} | Total Credit: {total_cr:,.2f}")
    
    if abs(total_dr - total_cr) > 0.01:
        print(f"  ⚠️ WARNING: Entry is not balanced! Diff: {total_dr - total_cr}")
    
    new_move = env['account.move'].create({
        'move_type': 'entry',
        'date': '2025-04-01',
        'ref': 'OPENING/2025-26',
        'journal_id': journal.id,
        'line_ids': line_ids
    })
    
    new_move.action_post()
    env.cr.commit()
    print(f"  ✅ SUCCESS: New corrected Opening Balance entry posted: {new_move.name}")

fix_opening_balance()

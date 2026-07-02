# migrate_opening_balance.py
import pandas as pd
import numpy as np
from datetime import datetime

def fval(v):
    try:
        if v is None or pd.isna(v): return 0.0
        return float(str(v).replace(',',''))
    except: return 0.0

def get_or_create_account(name, side, is_fixed=False):
    # Mapping heuristic
    atype = 'asset_current'
    if side == 'credit': atype = 'liability_current'
    
    lname = name.lower()
    if 'capital' in lname: atype = 'equity'
    if 'profit' in lname: atype = 'equity_unaffected'
    if 'bank' in lname: atype = 'asset_cash'
    if 'cash' in lname: atype = 'asset_cash'
    if 'loan' in lname: 
        if side == 'credit': atype = 'liability_non_current'
        else: atype = 'asset_current'
    if 'debtor' in lname: atype = 'asset_receivable'
    if 'creditor' in lname: atype = 'liability_payable'
    if is_fixed or 'fixed' in lname or 'machinery' in lname or 'furniture' in lname or 'computer' in lname or 'vehicle' in lname or 'softwar' in lname or 'interior' in lname or 'mobile' in lname:
        atype = 'asset_fixed'
    if 'stock' in lname: atype = 'asset_current'
    if 'tax' in lname: atype = 'liability_current'
    if 'payable' in lname: atype = 'liability_current'
    if 'advance' in lname and side == 'debit': atype = 'asset_current'
    
    # Specific account codes if possible
    acc = env['account.account'].search([('name', '=', name)], limit=1)
    if not acc:
        # Create a new MIG code
        last_acc = env['account.account'].search([('code', 'like', 'OB%')], order='code desc', limit=1)
        next_id = 1
        if last_acc:
            try: next_id = int(last_acc.code[2:]) + 1
            except: pass
        code = f"OB{next_id:03}"
        acc = env['account.account'].create({'name': name, 'code': code, 'account_type': atype})
    else:
        # Update type if it's currently wrong (e.g. from 'expense' to 'asset_fixed')
        if acc.account_type != atype and acc.account_type not in ('asset_cash', 'asset_receivable', 'liability_payable'):
            acc.account_type = atype
            
    return acc

def migrate():
    print("Reading Balance Sheet (2) for Opening Balances...")
    df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', sheet_name='Balance Sheet (2)', header=None)
    
    # ── 1. EXTRACTION ────────────────────────────────────────────────────────
    lines = [] # (account_id, debit, credit)
    
    # Helper to process sides
    def process_side(name, amt, side):
        if not name or name in ('nan', 'None', 'Liabilities', 'Assets', 'Total', 'Difference in opening balances'): return
        
        is_fixed = False
        # In Tally BS, accounts under "Fixed Assets" are fixed.
        # We'll just use the name heuristic.
        
        acc = get_or_create_account(name, side, is_fixed)
        if side == 'debit':
            if amt > 1: lines.append((acc.id, amt, 0.0))
            elif amt < -1: lines.append((acc.id, 0.0, abs(amt)))
        else: # Credit
            if amt > 1: lines.append((acc.id, 0.0, amt))
            elif amt < -1: lines.append((acc.id, abs(amt), 0.0))

    for idx, row in df.iterrows():
        if idx < 9: continue
        r = row.tolist()
        process_side(str(r[0]).strip(), fval(r[1]) or fval(r[2]), 'credit')
        if len(r) > 3:
            process_side(str(r[3]).strip(), fval(r[4]) or fval(r[5]), 'debit')

    # Total differences
    total_debit = sum(l[1] for l in lines)
    total_credit = sum(l[2] for l in lines)
    diff = total_debit - total_credit
    
    if abs(diff) > 0.1:
        print(f"Opening Balance out of sync by {diff:,.2f}. Adjusting to suspense...")
        suspense = get_or_create_account('Difference in Opening Balances', 'credit')
        if diff > 0: lines.append((suspense.id, 0.0, diff))
        else: lines.append((suspense.id, abs(diff), 0.0))

    # ── 2. ODOO ENTRY ────────────────────────────────────────────────────────
    print("Cleaning previous Opening Entry on 2025-04-01...")
    old = env['account.move'].search([('date', '=', '2025-04-01'), ('ref', 'ilike', 'Opening Balance')])
    if old:
        old.button_draft()
        old.unlink()
    
    journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
    
    move = env['account.move'].create({
        'ref': 'Opening Balance 2025-26',
        'date': '2025-04-01',
        'journal_id': journal.id,
        'line_ids': [(0, 0, {
            'account_id': lid,
            'debit': deb,
            'credit': cre,
            'name': 'Opening Balance Migration'
        }) for lid, deb, cre in lines]
    })
    move.action_post()
    
    env.cr.commit()
    print(f"Successfully posted Opening Entry with {len(lines)} lines.")
    print(f"Total Debit/Credit: {move.amount_total:,.2f}")

migrate()

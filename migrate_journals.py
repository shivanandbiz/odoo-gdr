# migrate_journals.py
import openpyxl
from datetime import datetime
from collections import defaultdict

def get_partner(name):
    p = env['res.partner'].search([('name', '=', name)], limit=1)
    if not p:
        p = env['res.partner'].create({'name': name})
    return p.id

def get_account(name):
    # Try to find by name
    a = env['account.account'].search([('name', '=', name)], limit=1)
    if not a:
        # Create a dummy account if not found
        # Determine type based on name
        atype = 'expense'
        if 'Rig' in name or 'Bench' in name or 'Tool' in name: atype = 'asset_fixed'
        elif 'SGST' in name or 'CGST' in name or 'IGST' in name: atype = 'asset_current'
        
        # Find a unique code
        existing_codes = env['account.account'].search([]).mapped('code')
        new_code = 'MIG' + str(len(existing_codes))
        a = env['account.account'].create({
            'name': name,
            'code': new_code,
            'account_type': atype
        })
    return a.id

def migrate_journal_register():
    print("Migrating Journal Register...")
    wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
    ws = wb['Journal Register']
    rows = list(ws.iter_rows(values_only=True))
    
    # Header is at row 8 (index 8)
    hdr_idx = 8
    headers = [str(c).strip() if c is not None else f'Col{j}' for j, c in enumerate(rows[hdr_idx])]
    print(f"Headers count: {len(headers)}")
    
    journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
    
    # Identify ledger columns (from index 7 onwards)
    ledger_cols = []
    for j in range(7, len(headers)):
        name = headers[j]
        if name and 'Unnamed' not in name:
            ledger_cols.append((j, name))
            
    print(f"Found {len(ledger_cols)} ledger columns.")
    
    count = 0
    errors = 0
    for row in rows[hdr_idx + 1:]:
        d = {h: v for h, v in zip(headers, row)}
        part = str(d.get('Particulars', '') or '').strip()
        if not part or 'Total' in part or 'Grand' in part or part == 'None': continue
        
        dt = d.get('Date')
        if not isinstance(dt, datetime): continue
        dt_str = dt.strftime('%Y-%m-%d')
        
        gross = float(str(d.get('Gross Total') or 0).strip() or 0)
        
        # Find which ledger columns have values
        lines = []
        sum_debits = 0
        for col_idx, ledger_name in ledger_cols:
            val = float(str(row[col_idx] or 0).strip() or 0)
            if val != 0:
                lines.append({
                    'name': ledger_name,
                    'account_id': get_account(ledger_name),
                    'debit': val if val > 0 else 0,
                    'credit': -val if val < 0 else 0
                })
                sum_debits += val
        
        if not lines: continue
        
        # Add the balancing line for Particulars
        partner_id = get_partner(part)
        partner_account = env['res.partner'].browse(partner_id).property_account_payable_id.id # Standard for Journal
        
        lines.append({
            'name': f"Ref: {part}",
            'partner_id': partner_id,
            'account_id': partner_account,
            'debit': 0 if sum_debits > 0 else -sum_debits,
            'credit': sum_debits if sum_debits > 0 else 0
        })
        
        try:
            move = env['account.move'].create({
                'move_type': 'entry',
                'journal_id': journal.id,
                'date': dt_str,
                'ref': str(d.get('Voucher Ref. No.') or ''),
                'line_ids': [(0, 0, line) for line in lines],
            })
            move.action_post()
            count += 1
            if count % 100 == 0:
                env.cr.commit()
                print(f"  ✓ {count} journals...")
        except Exception as e:
            errors += 1
            print(f"  ERR row {count}: {e}")

    env.cr.commit()
    print(f"Finished Journal Register: {count} records imported. Errors: {errors}")

migrate_journal_register()

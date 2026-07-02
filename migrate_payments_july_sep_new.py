import pandas as pd
from datetime import datetime

def get_partner(name):
    if not name: return None
    p = env['res.partner'].search([('name', '=ilike', name)], limit=1)
    if not p:
        p = env['res.partner'].search([('name', 'ilike', name)], limit=1)
    return p

def get_account(name):
    if not name: return None
    return env['account.account'].search([('name', 'ilike', name)], limit=1)

def get_journal(name):
    j = env['account.journal'].search([('name', 'ilike', name)], limit=1)
    if not j:
        j = env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
        if not j: j = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def migrate_july_sep_payments():
    fname = '/home/biz/odoo/july_sep_payment_reg.xlsx'
    print(f"Reading {fname}...")
    df = pd.read_excel(fname, header=None)
    
    # Headers are at Row 9 (Index 8)
    headers = df.iloc[8].tolist()
    accounts_map = {}
    for i in range(7, len(headers)):
        if pd.notna(headers[i]):
            accounts_map[i] = str(headers[i]).strip()
            
    print(f"Mapped {len(accounts_map)} account columns.")

    print("Cleaning up older migration data (Pure Move logic)...")
    for pref in ['PAY_JUL_SEP/', 'JS_']:
        moves = env['account.move'].search([('ref', 'like', f"{pref}%")])
        if moves:
            print(f"  Unreconciling {len(moves)} moves with prefix {pref}")
            moves.line_ids.remove_move_reconcile()
            posted_moves = moves.filtered(lambda m: m.state == 'posted')
            if posted_moves:
                posted_moves.button_draft()
                
    # Use SQL for actual deletions to be fast and avoid triggers
    env.cr.execute("DELETE FROM account_payment WHERE memo LIKE 'PAY_JUL_SEP/%%' OR memo LIKE 'JS_%%'")
    env.cr.execute("DELETE FROM account_move WHERE ref LIKE 'PAY_JUL_SEP/%%' OR ref LIKE 'JS_%%'")
    
    # Extra cleanup for unreferenced moves in the period
    env.cr.execute("""
        DELETE FROM account_move 
        WHERE date >= '2025-07-01' AND date <= '2025-09-30'
        AND ref IS NULL AND move_type = 'entry'
        AND journal_id IN (SELECT id FROM account_journal WHERE type IN ('bank', 'cash'))
    """)
    
    env.cr.commit()
    print("Cleanup finished.")
    
    count = 0
    reconciled_count = 0
    errors = 0
    
    # Data starts from row 10 (Index 9)
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = f"JS_{idx}"
        narration = str(r[5]).strip() if pd.notna(r[5]) else ''
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        vals = {}
        for col_idx, acc_name in accounts_map.items():
            if col_idx < len(r) and pd.notna(r[col_idx]):
                try:
                    v = float(r[col_idx] or 0)
                    if v != 0: vals[acc_name] = v
                except: pass
        
        if not vals: continue
        
        dr_name = None
        cr_name = None
        amount = 0.0
        
        is_bank_source = any(b in part_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp'])
        
        if is_bank_source:
            cr_name = part_name
            for name, val in vals.items():
                if name != part_name:
                    dr_name = name
                    amount = abs(val)
                    break
            if not dr_name:
                amount = abs(vals.get(part_name, 0))
                dr_name = "Suspense"
        else:
            dr_name = part_name
            for name, val in vals.items():
                if any(b in name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp']):
                    cr_name = name
                    amount = abs(val)
                    break
            if not cr_name:
                for name, val in vals.items():
                    if name != dr_name:
                        cr_name = name
                        amount = abs(val)
                        break
        
        if not dr_name or not cr_name: 
            # Fallback to Gross Total column (Index 6)
            amount = float(r[6]) if pd.notna(r[6]) else 0
            if amount == 0: continue
            dr_name = part_name
            for name in vals.keys():
                if 'HDFC' in name or 'Bank' in name:
                    cr_name = name
                    break
            if not cr_name: cr_name = "Bank"

        dt_str = datetime.now().strftime('%Y-%m-%d')
        if isinstance(raw_date, (datetime, pd.Timestamp)):
            dt_str = raw_date.strftime('%Y-%m-%d')
        elif pd.notna(raw_date):
            dt_str = str(raw_date)[:10]

        journal = get_journal(cr_name)
        
        try:
            partner = get_partner(dr_name)
            dr_acc = get_account(dr_name)
            cr_acc = get_account(cr_name)
            
            dr_acc_id = partner.property_account_payable_id.id if partner else (dr_acc.id if dr_acc else False)
            cr_acc_id = cr_acc.id if cr_acc else journal.default_account_id.id
            
            if not dr_acc_id:
                if not dr_acc:
                    partner = env['res.partner'].create({'name': dr_name, 'supplier_rank': 1})
                    dr_acc_id = partner.property_account_payable_id.id
                else:
                    dr_acc_id = dr_acc.id

            # Create MOVE (Journal Entry)
            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': f"PAY_JUL_SEP/{vref}",
                'journal_id': journal.id,
                'line_ids': [
                    (0, 0, {
                        'name': f"Payment: {dr_name} | {narration}",
                        'account_id': dr_acc_id,
                        'debit': amount,
                        'credit': 0.0,
                        'partner_id': partner.id if partner else False,
                    }),
                    (0, 0, {
                        'name': f"Payment: {dr_name} | {narration}",
                        'account_id': cr_acc_id,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ]
            })
            move.action_post()
            
            if count % 100 == 0:
                print(f"  Migrated {count} rows...")
            count += 1
            
            # Reconciliation
            if partner:
                pay_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled)
                bill_lines = env['account.move.line'].search([
                    ('partner_id', '=', partner.id),
                    ('account_id.account_type', '=', 'liability_payable'),
                    ('reconciled', '=', False),
                    ('move_id.move_type', '=', 'in_invoice'),
                    ('move_id.state', '=', 'posted'),
                    ('credit', '>', 0)
                ], order='date asc')
                if pay_line and bill_lines:
                    (pay_line | bill_lines).reconcile()
                    reconciled_count += 1
                    
        except Exception as e:
            errors += 1
            print(f"  ERR row {idx}: {e}")
            
    env.cr.commit()
    print(f"\nJuly-Sep Payment Migration Finished.")
    print(f"Total: {count} | Reconciled: {reconciled_count} | Errors: {errors}")

migrate_july_sep_payments()

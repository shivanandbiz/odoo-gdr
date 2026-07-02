import pandas as pd
from datetime import datetime

def get_partner(name):
    if not name: return None
    return env['res.partner'].search([('name', '=ilike', name)], limit=1)

def get_account(name):
    if not name: return None
    return env['account.account'].search([('name', 'ilike', name)], limit=1)

def get_journal(name):
    j = env['account.journal'].search([('name', 'ilike', name)], limit=1)
    if not j:
        j = env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
        if not j: j = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def migrate_jan_mar_payments():
    fname = '/home/biz/odoo/payment_register_jan_mar.xlsx'
    print(f"Reading {fname}...")
    df = pd.read_excel(fname, header=None)
    
    headers = df.iloc[8].tolist()
    accounts_map = {}
    for i in range(7, len(headers)):
        if pd.notna(headers[i]):
            accounts_map[i] = str(headers[i]).strip()
            
    print(f"Mapped {len(accounts_map)} account columns.")

    print("Cleaning up older migration data (ref like PAY_JAN_MAR/)...")
    env['account.move'].search([('ref', 'like', 'PAY_JAN_MAR/%')]).button_draft()
    env['account.move'].search([('ref', 'like', 'PAY_JAN_MAR/%')]).unlink()
    env['account.payment'].search([('memo', 'like', 'PAY_JAN_MAR/%')]).action_draft()
    env['account.payment'].search([('memo', 'like', 'PAY_JAN_MAR/%')]).unlink()
    env.cr.commit()
    
    count = 0
    reconciled_count = 0
    errors = 0
    
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = f"JM_{idx}"
        narration = str(r[5]).strip() if pd.notna(r[5]) else ''
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        vals = {}
        for col_idx, acc_name in accounts_map.items():
            if col_idx < len(r) and pd.notna(r[col_idx]) and float(r[col_idx] or 0) != 0:
                vals[acc_name] = float(r[col_idx])
        
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
            amount = float(r[7]) if pd.notna(r[7]) else 0
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
                partner = env['res.partner'].create({'name': dr_name, 'supplier_rank': 1})
                dr_acc_id = partner.property_account_payable_id.id

            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': f"PAY_JAN_MAR/{vref}",
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
            
            payment = env['account.payment'].create({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner.id if partner else False,
                'amount': amount,
                'journal_id': journal.id,
                'date': dt_str,
                'memo': f"PAY_JAN_MAR/{vref} | {narration}",
                'state': 'in_process',
            })
            try: payment.move_id = move.id
            except: pass
            
            count += 1
            
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
    print(f"\nJan-Mar Payment Migration Finished.")
    print(f"Total: {count} | Reconciled: {reconciled_count} | Errors: {errors}")

migrate_jan_mar_payments()

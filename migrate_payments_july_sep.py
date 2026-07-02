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

def migrate_july_sep_payments():
    fname = '/home/biz/odoo/payment_register_july_sep.xlsx'
    print(f"Reading {fname}...")
    df = pd.read_excel(fname, header=None)
    
    # Headers are at Row 9 (Index 8)
    headers = df.iloc[8].tolist()
    accounts_map = {}
    for i in range(6, len(headers)):
        if pd.notna(headers[i]):
            accounts_map[i] = str(headers[i]).strip()
            
    print(f"Mapped {len(accounts_map)} account columns.")

    print("Cleaning up older migration data (ref like PAY_JUL_SEP/)...")
    env['account.move'].search([('ref', 'like', 'PAY_JUL_SEP/%')]).button_draft()
    env['account.move'].search([('ref', 'like', 'PAY_JUL_SEP/%')]).unlink()
    env['account.payment'].search([('memo', 'like', 'PAY_JUL_SEP/%')]).action_draft()
    env['account.payment'].search([('memo', 'like', 'PAY_JUL_SEP/%')]).unlink()
    env.cr.commit()
    
    count = 0
    reconciled_count = 0
    errors = 0
    
    # Data starts from row 10 (Index 9)
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = f"JS_{idx}" # No explicit ref column found easily, use row index
        narration = str(r[3]).strip() if pd.notna(r[3]) else ''
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        # In this pivot format, we need to find DR and CR from columns 6+
        # Generally, HDFC/Bank is the Credit (Source)
        # Others are Debit (Vendor/Expense)
        
        vals = {}
        for col_idx, acc_name in accounts_map.items():
            if col_idx < len(r) and pd.notna(r[col_idx]) and float(r[col_idx] or 0) != 0:
                vals[acc_name] = float(r[col_idx])
        
        if not vals: continue
        
        # Logic to determine DR and CR:
        # If part_name is HDFC, then HDFC is CR, the OTHER one in vals is DR.
        # If part_name is a Vendor, then Vendor is DR, the bank in vals is CR.
        
        dr_name = None
        cr_name = None
        amount = 0.0
        
        # Check if part_name is one of the accounts in the pivot
        is_bank_source = 'HDFC' in part_name or 'Kotak' in part_name or 'Bank' in part_name or 'Cash' in part_name
        
        if is_bank_source:
            cr_name = part_name
            # Find the DR from vals (it's the one that is NOT part_name)
            for name, val in vals.items():
                if name != part_name:
                    dr_name = name
                    amount = abs(val)
                    break
            if not dr_name: # Maybe only one column has value and it IS part_name? 
                # This would be weird for a payment, but let's handle
                amount = abs(vals.get(part_name, 0))
                dr_name = "Suspense" # Fallback
        else:
            dr_name = part_name
            # Find the CR from vals (it's usually the bank account)
            for name, val in vals.items():
                if 'HDFC' in name or 'Kotak' in name or 'Bank' in name or 'Cash' in name:
                    cr_name = name
                    amount = abs(val)
                    break
            if not cr_name:
                # Pick any other column that has the value
                for name, val in vals.items():
                    if name != dr_name:
                        cr_name = name
                        amount = abs(val)
                        break
        
        if not dr_name or not cr_name: 
            # If still not found, use Gross Total (Col 5)
            amount = float(r[5]) if pd.notna(r[5]) else 0
            if amount == 0: continue
            dr_name = part_name
            # Find any bank column for CR
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
            # 1. Accounts
            partner = get_partner(dr_name)
            dr_acc = get_account(dr_name)
            cr_acc = get_account(cr_name)
            
            dr_acc_id = partner.property_account_payable_id.id if partner else (dr_acc.id if dr_acc else False)
            cr_acc_id = cr_acc.id if cr_acc else journal.default_account_id.id
            
            if not dr_acc_id:
                # Create partner if it looks like a person/company
                partner = env['res.partner'].create({'name': dr_name, 'supplier_rank': 1})
                dr_acc_id = partner.property_account_payable_id.id

            # 2. Create Move
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
            
            # 3. Create Payment Record (for UI)
            payment = env['account.payment'].create({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner.id if partner else False,
                'amount': amount,
                'journal_id': journal.id,
                'date': dt_str,
                'memo': f"PAY_JUL_SEP/{vref} | {narration}",
                'state': 'in_process',
            })
            try: payment.move_id = move.id
            except: pass
            
            count += 1
            
            # 4. Reconciliation
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

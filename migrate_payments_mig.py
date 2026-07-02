import pandas as pd
from datetime import datetime

def get_partner(name):
    # Case-insensitive
    return env['res.partner'].search([('name', '=ilike', name)], limit=1)

def get_account(name):
    return env['account.account'].search([('name', 'ilike', name)], limit=1)

def get_journal(name):
    j = env['account.journal'].search([('name', 'ilike', name)], limit=1)
    if not j:
        # Fallback to Bank
        j = env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
        if not j: j = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def migrate_vendor_payments():
    fname = '/home/biz/odoo/new_payment_register_mig.xlsx'
    print(f"Reading {fname}...")
    df = pd.read_excel(fname, header=None)
    
    # Headers are at Row 9 (Index 8)
    headers = df.iloc[8].tolist()
    sources_map = {}
    for i in range(7, len(headers)):
        if pd.notna(headers[i]):
            sources_map[i] = str(headers[i]).strip()
            
    print(f"Mapped {len(sources_map)} source columns.")

    print("Cleaning up older migration data (ref like PAY_MIG/)...")
    # Clean Moves
    env['account.move'].search([('ref', 'like', 'PAY_MIG/%')]).button_draft()
    env['account.move'].search([('ref', 'like', 'PAY_MIG/%')]).unlink()
    # Clean Payments
    env['account.payment'].search([('memo', 'like', 'PAY_MIG/%')]).action_draft()
    env['account.payment'].search([('memo', 'like', 'PAY_MIG/%')]).unlink()
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
        vref = str(r[3]).strip() if pd.notna(r[3]) and str(r[3]) != 'nan' else f"{idx}"
        narration = str(r[5]).strip() if pd.notna(r[5]) else ''
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        # Find amount and source column
        source_name = None
        amount = 0.0
        for col_idx in sources_map.keys():
            if col_idx < len(r) and pd.notna(r[col_idx]) and float(r[col_idx] or 0) > 0:
                source_name = sources_map[col_idx]
                amount = float(r[col_idx])
                break
        
        if amount == 0: continue
        
        dt_str = datetime.now().strftime('%Y-%m-%d')
        if isinstance(raw_date, (datetime, pd.Timestamp)):
            dt_str = raw_date.strftime('%Y-%m-%d')
        elif pd.notna(raw_date):
            dt_str = str(raw_date)[:10]

        journal = get_journal(source_name or 'Bank')
        
        try:
            # 1. Determine accounts
            # Target (Debit)
            partner = get_partner(part_name)
            target_acc_id = False
            
            # Check if Part Name is another bank account (Transfer)
            is_bank_transfer = any(part_name.lower() in v.lower() for v in sources_map.values())
            
            if partner:
                target_acc_id = partner.property_account_payable_id.id
            elif is_bank_transfer:
                acc = get_account(part_name)
                target_acc_id = acc.id if acc else False
            else:
                # Search for account directly (Expense)
                acc = get_account(part_name)
                if acc:
                    target_acc_id = acc.id
                else:
                    # Create partner
                    partner = env['res.partner'].create({'name': part_name, 'supplier_rank': 1})
                    target_acc_id = partner.property_account_payable_id.id
            
            # Source (Credit)
            src_acc = get_account(source_name)
            src_acc_id = src_acc.id if src_acc else journal.default_account_id.id
            
            if not target_acc_id: 
                # Last resort
                target_acc_id = env['account.account'].search([('account_type', '=', 'expense')], limit=1).id

            # 2. Create Ledger Move
            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': f"PAY_MIG/{vref}",
                'journal_id': journal.id,
                'line_ids': [
                    (0, 0, {
                        'name': f"Payment: {part_name} | {narration}",
                        'account_id': target_acc_id,
                        'debit': amount,
                        'credit': 0.0,
                        'partner_id': partner.id if partner else False,
                    }),
                    (0, 0, {
                        'name': f"Payment: {part_name} | {narration}",
                        'account_id': src_acc_id,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ]
            })
            move.action_post()
            
            # 3. Create UI Payment Record
            payment = env['account.payment'].create({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner.id if partner else False,
                'amount': amount,
                'journal_id': journal.id,
                'date': dt_str,
                'memo': f"PAY_MIG/{vref} | {narration}",
                'state': 'in_process',
            })
            try: payment.move_id = move.id
            except: pass
            
            count += 1
            
            # 4. Reconciliation with Vendor Bills
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
    print(f"\nVendor Payment Migration Finished.")
    print(f"Total: {count} | Reconciled: {reconciled_count} | Errors: {errors}")

migrate_vendor_payments()

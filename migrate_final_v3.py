import pandas as pd
from datetime import datetime

def get_partner(name):
    # Case-insensitive search
    p = env['res.partner'].search([('name', '=ilike', name)], limit=1)
    return p

def get_journal(name):
    j = env['account.journal'].search([('name', 'ilike', name)], limit=1)
    if not j:
        j = env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
        if not j: j = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def get_account(name):
    return env['account.account'].search([('name', 'ilike', name)], limit=1)

def migrate_final_v3():
    fname = '/home/biz/odoo/new_recipt_register_mig.xlsx'
    print(f"Reading {fname}...")
    df = pd.read_excel(fname, header=None)
    
    dest_map = {
        8: 'HDFC C/A 50200024612749',
        9: 'Kotak -3545975369',
        10: 'Gkp Current A/c',
        11: 'BANK CHARGES',
        12: 'Imprest - Shantalinga',
        13: 'BG Rail Bhavan -009GT02231400001',
        14: 'FD INTEREST',
        15: 'Cholamandalam Investment and Finance Cmpy LTD Term',
        16: 'F D Amount',
        17: 'Suspense',
        18: 'THE KARUR VYSYA BANK LIMITED -Unsecured'
    }

    print("Cleaning up older migration data...")
    # Clean Moves
    env['account.move'].search([('ref', 'like', 'REC_MIG/%')]).button_draft()
    env['account.move'].search([('ref', 'like', 'REC_MIG/%')]).unlink()
    # Clean Payments
    env['account.payment'].search([('memo', 'like', 'REC_MIG/%')]).action_draft()
    env['account.payment'].search([('memo', 'like', 'REC_MIG/%')]).unlink()
    env.cr.commit()
    
    count = 0
    reconciled_count = 0
    errors = 0
    
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = str(r[3]).strip() if pd.notna(r[3]) and str(r[3]) != 'nan' else f"{idx}"
        narration = str(r[5]).strip() if pd.notna(r[5]) else ''
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        # Amount and Destination
        dest_account_name = None
        amount = 0.0
        for col_idx in range(8, 19):
            if col_idx < len(r) and pd.notna(r[col_idx]) and float(r[col_idx] or 0) > 0:
                dest_account_name = dest_map.get(col_idx)
                amount = float(r[col_idx])
                break
        
        if amount == 0: continue
        
        dt_str = datetime.now().strftime('%Y-%m-%d')
        if isinstance(raw_date, (datetime, pd.Timestamp)):
            dt_str = raw_date.strftime('%Y-%m-%d')
        elif pd.notna(raw_date):
            dt_str = str(raw_date)[:10]

        journal = get_journal(dest_account_name or 'Bank')
        partner = get_partner(part_name)
        
        try:
            # 1. Determine accounts
            dest_acc = get_account(dest_account_name)
            dest_acc_id = dest_acc.id if dest_acc else journal.default_account_id.id
            
            is_transfer = any(part_name.lower() in val.lower() for val in dest_map.values())
            
            partner_id = False
            source_acc_id = False
            
            if partner:
                partner_id = partner.id
                source_acc_id = partner.property_account_receivable_id.id
            elif is_transfer:
                source_acc = get_account(part_name)
                source_acc_id = source_acc.id if source_acc else False
            
            if not source_acc_id:
                if not partner:
                    partner = env['res.partner'].create({'name': part_name, 'customer_rank': 1})
                partner_id = partner.id
                source_acc_id = partner.property_account_receivable_id.id

            # 2. Create the Ledger Move (STABLE WAY)
            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': f"REC_MIG/{vref}",
                'journal_id': journal.id,
                'line_ids': [
                    (0, 0, {
                        'name': f"Receipt: {part_name} | {narration}",
                        'account_id': dest_acc_id,
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': f"Receipt: {part_name} | {narration}",
                        'account_id': source_acc_id,
                        'partner_id': partner_id,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ]
            })
            move.action_post()
            
            # 3. Create the UI Payment record
            payment = env['account.payment'].create({
                'payment_type': 'inbound' if not is_transfer else 'internal',
                'partner_type': 'customer' if not is_transfer else False,
                'partner_id': partner_id if not is_transfer else False,
                'amount': amount,
                'journal_id': journal.id,
                'date': dt_str,
                'memo': f"REC_MIG/{vref} | {narration}",
                'state': 'in_process',
            })
            # Link the move to payment so they appear connected in UI if possible
            # In some versions it's payment.move_id = move.id
            try: payment.move_id = move.id
            except: pass
            
            count += 1
            
            # 4. Reconciliation
            if partner_id:
                pay_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
                inv_lines = env['account.move.line'].search([
                    ('partner_id', '=', partner_id),
                    ('account_id.account_type', '=', 'asset_receivable'),
                    ('reconciled', '=', False),
                    ('move_id.move_type', '=', 'out_invoice'),
                    ('move_id.state', '=', 'posted'),
                    ('debit', '>', 0)
                ], order='date asc')
                if pay_line and inv_lines:
                    (pay_line | inv_lines).reconcile()
                    reconciled_count += 1
                    
        except Exception as e:
            errors += 1
            print(f"  ERR row {idx}: {e}")
            
    env.cr.commit()
    print(f"\nFinal Migration v3 Finished.")
    print(f"Total Migrated: {count} | Reconciled: {reconciled_count} | Errors: {errors}")

migrate_final_v3()

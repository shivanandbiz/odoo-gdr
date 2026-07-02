import pandas as pd
from datetime import datetime

def get_partner(name):
    return env['res.partner'].search([('name', '=', name)], limit=1)

def get_journal(name):
    j = env['account.journal'].search([('name', 'ilike', name)], limit=1)
    if not j:
        j = env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
        if not j: j = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def migrate_receipts_robust():
    fname = '/home/biz/odoo/new_recipt_register_mig.xlsx'
    print(f"Reading {fname}...")
    df = pd.read_excel(fname, header=None)
    
    inr_currency = env.ref('base.INR')
    
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

    count = 0; reconciled_count = 0; errors = 0
    
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = str(r[3]).strip() if pd.notna(r[3]) and str(r[3]) != 'nan' else f"{idx}"
        narration = str(r[5]).strip()[:200] if pd.notna(r[5]) else ''
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        dest_account_name = None; amount = 0.0
        for col_idx in range(8, 19):
            if col_idx < len(r) and pd.notna(r[col_idx]) and float(r[col_idx] or 0) > 0:
                dest_account_name = dest_map.get(col_idx)
                amount = float(r[col_idx])
                break
        
        if amount == 0: continue
        
        if isinstance(raw_date, (datetime, pd.Timestamp)):
            dt_str = raw_date.strftime('%Y-%m-%d')
        else:
            try:
                dt_str = str(raw_date)[:10]
            except:
                dt_str = datetime.now().strftime('%Y-%m-%d')
        
        journal = get_journal(dest_account_name or 'Bank')
        partner = get_partner(part_name)
        is_transfer = any(part_name.lower() in val.lower() for val in dest_map.values())
        
        try:
            if is_transfer:
                # Internal transfer: Source is part_name, Dest is dest_account_name
                # We'll just create a journal entry directly to avoid internal transfer payment bugs in older scripts
                source_journal = get_journal(part_name)
                
                # We create an entry moving from source to dest
                # Since it's a receipt in dest, we debit dest, credit source
                move = env['account.move'].create({
                    'move_type': 'entry', 'date': dt_str, 'ref': f"REC_MIG/{vref}", 'journal_id': source_journal.id,
                    'line_ids': [
                        (0, 0, {'name': narration or "Internal Transfer", 'account_id': journal.default_account_id.id, 'debit': amount}),
                        (0, 0, {'name': narration or "Internal Transfer", 'account_id': source_journal.default_account_id.id, 'credit': amount}),
                    ]
                })
                try: move.action_post()
                except Exception as pe: print(f"  Row {idx} transfer post fail: {pe}")
                count += 1
            else:
                # Customer Payment
                if not partner: partner = env['res.partner'].create({'name': part_name, 'customer_rank': 1})
                
                dest_acc_id = journal.default_account_id.id
                source_acc_id = partner.property_account_receivable_id.id
                
                move = env['account.move'].create({
                    'move_type': 'entry', 'date': dt_str, 'ref': f"REC_MIG/{vref}", 'journal_id': journal.id,
                    'line_ids': [
                        (0, 0, {'name': f"Receipt: {part_name} | {narration}", 'account_id': dest_acc_id, 'debit': amount, 'currency_id': inr_currency.id}),
                        (0, 0, {'name': f"Receipt: {part_name} | {narration}", 'account_id': source_acc_id, 'partner_id': partner.id, 'credit': amount, 'currency_id': inr_currency.id}),
                    ]
                })
                
                try:
                    with env.cr.savepoint():
                        move.action_post()
                except Exception as pe:
                    print(f"  Row {idx} move skip: {pe}")
                    continue

                mline = env['account.payment.method.line'].search([('payment_type','=','inbound'),('journal_id','=',journal.id)], limit=1)
                mline_id = mline.id if mline else None
                
                memo = f"REC_MIG/{vref} | {narration}"[:255]
                env.cr.execute("""
                    INSERT INTO account_payment 
                    (amount, date, journal_id, partner_id, payment_type, partner_type, state, memo, move_id, company_id, currency_id, payment_method_line_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (amount, dt_str, journal.id, partner.id, 'inbound', 'customer', 'in_process', memo, move.id, journal.company_id.id, inr_currency.id, mline_id))
                
                payment_id = env.cr.fetchone()[0]
                env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (payment_id, move.id))
                count += 1
                
                try:
                    with env.cr.savepoint():
                        rec_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                        if rec_line:
                            open_lines = env['account.move.line'].search([
                                ('partner_id', '=', partner.id), ('account_id', '=', rec_line.account_id.id),
                                ('reconciled', '=', False), ('move_id.move_type', '=', 'out_invoice'),
                                ('move_id.state', '=', 'posted'), ('balance', '>', 0)
                            ], order='date asc')
                            if open_lines:
                                (rec_line | open_lines).reconcile()
                                reconciled_count += 1
                except Exception as rec_err:
                    print(f"  Row {idx} recon skip: {rec_err}")
                        
        except Exception as e:
            errors += 1
            print(f"  ERR row {idx}: {e}")
            
    env.cr.commit()
    print(f"\nMigration Finished. Total Payments Created: {count} | Reconciled: {reconciled_count} | Errors: {errors}")

migrate_receipts_robust()

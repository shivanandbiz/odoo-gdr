import pandas as pd
from datetime import datetime

def get_partner(name):
    return env['res.partner'].search([('name', '=', name)], limit=1)

def get_journal(name):
    # Try to find a journal with this name
    j = env['account.journal'].search([('name', 'ilike', name)], limit=1)
    if not j:
        # Fallback to general bank journal
        j = env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
        if not j: journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def migrate_as_payments():
    fname = '/home/biz/odoo/new_recipt_register_mig.xlsx'
    print(f"Reading {fname} with pandas...")
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

    print("Cleaning up previous migration entries (ref like REC_MIG/)...")
    # Deleting the moves we created as 'entry'
    existing_moves = env['account.move'].search([('ref', 'like', 'REC_MIG/%')])
    if existing_moves:
        for m in existing_moves:
            if m.state != 'draft': m.button_draft()
        existing_moves.unlink()
        env.cr.commit()

    print("Cleaning up previous payments (memo like REC_MIG/)...")
    existing_payments = env['account.payment'].search([('memo', 'like', 'REC_MIG/%')])
    if existing_payments:
        for p in existing_payments:
            if p.state != 'draft': p.action_draft()
        existing_payments.unlink()
        env.cr.commit()
    
    count = 0
    reconciled_count = 0
    errors = 0
    
    # Data starts from row 10 (index 9)
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = str(r[3]).strip() if pd.notna(r[3]) and str(r[3]) != 'nan' else f"{idx}"
        narration = str(r[5]).strip() if pd.notna(r[5]) else ''
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        # Determine Destination and Amount
        dest_account_name = None
        amount = 0.0
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
        
        # Check if Part Name is one of our bank accounts (Transfer Case)
        is_transfer = any(part_name.lower() in val.lower() for val in dest_map.values())
        
        try:
            if is_transfer:
                # Handle as Internal Transfer OR just a Journal Entry (Payment model is more for partners)
                # But we can create a payment for transfer too
                source_journal = get_journal(part_name)
                payment = env['account.payment'].create({
                    'payment_type': 'internal',
                    'date': dt_str,
                    'amount': amount,
                    'journal_id': source_journal.id,
                    'destination_journal_id': journal.id,
                    'memo': f"REC_MIG/{vref} | {narration}",
                })
                payment.action_post()
                count += 1
            else:
                # Handle as Customer Receipt
                if not partner:
                    partner = env['res.partner'].create({'name': part_name, 'customer_rank': 1})
                
                payment = env['account.payment'].create({
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': partner.id,
                    'amount': amount,
                    'journal_id': journal.id,
                    'date': dt_str,
                    'memo': f"REC_MIG/{vref}",
                })
                # In modern Odoo, 'ref' is the memo field on payment
                payment.memo = f"REC_MIG/{vref} | {narration}"
                
                payment.action_post()
                count += 1
                
                # ── RECONCILIATION ───────────────────────────────────────────
                # Correct way for account.payment to reconcile:
                # Find the move created by the payment
                move = payment.move_id
                rec_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                if rec_line:
                    open_lines = env['account.move.line'].search([
                        ('partner_id', '=', partner.id),
                        ('account_id', '=', rec_line.account_id.id),
                        ('reconciled', '=', False),
                        ('move_id.move_type', '=', 'out_invoice'),
                        ('move_id.state', '=', 'posted'),
                        ('balance', '>', 0)
                    ], order='date asc')
                    if open_lines:
                        (rec_line | open_lines).reconcile()
                        reconciled_count += 1
                        
        except Exception as e:
            errors += 1
            print(f"  ERR row {idx}: {e}")
            
    env.cr.commit()
    print(f"\nMigration Finished. Total Payments: {count} | Reconciled: {reconciled_count} | Errors: {errors}")

migrate_as_payments()

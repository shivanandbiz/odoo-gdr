
import pandas as pd
from datetime import datetime
import odoo
from odoo import api, SUPERUSER_ID

def get_partner_intelligent(env, name):
    name = str(name).strip()
    if not name or name.lower() == 'nan': return False
    
    # 1. Exact match
    partner = env['res.partner'].search([('name', '=', name)], limit=1)
    if partner: return partner
    
    # 2. Case insensitive match
    partner = env['res.partner'].search([('name', '=ilike', name)], limit=1)
    if partner: return partner
    
    # 3. Partial match (ilike)
    partners = env['res.partner'].search([('name', 'ilike', name)])
    if not partners:
        # Try removing common suffixes
        clean_name = name.replace('PVT LTD', '').replace('PRIVATE LIMITED', '').replace('Ltd', '').replace('Pvt', '').strip()
        partners = env['res.partner'].search([('name', 'ilike', clean_name)])
        
    if partners:
        if len(partners) == 1:
            return partners[0]
        else:
            # Pick the one with the most invoices
            best_p = partners[0]
            max_inv = -1
            for p in partners:
                inv_count = env['account.move'].search_count([('partner_id', '=', p.id), ('move_type', '=', 'out_invoice')])
                if inv_count > max_inv:
                    max_inv = inv_count
                    best_p = p
            return best_p
            
    return False

def get_journal(env, name):
    if not name:
        return env['account.journal'].search([('type', '=', 'bank')], limit=1)
    
    name_str = str(name).upper()
    j = env['account.journal'].search(['|', ('name', '=', name), ('code', '=', name)], limit=1)
    if not j:
        if 'HDFC' in name_str or '50200024612749' in name_str:
            j = env['account.journal'].search([('name', 'ilike', '50200024612749')], limit=1)
        elif 'KOTAK' in name_str or '3545975369' in name_str:
            j = env['account.journal'].search([('name', 'ilike', '3545975369')], limit=1)
        elif 'GKP' in name_str:
            j = env['account.journal'].search([('name', 'ilike', 'Gkp')], limit=1)
        elif 'KARUR' in name_str:
            j = env['account.journal'].search([('name', 'ilike', 'Karur')], limit=1)
        elif 'CANARA' in name_str:
            j = env['account.journal'].search([('name', 'ilike', 'CANARA')], limit=1)
            
    if not j:
        j = env['account.journal'].search(['|', ('name', 'ilike', name), ('code', 'ilike', name)], limit=1)
            
    return j or env['account.journal'].search([('type', '=', 'bank')], limit=1)

def migrate_receipts_v5(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/Final_recipt_register_2025_2026.xlsx'
    df = pd.read_excel(file_path, header=8)
    df = df[df['Voucher Type'] == 'Receipt']
    
    print(f"Total Receipt records to process: {len(df)}")
    
    currency_inr = env['res.currency'].search([('name', '=', 'INR')], limit=1)
    if not currency_inr:
        currency_inr = env.company.currency_id

    dest_cols = [
        'HDFC C/A 50200024612749', 'Kotak -3545975369', 'Gkp Current A/c',
        'BANK CHARGES', 'Imprest - Shantalinga',
        'BG Rail Bhavan -009GT02231400001', 'FD INTEREST',
        'Cholamandalam Investment and Finance Cmpy LTD  Term', 'F D Amount',
        'Suspense', 'THE KARUR VYSYA BANK LIMITED -Unsecured'
    ]

    REF_PREFIX = "CR_25_26"
    count = 0
    errors = 0
    linked_to_inv = 0
    auto_reconciled = 0
    
    for idx, row in df.iterrows():
        try:
            part_name = str(row['Particulars']).strip() if pd.notna(row['Particulars']) else ''
            if not part_name or part_name.lower() == 'nan' or 'total' in part_name.lower():
                continue
                
            amount = float(row['Gross Total']) if pd.notna(row['Gross Total']) else 0.0
            if amount <= 0: continue

            raw_date = row['Date']
            if isinstance(raw_date, (datetime, pd.Timestamp)): date_val = raw_date
            else: date_val = pd.to_datetime(raw_date)
            dt_str = date_val.strftime('%Y-%m-%d')
                
            vref = str(row['Voucher Ref. No.']).strip() if pd.notna(row['Voucher Ref. No.']) else ''
            narration = str(row['Narration']).strip() if pd.notna(row['Narration']) else ''
            
            dest_account_name = None
            for col in dest_cols:
                if col in row and pd.notna(row[col]) and float(row[col] or 0) != 0:
                    dest_account_name = col
                    break
            
            journal = get_journal(env, dest_account_name)
            partner = get_partner_intelligent(env, part_name)
            if not partner:
                print(f"Partner not found: {part_name}. Creating...")
                partner = env['res.partner'].create({
                    'name': part_name, 
                    'customer_rank': 1,
                })
            
            ref = f"{REF_PREFIX}/{idx}"
            memo = f"{vref} | {narration}" if vref and narration else (vref or narration)
            memo = memo[:255]
            
            if env['account.move'].search_count([('ref', '=', ref)]):
                print(f"[{count+1}] Row {idx} Already migrated. Skipping.")
                count += 1
                continue

            receivable_account = partner.property_account_receivable_id
            bank_account = journal.default_account_id
            
            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': ref,
                'journal_id': journal.id,
                'line_ids': [
                    (0, 0, {
                        'name': memo,
                        'account_id': bank_account.id,
                        'debit': amount,
                        'partner_id': partner.id,
                    }),
                    (0, 0, {
                        'name': memo,
                        'account_id': receivable_account.id,
                        'credit': amount,
                        'partner_id': partner.id,
                    }),
                ]
            })
            move.action_post()
            
            # Link to account_payment
            mline = env['account.payment.method.line'].search([
                ('payment_type', '=', 'inbound'),
                ('journal_id', '=', journal.id)
            ], limit=1)
            
            env.cr.execute("""
                INSERT INTO account_payment 
                (amount, date, journal_id, partner_id, payment_type, partner_type, state, memo, move_id, company_id, currency_id, payment_method_line_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (amount, dt_str, journal.id, partner.id, 'inbound', 'customer', 'posted', memo, move.id, journal.company_id.id, currency_inr.id, mline.id if mline else None))
            
            payment_id = env.cr.fetchone()[0]
            env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (payment_id, move.id))

            rec_line = move.line_ids.filtered(lambda l: l.account_id.id == receivable_account.id)
            
            # Link to specific invoice if ref matches
            linked = False
            if vref:
                inv = env['account.move'].search([
                    ('ref', '=', vref),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'not in', ('paid', 'in_payment'))
                ], limit=1)
                
                if inv:
                    inv_lines = inv.line_ids.filtered(lambda l: l.account_id.id == receivable_account.id and not l.reconciled)
                    if inv_lines and rec_line:
                        (rec_line | inv_lines).reconcile()
                        linked_to_inv += 1
                        linked = True
                        print(f"[{count+1}] Linked to Invoice {inv.name}")
            
            # If not linked to specific, try auto-reconcile
            if not linked:
                open_inv_lines = env['account.move.line'].search([
                    ('partner_id', '=', partner.id),
                    ('account_id', '=', receivable_account.id),
                    ('reconciled', '=', False),
                    ('move_id.move_type', '=', 'out_invoice'),
                    ('debit', '>', 0)
                ], order='date asc, id asc')
                
                if open_inv_lines and rec_line and not rec_line.reconciled:
                     try:
                         (rec_line | open_inv_lines).reconcile()
                         auto_reconciled += 1
                         print(f"[{count+1}] Auto-reconciled with partner invoices")
                     except: pass
            
            if not linked and not (rec_line and rec_line.reconciled):
                print(f"[{count+1}] Created as standalone payment for {partner.name}")

            count += 1
            if count % 20 == 0:
                env.cr.commit()
                print(f"Committed {count} records...")
                
        except Exception as e:
            print(f"Error at idx {idx}: {e}")
            errors += 1
            env.cr.rollback()

    env.cr.commit()
    print(f"\nFINISH: Migrated {count} records.")
    print(f"Linked to specific Inv: {linked_to_inv}")
    print(f"Auto-reconciled: {auto_reconciled}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    migrate_receipts_v5(env)

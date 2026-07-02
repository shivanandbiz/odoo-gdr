
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
            # Pick the one with the most vendor bills (in_invoice)
            best_p = partners[0]
            max_inv = -1
            for p in partners:
                inv_count = env['account.move'].search_count([('partner_id', '=', p.id), ('move_type', '=', 'in_invoice')])
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
        elif 'CASH' in name_str or 'PETTY' in name_str:
            j = env['account.journal'].search([('type', '=', 'cash')], limit=1)
            
    if not j:
        j = env['account.journal'].search(['|', ('name', 'ilike', name), ('code', 'ilike', name)], limit=1)
            
    return j or env['account.journal'].search([('type', '=', 'bank')], limit=1)

def migrate_vendor_payments_v5(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/Final_payment_register_2025_2026.xlsx'
    xl = pd.ExcelFile(file_path)
    
    print(f"Sheets found: {xl.sheet_names}")
    
    currency_inr = env['res.currency'].search([('name', '=', 'INR')], limit=1)
    if not currency_inr:
        currency_inr = env.company.currency_id

    bank_keywords = ['HDFC', 'KOTAK', 'GKP', 'KARUR', 'CANARA', 'CASH', 'PETTY', 'BANK', 'KVB']
    REF_PREFIX = "VP_25_26"
    
    total_count = 0
    total_errors = 0
    total_reconciled = 0
    
    for sheet_name in xl.sheet_names:
        print(f"\n--- Processing Sheet: {sheet_name} ---")
        df = pd.read_excel(xl, sheet_name=sheet_name, header=8)
        
        # Identify account columns (after Gross Total)
        col_list = df.columns.tolist()
        try:
            start_idx = col_list.index('Gross Total') + 1
        except:
            # Fallback if Gross Total is not found
            try: start_idx = col_list.index('Value') + 1
            except: start_idx = 8
            
        account_cols = col_list[start_idx:]
        
        for idx, row in df.iterrows():
            try:
                part_name = str(row['Particulars']).strip() if pd.notna(row['Particulars']) else ''
                if not part_name or part_name.lower() == 'nan' or 'total' in part_name.lower():
                    continue
                
                amount = float(row['Gross Total']) if pd.notna(row['Gross Total']) else 0.0
                if amount == 0:
                    # Try to find amount in account columns if Gross Total is 0
                    for col in account_cols:
                        val = row[col]
                        if pd.notna(val) and float(val or 0) != 0:
                            amount = abs(float(val))
                            break
                            
                if amount <= 0: continue

                raw_date = row['Date']
                if not pd.notna(raw_date): continue
                if isinstance(raw_date, (datetime, pd.Timestamp)): date_val = raw_date
                else: date_val = pd.to_datetime(raw_date, errors='coerce')
                if not date_val: continue
                dt_str = date_val.strftime('%Y-%m-%d')
                
                narration = str(row['Narration']).strip() if pd.notna(row['Narration']) else ''
                vref = str(row['Voucher Ref. No.']).strip() if 'Voucher Ref. No.' in row and pd.notna(row['Voucher Ref. No.']) else ''
                
                source_name = ""
                target_name = ""
                
                is_part_bank = any(k in part_name.upper() for k in bank_keywords)
                
                if is_part_bank:
                    source_name = part_name
                    # Find target from account columns
                    for col in account_cols:
                        if pd.notna(row[col]) and float(row[col] or 0) != 0:
                            target_name = col
                            break
                else:
                    target_name = part_name
                    # Find source from account columns
                    for col in account_cols:
                        if any(k in str(col).upper() for k in bank_keywords):
                            if pd.notna(row[col]) and float(row[col] or 0) != 0:
                                source_name = col
                                break
                    if not source_name:
                        source_name = "HDFC C/A 50200024612749" # Default
                
                if not target_name: target_name = part_name
                
                journal = get_journal(env, source_name)
                partner = get_partner_intelligent(env, target_name)
                
                if not partner:
                    # Skip rows that are definitely not vendors if we want, 
                    # but here we'll create them to stay safe as per "migrate all"
                    # However, if it's "Gross Total" or similar, skip.
                    if 'TOTAL' in target_name.upper(): continue
                    print(f"Partner not found: {target_name}. Creating...")
                    partner = env['res.partner'].create({
                        'name': target_name,
                        'supplier_rank': 1,
                    })
                
                ref = f"{REF_PREFIX}/{sheet_name}/{idx}"
                memo = f"{vref} | {narration}".strip(" | ")
                memo = memo[:255]
                
                if env['account.move'].search_count([('ref', '=', ref)]):
                    continue

                payable_account = partner.property_account_payable_id
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
                            'credit': amount,
                            'partner_id': partner.id,
                        }),
                        (0, 0, {
                            'name': memo,
                            'account_id': payable_account.id,
                            'debit': amount,
                            'partner_id': partner.id,
                        }),
                    ]
                })
                move.action_post()
                
                # Link to account_payment via SQL
                mline = env['account.payment.method.line'].search([
                    ('payment_type', '=', 'outbound'),
                    ('journal_id', '=', journal.id)
                ], limit=1)
                
                env.cr.execute("""
                    INSERT INTO account_payment 
                    (amount, date, journal_id, partner_id, payment_type, partner_type, state, memo, move_id, company_id, currency_id, payment_method_line_id, amount_company_currency_signed, name) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (amount, dt_str, journal.id, partner.id, 'outbound', 'supplier', 'paid', memo, move.id, journal.company_id.id, currency_inr.id, mline.id if mline else None, -amount, move.name))
                
                payment_id = env.cr.fetchone()[0]
                env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (payment_id, move.id))

                # Auto-reconcile with Vendor Bills
                pay_line = move.line_ids.filtered(lambda l: l.account_id.id == payable_account.id and not l.reconciled)
                if pay_line:
                    bill_lines = env['account.move.line'].search([
                        ('partner_id', '=', partner.id),
                        ('account_id', '=', payable_account.id),
                        ('reconciled', '=', False),
                        ('move_id.move_type', '=', 'in_invoice'),
                        ('credit', '>', 0)
                    ], order='date asc, id asc')
                    if bill_lines:
                        try:
                            (pay_line | bill_lines).reconcile()
                            total_reconciled += 1
                        except: pass

                total_count += 1
                if total_count % 100 == 0:
                    env.cr.commit()
                    print(f"Processed {total_count} records...")
                    
            except Exception as e:
                print(f"Error at sheet {sheet_name} idx {idx}: {e}")
                total_errors += 1
                env.cr.rollback()

    env.cr.commit()
    print(f"\nFINISH: Migrated {total_count} records. Reconciled: {total_reconciled}. Errors: {total_errors}")

if __name__ == "__main__":
    migrate_vendor_payments_v5(env)

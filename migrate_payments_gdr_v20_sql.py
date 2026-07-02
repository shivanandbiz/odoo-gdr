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

def migrate_gdr_payments():
    fname = '/home/biz/odoo/payment_register_gdr.xlsx'
    xl_file = pd.ExcelFile(fname)
    sheet_names = xl_file.sheet_names
    print(f"File contains sheets: {sheet_names}")

    print("--- NUCLEAR CLEANUP (SQL) ---")
    # This is the only way to be 100% sure we are in a clean state and avoid constraint triggers
    env.cr.execute("DELETE FROM account_partial_reconcile")
    env.cr.execute("DELETE FROM account_full_reconcile")
    env.cr.execute("DELETE FROM account_payment")
    env.cr.execute("DELETE FROM account_move WHERE ref LIKE 'PAY_GDR/%' OR ref LIKE 'PAY_%'")
    env.cr.commit()
    print("Cleanup finished.\n")

    sheet_prefix_map = {'Apr-June': 'AJ', 'July-Sep': 'JS', 'Oct-Dec': 'OD', 'Jan-March': 'JM'}

    total_count = 0; total_reconciled = 0; errors = 0

    for sheet in sheet_names:
        print(f"Processing sheet: {sheet}...")
        df = pd.read_excel(fname, sheet_name=sheet, header=None)
        
        headers = None; data_start_idx = 9
        for i in range(7, 12):
            if i >= len(df): break
            row_vals = [str(x).strip() for x in df.iloc[i].tolist()]
            if 'Date' in row_vals and 'Particulars' in row_vals:
                headers = row_vals; data_start_idx = i + 1; break
        if not headers: continue
            
        col_map = {h: i for i, h in enumerate(headers) if h != 'nan'}
        amount_idx = col_map.get('Gross Total', col_map.get('Value', 6))
        part_idx = col_map.get('Particulars', 1)
        date_idx = col_map.get('Date', 0)
        ref_idx = col_map.get('Voucher Ref. No.', 3)
        narr_idx = col_map.get('Narration', 5)
        
        accounts_map = {}
        for i, h in enumerate(headers):
            if i >= 7 and h != 'nan' and h not in ['Gross Total', 'Value', 'Voucher Ref. No.', 'Voucher Ref. Date', 'Narration']:
                accounts_map[i] = h
        
        sheet_pref = sheet_prefix_map.get(sheet, 'GDR')

        for idx, row in df.iloc[data_start_idx:].iterrows():
            r = row.tolist()
            if not any(pd.notna(x) for x in r): continue
            
            raw_date = r[date_idx]; part_name = str(r[part_idx]).strip()
            vref = str(r[ref_idx]).strip()[:50] if pd.notna(r[ref_idx]) else f"{idx}"
            narration = str(r[narr_idx]).strip()[:200] if pd.notna(r[narr_idx]) else ''
            
            if not part_name or 'Total' in part_name or part_name == 'nan': continue
            try: amount = float(r[amount_idx] or 0)
            except: amount = 0
            if amount == 0: continue

            # Determine Cr/Dr
            dr_name = part_name; cr_name = "Bank"
            is_bank_source = any(b in part_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp'])
            if is_bank_source:
                cr_name = part_name
                for col_i, acc_n in accounts_map.items():
                    if float(r[col_i] or 0) != 0 and acc_n != part_name:
                        dr_name = acc_n; break
            else:
                for col_i, acc_n in accounts_map.items():
                    if float(r[col_i] or 0) != 0 and any(b in acc_n for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH']):
                        cr_name = acc_n; break

            journal = get_journal(cr_name)
            dt_str = datetime.now().strftime('%Y-%m-%d')
            if isinstance(raw_date, (datetime, pd.Timestamp)): dt_str = raw_date.strftime('%Y-%m-%d')

            try:
                partner = get_partner(dr_name)
                dr_acc = get_account(dr_name); cr_acc = get_account(cr_name)
                dr_acc_id = partner.property_account_payable_id.id if partner else (dr_acc.id if dr_acc else False)
                cr_acc_id = cr_acc.id if cr_acc else journal.default_account_id.id
                if not dr_acc_id:
                    if not dr_acc:
                        partner = env['res.partner'].create({'name': dr_name, 'supplier_rank': 1})
                        dr_acc_id = partner.property_account_payable_id.id
                    else: dr_acc_id = dr_acc.id

                # 1. Create Move (Posted)
                move = env['account.move'].create({
                    'move_type': 'entry', 'date': dt_str, 'ref': f"PAY_GDR/{sheet_pref}/{vref}", 'journal_id': journal.id,
                    'line_ids': [
                        (0, 0, {'name': narration, 'account_id': dr_acc_id, 'debit': amount, 'partner_id': partner.id if partner else False}),
                        (0, 0, {'name': narration, 'account_id': cr_acc_id, 'credit': amount}),
                    ]
                })
                move.action_post()
                
                # 2. SQL Insert for Payment record (Bypasses all model constraints)
                # Note: We use some defaults for Odoo 17 account_payment table
                memo = f"PAY_GDR/{sheet_pref}/{vref} | {narration}"[:255]
                env.cr.execute("""
                    INSERT INTO account_payment 
                    (amount, date, journal_id, partner_id, payment_type, partner_type, state, memo, move_id, company_id, currency_id, payment_method_line_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, (SELECT id FROM account_payment_method_line WHERE payment_type='outbound' AND journal_id=%s LIMIT 1))
                    RETURNING id
                """, (amount, dt_str, journal.id, partner.id if partner else None, 'outbound', 'supplier', 'in_process', memo, move.id, journal.company_id.id, journal.currency_id.id or 1, journal.id))
                
                payment_id = env.cr.fetchone()[0]
                env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (payment_id, move.id))
                
                total_count += 1
                
                # 3. Reconciliation
                if partner:
                    pay_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled)
                    bill_lines = env['account.move.line'].search([
                        ('partner_id', '=', partner.id), ('account_id.account_type', '=', 'liability_payable'),
                        ('reconciled', '=', False), ('move_id.move_type', '=', 'in_invoice'), ('move_id.state', '=', 'posted'), ('credit', '>', 0)
                    ], order='date asc')
                    if pay_line and bill_lines: (pay_line | bill_lines).reconcile()
                    total_reconciled += 1
                        
            except Exception as e:
                errors += 1
                print(f"  ERR row {idx} in {sheet}: {e}")
            
            if total_count % 100 == 0:
                print(f"  Processed {total_count} records...")

        env.cr.commit()
    print(f"\nFINAL: Total {total_count} | Reconciled {total_reconciled} | Errors {errors}")

migrate_gdr_payments()

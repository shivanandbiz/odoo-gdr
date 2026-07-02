import pandas as pd
from datetime import datetime

def get_partner(name):
    if not name: return None
    p = env['res.partner'].search([('name', '=ilike', name)], limit=1)
    if not p: p = env['res.partner'].search([('name', 'ilike', name)], limit=1)
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

def migrate_all_vendor_payments():
    fname = '/home/biz/odoo/payment_register_gdr.xlsx'
    print(f"Reading {fname}...")
    xl_file = pd.ExcelFile(fname)
    sheet_names = xl_file.sheet_names
    
    inr_currency = env.ref('base.INR')
    sheet_prefix_map = {'Apr-June': 'AJ', 'July-Sep': 'JS', 'Oct-Dec': 'OD', 'Jan-March': 'JM'}

    total_count = 0; total_reconciled = 0; errors = 0

    print("Cleaning up older manual PAY_GDR moves (if any)...")
    legacy = env['account.move'].search([('ref', 'like', 'PAY_GDR/%')])
    if legacy:
        legacy.button_draft()
        legacy.unlink()

    for sheet in sheet_names:
        print(f"\nProcessing sheet: {sheet}...")
        df = pd.read_excel(fname, sheet_name=sheet, header=None)
        
        headers = None; data_start_idx = 9
        for i in range(7, 12):
            if i >= len(df): break
            row_vals = [str(x).strip() for x in df.iloc[i].tolist()]
            if 'Date' in row_vals and 'Particulars' in row_vals:
                headers = row_vals; data_start_idx = i + 1; break
        if not headers: 
            print(f"  Could not find headers in {sheet}, skipping.")
            continue
            
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
            except: amount = 0.0
            if amount == 0: continue

            dr_name = part_name; cr_name = "Bank"
            is_bank_source = any(b in part_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp'])
            if is_bank_source:
                cr_name = part_name
                for col_i, acc_n in accounts_map.items():
                    val = float(r[col_i] or 0) if pd.notna(r[col_i]) else 0.0
                    if val != 0 and acc_n != part_name:
                        dr_name = acc_n; break
            else:
                for col_i, acc_n in accounts_map.items():
                    val = float(r[col_i] or 0) if pd.notna(r[col_i]) else 0.0
                    if val != 0 and any(b in acc_n for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH']):
                        cr_name = acc_n; break

            journal = get_journal(cr_name)
            
            if isinstance(raw_date, (datetime, pd.Timestamp)): dt_str = raw_date.strftime('%Y-%m-%d')
            else:
                try: dt_str = str(raw_date)[:10]
                except: dt_str = datetime.now().strftime('%Y-%m-%d')

            try:
                partner = get_partner(dr_name)
                
                # Bank/Internal transfer check
                is_transfer = any(b in dr_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp'])
                
                if is_transfer:
                    dest_journal = get_journal(dr_name)
                    move = env['account.move'].create({
                        'move_type': 'entry', 'date': dt_str, 'ref': f"PAY_GDR/{sheet_pref}/{vref}", 'journal_id': journal.id,
                        'line_ids': [
                            (0, 0, {'name': narration or "Internal Transfer", 'account_id': dest_journal.default_account_id.id, 'debit': amount}),
                            (0, 0, {'name': narration or "Internal Transfer", 'account_id': journal.default_account_id.id, 'credit': amount}),
                        ]
                    })
                    try: move.action_post()
                    except Exception as pe: print(f"  Row {idx} transfer post fail: {pe}")
                    total_count += 1
                
                else:
                    dr_acc = get_account(dr_name); cr_acc = get_account(cr_name)
                    dr_acc_id = partner.property_account_payable_id.id if partner else (dr_acc.id if dr_acc else False)
                    cr_acc_id = cr_acc.id if cr_acc else journal.default_account_id.id
                    if not dr_acc_id:
                        if not dr_acc:
                            partner = env['res.partner'].create({'name': dr_name, 'supplier_rank': 1})
                            dr_acc_id = partner.property_account_payable_id.id
                        else: dr_acc_id = dr_acc.id

                    move = env['account.move'].create({
                        'move_type': 'entry', 'date': dt_str, 'ref': f"PAY_GDR/{sheet_pref}/{vref}", 'journal_id': journal.id,
                        'line_ids': [
                            (0, 0, {'name': f"Payment: {part_name} | {narration}", 'account_id': dr_acc_id, 'debit': amount, 'partner_id': partner.id if partner else False, 'currency_id': inr_currency.id}),
                            (0, 0, {'name': f"Payment: {part_name} | {narration}", 'account_id': cr_acc_id, 'credit': amount, 'currency_id': inr_currency.id}),
                        ]
                    })
                    
                    try:
                        with env.cr.savepoint(): move.action_post()
                    except Exception as pe:
                        print(f"  Row {idx} move skip: {pe}")
                        continue

                    mline = env['account.payment.method.line'].search([('payment_type','=','outbound'),('journal_id','=',journal.id)], limit=1)
                    mline_id = mline.id if mline else None
                    
                    memo = f"PAY_GDR/{sheet_pref}/{vref} | {narration}"[:255]
                    env.cr.execute("""
                        INSERT INTO account_payment 
                        (amount, date, journal_id, partner_id, payment_type, partner_type, state, memo, move_id, company_id, currency_id, payment_method_line_id) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (amount, dt_str, journal.id, partner.id if partner else None, 'outbound', 'supplier', 'in_process', memo, move.id, journal.company_id.id, inr_currency.id, mline_id))
                    
                    payment_id = env.cr.fetchone()[0]
                    env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (payment_id, move.id))
                    
                    total_count += 1
                    
                    if partner:
                        try:
                            with env.cr.savepoint():
                                pay_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled)
                                bill_lines = env['account.move.line'].search([
                                    ('partner_id', '=', partner.id), ('account_id.account_type', '=', 'liability_payable'),
                                    ('reconciled', '=', False), ('move_id.move_type', '=', 'in_invoice'), ('move_id.state', '=', 'posted'), ('credit', '>', 0)
                                ], order='date asc')
                                if pay_line and bill_lines:
                                    (pay_line | bill_lines).reconcile()
                                    total_reconciled += 1
                        except Exception as re:
                            print(f"  Row {idx} recon fail: {re}")
                            
            except Exception as e:
                errors += 1
                print(f"  ERR row {idx} in {sheet}: {e}")
            
            if total_count % 100 == 0:
                env.cr.commit()

        env.cr.commit()
    print(f"\nFINAL SUCCESS: Total Payments Created: {total_count} | Reconciled: {total_reconciled} | Errors: {errors}")

migrate_all_vendor_payments()

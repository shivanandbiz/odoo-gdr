import pandas as pd
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

def get_partner(env, name):
    if not name or str(name).lower() == 'nan':
        return env['res.partner']
    name = str(name).strip()
    if name.lower() == 'gross total':
        return env['res.partner']
    partner = env['res.partner'].search([('name', '=', name)], limit=1)
    if not partner:
        partner = env['res.partner'].search([('name', '=ilike', name)], limit=1)
    return partner

def get_account(env, name):
    if not name or str(name).lower() in ['nan', 'None', '']:
        return env['account.account']
    acc = env['account.account'].search([('name', 'ilike', str(name).strip())], limit=1)
    if not acc:
        acc = env['account.account'].search([('code', '=', str(name).strip())], limit=1)
    return acc

def get_journal(env, name):
    if not name:
        return env['account.journal'].search([('type', '=', 'bank')], limit=1)
    j = env['account.journal'].search([('name', 'ilike', str(name).strip())], limit=1)
    if not j:
        j = env['account.journal'].search([('code', 'ilike', str(name).strip())], limit=1)
    if not j:
        if 'cash' in str(name).lower():
            j = env['account.journal'].search([('type', '=', 'cash')], limit=1)
        else:
            j = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def migrate_payments(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/Final_payment_register_2025_2026.xlsx'
    xl = pd.ExcelFile(file_path)
    
    bank_keywords = ['hdfc', 'karur vysya', 'kvb', 'cash', 'petty cash', 'bank', 'shantalinga', 'imprest']
    
    total_count = 0
    total_reconciled = 0
    total_errors = 0
    total_skipped = 0
    REF_PREFIX = "BP_25_26"
    
    company_currency = env.company.currency_id

    for sheet_name in xl.sheet_names:
        print(f"\n--- Processing Sheet: {sheet_name} ---")
        df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
        
        header_idx = -1
        for i in range(min(20, len(df))):
            row_values = [str(x).lower() for x in df.iloc[i]]
            if 'particulars' in row_values:
                header_idx = i
                break
        
        if header_idx == -1:
            print(f"Could not find header in sheet {sheet_name}. Skipping.")
            continue
            
        headers = df.iloc[header_idx].tolist()
        data_df = df.iloc[header_idx + 1:]
        
        col_date = -1
        col_part = -1
        col_narr = -1
        col_gross = -1
        account_cols = {}
        
        for idx, h in enumerate(headers):
            h_str = str(h).lower().strip()
            if h_str == 'date': col_date = idx
            elif h_str == 'particulars': col_part = idx
            elif h_str == 'narration': col_narr = idx
            elif 'gross' in h_str or 'total' in h_str or 'value' in h_str: 
                if col_gross == -1: col_gross = idx
            if idx > 4 and pd.notna(h):
                account_cols[idx] = str(h).strip()

        for ridx, row in data_df.iterrows():
            ref = f"{REF_PREFIX}/{sheet_name}/{ridx}"
            if env['account.move'].search_count([('ref', '=', ref)]):
                total_skipped += 1
                continue

            try:
                with env.cr.savepoint():
                    date_val = row[col_date]
                    if not pd.to_datetime(date_val, errors='coerce'):
                        continue

                    particulars_raw = row[col_part]
                    particulars = str(particulars_raw).strip() if pd.notna(particulars_raw) else ""
                    narration = str(row[col_narr]).strip() if pd.notna(row[col_narr]) else ""
                    
                    if not particulars or particulars.lower() in ['nan', '', 'none', 'gross total']:
                        continue
                    if 'total' in particulars.lower() and 'grand' in particulars.lower():
                        continue
                    
                    gross_total = 0.0
                    if col_gross != -1 and pd.notna(row[col_gross]):
                        try: gross_total = float(row[col_gross])
                        except: pass
                    
                    if gross_total == 0:
                        found_val = False
                        for c_idx in account_cols:
                            if pd.notna(row[c_idx]):
                                try:
                                    val = float(row[c_idx])
                                    if val != 0:
                                        gross_total = val
                                        found_val = True
                                        break
                                except: pass
                        if not found_val: continue

                    dt_str = pd.to_datetime(date_val).strftime('%Y-%m-%d')

                    source_name = ""
                    target_name = ""
                    is_particulars_bank = any(k in particulars.lower() for k in bank_keywords)
                    
                    if particulars and is_particulars_bank:
                        source_name = particulars
                        for c_idx, acc_name in account_cols.items():
                            if pd.notna(row[c_idx]):
                                try:
                                    val = float(row[c_idx])
                                    if val != 0:
                                        target_name = acc_name
                                        gross_total = val
                                        break
                                except: pass
                    elif particulars:
                        target_name = particulars
                        for c_idx, acc_name in account_cols.items():
                            if any(k in acc_name.lower() for k in bank_keywords):
                                if pd.notna(row[c_idx]):
                                    try:
                                        val = float(row[c_idx])
                                        if val != 0:
                                            source_name = acc_name
                                            gross_total = val
                                            break
                                    except: pass
                    
                    if not target_name:
                        if narration: target_name = narration[:64]
                        else: target_name = particulars or "Unknown Partner"
                    
                    if target_name.lower() == 'gross total':
                        continue

                    if not source_name:
                        source_name = "HDFC C/A" 

                    journal = get_journal(env, source_name)
                    partner = get_partner(env, target_name)
                    
                    # Target Account (Liability)
                    target_acc_id = False
                    if partner:
                        target_acc_id = partner.property_account_payable_id.id
                    else:
                        acc = get_account(env, target_name)
                        if acc: target_acc_id = acc.id
                        else:
                            partner = env['res.partner'].create({'name': target_name, 'supplier_rank': 1})
                            target_acc_id = partner.property_account_payable_id.id

                    # Source Account (Asset)
                    src_acc = get_account(env, source_name)
                    src_acc_id = src_acc.id if src_acc else journal.default_account_id.id

                    move = env['account.move'].create({
                        'move_type': 'entry',
                        'date': dt_str,
                        'ref': ref,
                        'journal_id': journal.id,
                        'line_ids': [
                            (0, 0, {
                                'name': f"Payment: {target_name} | {narration}"[:64],
                                'account_id': target_acc_id,
                                'debit': gross_total,
                                'partner_id': partner.id if partner else False,
                                'currency_id': company_currency.id,
                                'amount_currency': gross_total,
                            }),
                            (0, 0, {
                                'name': f"Payment: {target_name} | {narration}"[:64],
                                'account_id': src_acc_id,
                                'credit': gross_total,
                                'partner_id': partner.id if partner else False,
                                'currency_id': company_currency.id,
                                'amount_currency': -gross_total,
                            }),
                        ]
                    })
                    move.action_post()
                    
                    mline = env['account.payment.method.line'].search([
                        ('payment_type', '=', 'outbound'),
                        ('journal_id', '=', journal.id)
                    ], limit=1)
                    
                    env.cr.execute("""
                        INSERT INTO account_payment 
                        (amount, date, journal_id, partner_id, payment_type, partner_type, state, memo, move_id, company_id, currency_id, payment_method_line_id) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (gross_total, dt_str, journal.id, partner.id if partner else None, 'outbound', 'supplier', 'posted', narration[:255], move.id, journal.company_id.id, company_currency.id, mline.id if mline else None))
                    
                    payment_id = env.cr.fetchone()[0]
                    env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (payment_id, move.id))

                    total_count += 1
                    
                    if partner:
                        try:
                            pay_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable' and l.debit > 0 and not l.reconciled)
                            if pay_line:
                                bill_lines = env['account.move.line'].search([
                                    ('partner_id', '=', partner.id),
                                    ('account_id.account_type', '=', 'liability_payable'),
                                    ('reconciled', '=', False),
                                    ('move_id.move_type', '=', 'in_invoice'),
                                    ('move_id.state', '=', 'posted'),
                                    ('credit', '>', 0)
                                ], order='date asc')
                                if bill_lines:
                                    (pay_line | bill_lines).reconcile()
                                    total_reconciled += 1
                        except: pass

            except Exception as e:
                total_errors += 1
                print(f"Error on sheet {sheet_name} row {ridx}: {e}")

        env.cr.commit()

    print(f"\nMigration Summary:")
    print(f"Total Payments Created: {total_count}")
    print(f"Total Payments Skipped: {total_skipped}")
    print(f"Total Reconciled: {total_reconciled}")
    print(f"Total Errors: {total_errors}")

if __name__ == '__main__':
    pass

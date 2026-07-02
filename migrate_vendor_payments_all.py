
import pandas as pd
from datetime import datetime

def migrate_vendor_payments_all_sheets(env):
    file_path = "/home/biz/GDR_Original_Data/Final Data/Final_payment_register_2025_2026.xlsx"
    xl = pd.ExcelFile(file_path)
    sheet_names = xl.sheet_names
    print(f"Detected sheets: {sheet_names}")
    
    total_count = 0
    reconciled_count = 0
    skipped_count = 0
    errors = 0
    
    # Pre-fetch journals
    journals = {j.name: j for j in env['account.journal'].search([('type', 'in', ('bank', 'cash'))])}
    for j in env['account.journal'].search([('type', '=', 'bank')]):
        if j.code: journals[j.code] = j
        if j.name:
            if '50200024612749' in j.name: journals['HDFC'] = j
            if '3545975369' in j.name: journals['Kotak'] = j

    def get_best_journal(name):
        if name in journals: return journals[name]
        if 'HDFC' in name: return journals.get('HDFC')
        if 'Kotak' in name: return journals.get('Kotak')
        match = env['account.journal'].search([('name', 'ilike', name)], limit=1)
        if match: return match
        return env['account.journal'].search([('type', '=', 'bank')], limit=1)

    for sheet in sheet_names:
        print(f"\n--- Processing Sheet: {sheet} ---")
        df = pd.read_excel(file_path, sheet_name=sheet, header=8)
        bank_cols = [c for c in df.columns.tolist() if c not in ['Date', 'Particulars', 'Voucher Type', 'Voucher No.', 'Voucher Ref. No.', 'Voucher Ref. Date', 'Narration', 'Gross Total', 'Value']]
        
        for idx, row in df.iterrows():
            part_name = str(row['Particulars']).strip()
            if not part_name or 'Total' in part_name or part_name == 'nan':
                continue
                
            try:
                amount = float(row['Gross Total'] or row.get('Value', 0))
                if amount == 0: continue
                
                vref_raw = str(row['Voucher Ref. No.']).strip() if pd.notna(row['Voucher Ref. No.']) else f"{sheet}_{idx}"
                vref = f"VENDOR_PAY/{vref_raw}"
                
                # Check for existing
                existing = env['account.move'].search([('ref', '=', vref)], limit=1)
                if existing:
                    skipped_count += 1
                    continue

                # Find Bank/Cash source
                source_journal = None
                for b_col in bank_cols:
                    if b_col in row:
                        val = row[b_col]
                        if pd.notna(val) and float(val or 0) > 0:
                            source_journal = get_best_journal(b_col)
                            break
                
                if not source_journal:
                    source_journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)

                partner = env['res.partner'].search([('name', '=ilike', part_name)], limit=1)
                if not partner:
                    partner = env['res.partner'].search([('name', 'ilike', part_name)], limit=1)
                
                dest_acc = partner.property_account_payable_id if partner else None
                if not dest_acc:
                    dest_acc = env['account.account'].search([('name', '=ilike', part_name)], limit=1)
                if not dest_acc:
                    dest_acc = env['account.account'].search([('account_type', '=', 'liability_payable')], limit=1)

                date_val = row['Date']
                if isinstance(date_val, (datetime, pd.Timestamp)):
                    dt_str = date_val.strftime('%Y-%m-%d')
                else:
                    dt_str = str(date_val)[:10]

                narration = str(row['Narration']).strip()[:200] if pd.notna(row['Narration']) else ''
                
                # Create Move
                move = env['account.move'].create({
                    'move_type': 'entry',
                    'date': dt_str,
                    'ref': vref,
                    'journal_id': source_journal.id,
                    'line_ids': [
                        (0, 0, {
                            'name': narration or f"Vendor Payment: {part_name}",
                            'account_id': dest_acc.id,
                            'debit': amount,
                            'partner_id': partner.id if partner else False,
                        }),
                        (0, 0, {
                            'name': narration or f"Vendor Payment: {part_name}",
                            'account_id': source_journal.default_account_id.id,
                            'credit': amount,
                        }),
                    ]
                })
                move.action_post()
                
                # Create Payment Record
                mline = env['account.payment.method.line'].search([('payment_type','=','outbound'),('journal_id','=',source_journal.id)], limit=1)
                memo = f"{vref} | {narration}"[:255]
                env.cr.execute("""
                    INSERT INTO account_payment 
                    (amount, date, journal_id, partner_id, payment_type, partner_type, state, memo, move_id, company_id, currency_id, payment_method_line_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (amount, dt_str, source_journal.id, partner.id if partner else None, 'outbound', 'supplier', 'posted', memo, move.id, source_journal.company_id.id, source_journal.currency_id.id or 1, mline.id if mline else None))
                
                pay_id = env.cr.fetchone()[0]
                env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (pay_id, move.id))
                
                total_count += 1
                
                # Reconciliation
                if partner:
                    try:
                        with env.cr.savepoint():
                            pay_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled)
                            bill_lines = env['account.move.line'].search([
                                ('partner_id', '=', partner.id), ('account_id.account_type', '=', 'liability_payable'),
                                ('reconciled', '=', False), ('move_id.move_type', '=', 'in_invoice'), ('move_id.state', '=', 'posted'), ('balance', '<', 0)
                            ], order='date asc, id asc')
                            if pay_line and bill_lines:
                                (pay_line | bill_lines).reconcile()
                                reconciled_count += 1
                    except: pass

            except Exception as e:
                errors += 1
                print(f"Error at {sheet}:{idx}: {e}")
            
            if total_count % 50 == 0 and total_count > 0:
                env.cr.commit()

    env.cr.commit()
    print(f"\nMigration Complete.")
    print(f"Total New: {total_count}, Skipped: {skipped_count}, Reconciled: {reconciled_count}, Errors: {errors}")

if __name__ == "__main__":
    migrate_vendor_payments_all_sheets(env)

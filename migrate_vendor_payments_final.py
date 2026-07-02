
import pandas as pd
from datetime import datetime

def migrate_vendor_payments(env):
    file_path = "/home/biz/GDR_Original_Data/Final Data/Final_payment_register_2025_2026.xlsx"
    df = pd.read_excel(file_path, header=8)
    
    print(f"Loaded {len(df)} rows from {file_path}")
    
    bank_cols = df.columns.tolist()[7:]
    
    total_count = 0
    reconciled_count = 0
    errors = 0
    
    # Pre-fetch some journals
    journals = {j.name: j for j in env['account.journal'].search([('type', 'in', ('bank', 'cash'))])}
    # Add by code/account number
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

    for idx, row in df.iterrows():
        part_name = str(row['Particulars']).strip()
        if not part_name or 'Total' in part_name or part_name == 'nan':
            continue
            
        try:
            amount = float(row['Gross Total'] or 0)
            if amount == 0: continue
            
            # Find Source (Bank/Cash)
            source_journal = None
            source_acc_name = None
            for b_col in bank_cols:
                val = row[b_col]
                if pd.notna(val) and float(val or 0) > 0:
                    source_acc_name = b_col
                    source_journal = get_best_journal(b_col)
                    break
            
            if not source_journal:
                # Default to Bank if no column matched but amount exists
                source_journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)

            # Find Target (Partner or Account)
            partner = env['res.partner'].search([('name', '=ilike', part_name)], limit=1)
            if not partner:
                partner = env['res.partner'].search([('name', 'ilike', part_name)], limit=1)
            
            # Determine Accounts
            dest_acc = None
            if partner:
                dest_acc = partner.property_account_payable_id
            else:
                dest_acc = env['account.account'].search([('name', '=ilike', part_name)], limit=1)
                if not dest_acc:
                    dest_acc = env['account.account'].search([('name', 'ilike', part_name)], limit=1)
            
            if not dest_acc:
                # If still no account, and not a partner, maybe create partner?
                # But safer to use a fallback or skip with error
                dest_acc = env['account.account'].search([('account_type', '=', 'liability_payable')], limit=1)

            date_val = row['Date']
            if isinstance(date_val, (datetime, pd.Timestamp)):
                dt_str = date_val.strftime('%Y-%m-%d')
            else:
                dt_str = str(date_val)[:10]

            vref = str(row['Voucher Ref. No.']).strip() if pd.notna(row['Voucher Ref. No.']) else f"{idx}"
            narration = str(row['Narration']).strip()[:200] if pd.notna(row['Narration']) else ''
            
            # Create Move (Accounting Impact)
            move_vals = {
                'move_type': 'entry',
                'date': dt_str,
                'ref': f"VENDOR_PAY/{vref}",
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
            }
            
            move = env['account.move'].create(move_vals)
            move.action_post()
            
            # Create Payment Record (UI Visibility)
            mline = env['account.payment.method.line'].search([('payment_type','=','outbound'),('journal_id','=',source_journal.id)], limit=1)
            
            memo = f"VENDOR_PAY/{vref} | {narration}"[:255]
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
                            ('partner_id', '=', partner.id),
                            ('account_id.account_type', '=', 'liability_payable'),
                            ('reconciled', '=', False),
                            ('move_id.move_type', '=', 'in_invoice'),
                            ('move_id.state', '=', 'posted'),
                            ('balance', '<', 0) # Bills have credit balance (negative total)
                        ], order='date asc, id asc')
                        if pay_line and bill_lines:
                            (pay_line | bill_lines).reconcile()
                            reconciled_count += 1
                except Exception as re:
                    pass

            if total_count % 100 == 0:
                print(f"Processed {total_count} records...")
                env.cr.commit()
                
        except Exception as e:
            errors += 1
            print(f"Error at row {idx}: {e}")
            
    env.cr.commit()
    print(f"\nMigration Complete. Total: {total_count}, Reconciled: {reconciled_count}, Errors: {errors}")

if __name__ == "__main__":
    migrate_vendor_payments(env)


import pandas as pd
from datetime import datetime
import odoo
from odoo import api, SUPERUSER_ID

def get_partner(env, name):
    name = name.strip()
    if not name: return False
    partner = env['res.partner'].search([('name', '=', name)], limit=1)
    if not partner:
        partner = env['res.partner'].search([('name', 'ilike', name)], limit=1)
    return partner

def get_journal(env, name):
    if not name:
        return env['account.journal'].search([('type', '=', 'bank')], limit=1)
    j = env['account.journal'].search(['|', ('name', 'ilike', name), ('code', 'ilike', name)], limit=1)
    if not j:
        if 'HDFC' in name.upper():
            j = env['account.journal'].search([('name', 'ilike', '50200024612749')], limit=1)
        elif 'KOTAK' in name.upper():
            j = env['account.journal'].search([('name', 'ilike', '3545975369')], limit=1)
    return j or env['account.journal'].search([('type', '=', 'bank')], limit=1)

def migrate_v2(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/Final_recipt_register_2025_2026.xlsx'
    print(f"Reading Excel: {file_path}")
    df = pd.read_excel(file_path, skiprows=8)
    
    # Dest map (based on column headers in row 8)
    dest_map = {
        'HDFC C/A 50200024612749': '50200024612749',
        'Kotak -3545975369': '3545975369',
        'Gkp Current A/c': 'Gkp Current A/c',
        'BANK CHARGES': 'BANK CHARGES',
        'Imprest - Shantalinga': 'Imprest - Shantalinga',
        'BG Rail Bhavan -009GT02231400001': 'BG Rail Bhavan',
        'FD INTEREST': 'FD INTEREST',
        'Cholamandalam Investment and Finance Cmpy LTD  Term': 'Cholamandalam',
        'F D Amount': 'F D Amount',
        'Suspense': 'Suspense',
        'THE KARUR VYSYA BANK LIMITED -Unsecured': 'Karur Vysya'
    }

    inr_currency = env.ref('base.INR')
    total_processed = 0
    payments_created = 0
    reconciled_count = 0
    errors = 0

    print("Starting migration V2...")

    for idx, row in df.iterrows():
        try:
            part_name = str(row['Particulars']).strip() if pd.notna(row['Particulars']) else ''
            if not part_name or part_name.lower() == 'nan' or 'total' in part_name.lower():
                continue
            
            amount = float(row['Gross Total']) if pd.notna(row['Gross Total']) else 0.0
            if amount <= 0:
                continue

            total_processed += 1
            
            raw_date = row['Date']
            if isinstance(raw_date, (datetime, pd.Timestamp)):
                dt_str = raw_date.strftime('%Y-%m-%d')
            else:
                dt_str = str(raw_date)[:10]

            vref = str(row['Voucher Ref. No.']).strip() if pd.notna(row['Voucher Ref. No.']) else ''
            narration = str(row['Narration']).strip() if pd.notna(row['Narration']) else ''
            
            dest_account_name = None
            for col in dest_map.keys():
                if col in row and pd.notna(row[col]) and float(row[col] or 0) != 0:
                    dest_account_name = dest_map[col]
                    break
            
            journal = get_journal(env, dest_account_name)
            partner = get_partner(env, part_name)
            
            if not partner:
                print(f"  Row {idx}: Creating missing partner: {part_name}")
                partner = env['res.partner'].create({'name': part_name, 'customer_rank': 1})
            
            # Create account.payment using ORM (cleaner)
            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': partner.id,
                'amount': amount,
                'date': dt_str,
                'journal_id': journal.id,
                'memo': f"{vref} | {narration}"[:255] if vref else narration[:255],
                'currency_id': inr_currency.id,
            }
            
            payment = env['account.payment'].create(payment_vals)
            payment.action_post()
            payments_created += 1

            # Reconciliation
            try:
                rec_line = payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                if rec_line:
                    matched_invoice = False
                    if vref:
                        inv = env['account.move'].search([
                            ('ref', '=', vref),
                            ('move_type', '=', 'out_invoice'),
                            ('state', '=', 'posted'),
                            ('payment_state', 'in', ('not_paid', 'partial'))
                        ], limit=1)
                        if inv:
                            inv_line = inv.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
                            if inv_line:
                                (rec_line | inv_line).reconcile()
                                matched_invoice = True
                    
                    if not matched_invoice:
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
                            matched_invoice = True
                    
                    if matched_invoice:
                        reconciled_count += 1
            except Exception as rec_err:
                print(f"  Row {idx} reconciliation error: {rec_err}")

        except Exception as e:
            print(f"  Error on row {idx}: {e}")
            errors += 1

    env.cr.commit()
    print(f"\nMigration V2 Summary:")
    print(f"Total Rows Found: {total_processed}")
    print(f"Payments Created: {payments_created}")
    print(f"Reconciled: {reconciled_count}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    pass

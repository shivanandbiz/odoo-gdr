
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
    j = env['account.journal'].search(['|', ('name', 'ilike', name), ('code', 'ilike', name)], limit=1)
    if not j:
        if name and 'HDFC' in name.upper():
            j = env['account.journal'].search([('name', 'ilike', '50200024612749')], limit=1)
        elif name and 'KOTAK' in name.upper():
            j = env['account.journal'].search([('name', 'ilike', '3545975369')], limit=1)
    return j or env['account.journal'].search([('type', '=', 'bank')], limit=1)

def migrate_v3(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/Final_recipt_register_2025_2026.xlsx'
    df = pd.read_excel(file_path, skiprows=8)
    
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

    payments_created = 0
    invoices_paid = 0

    for idx, row in df.iterrows():
        try:
            part_name = str(row['Particulars']).strip() if pd.notna(row['Particulars']) else ''
            if not part_name or part_name.lower() == 'nan' or 'total' in part_name.lower(): continue
            amount = float(row['Gross Total']) if pd.notna(row['Gross Total']) else 0.0
            if amount <= 0: continue

            raw_date = row['Date']
            dt_str = raw_date.strftime('%Y-%m-%d') if isinstance(raw_date, (datetime, pd.Timestamp)) else str(raw_date)[:10]
            vref = str(row['Voucher Ref. No.']).strip() if pd.notna(row['Voucher Ref. No.']) else ''
            narration = str(row['Narration']).strip() if pd.notna(row['Narration']) else ''
            
            dest_account_name = None
            for col, val in dest_map.items():
                if col in row and pd.notna(row[col]) and float(row[col] or 0) != 0:
                    dest_account_name = val
                    break
            
            journal = get_journal(env, dest_account_name)
            partner = get_partner(env, part_name) or env['res.partner'].create({'name': part_name, 'customer_rank': 1})
            
            # Search for matching invoice
            inv = False
            if vref:
                inv = env['account.move'].search([
                    ('ref', '=', vref),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'not in', ('paid', 'in_payment'))
                ], limit=1)
            
            if not inv:
                # Try search by partner and amount
                inv = env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('amount_total', '=', amount),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'not in', ('paid', 'in_payment'))
                ], limit=1)

            if inv:
                # Register payment on invoice
                ctx = {'active_model': 'account.move', 'active_ids': [inv.id]}
                register = env['account.payment.register'].with_context(ctx).create({
                    'journal_id': journal.id,
                    'amount': amount,
                    'payment_date': dt_str,
                    'communication': f"{vref} | {narration}"[:255] if vref else narration[:255],
                })
                register._create_payments()
                invoices_paid += 1
                payments_created += 1
                print(f"Row {idx}: Paid invoice {inv.name}")
            else:
                # Create regular payment
                payment = env['account.payment'].create({
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': partner.id,
                    'amount': amount,
                    'date': dt_str,
                    'journal_id': journal.id,
                    'memo': f"{vref} | {narration}"[:255] if vref else narration[:255],
                })
                # Using action_post() - we'll follow up with SQL force post if needed
                payment.action_post()
                payments_created += 1
                print(f"Row {idx}: Created regular payment for {part_name}")

        except Exception as e:
            print(f"Row {idx} Error: {e}")

    env.cr.commit()
    print(f"V3 Finished. Created {payments_created} payments. Paid {invoices_paid} invoices.")

if __name__ == "__main__":
    pass

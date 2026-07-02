
import pandas as pd
from datetime import datetime
import odoo
from odoo import api, SUPERUSER_ID

def get_partner(env, name):
    name = name.strip()
    if not name or name.lower() == 'nan': return False
    partner = env['res.partner'].search([('name', '=', name)], limit=1)
    if not partner:
        partner = env['res.partner'].search([('name', 'ilike', name)], limit=1)
    return partner

def get_journal(env, name):
    if not name:
        return env['account.journal'].search([('type', '=', 'bank')], limit=1)
    
    # Try searching by name or code
    j = env['account.journal'].search(['|', ('name', '=', name), ('code', '=', name)], limit=1)
    if not j:
        # Fallback for specific bank names in excel
        if 'HDFC' in name.upper() or '50200024612749' in name:
            j = env['account.journal'].search([('name', 'ilike', '50200024612749')], limit=1)
        elif 'KOTAK' in name.upper() or '3545975369' in name:
            j = env['account.journal'].search([('name', 'ilike', '3545975369')], limit=1)
        elif 'GKP' in name.upper():
            j = env['account.journal'].search([('name', 'ilike', 'Gkp')], limit=1)
        elif 'KARUR' in name.upper():
            j = env['account.journal'].search([('name', 'ilike', 'Karur')], limit=1)
            
    if not j:
        j = env['account.journal'].search(['|', ('name', 'ilike', name), ('code', 'ilike', name)], limit=1)
            
    return j or env['account.journal'].search([('type', '=', 'bank')], limit=1)

def migrate_receipts(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/Final_recipt_register_2025_2026.xlsx'
    df = pd.read_excel(file_path, header=8)
    
    # Filter only Receipt voucher types
    df = df[df['Voucher Type'] == 'Receipt']
    
    print(f"Total Receipt records to process: {len(df)}")
    
    currency_inr = env['res.currency'].search([('name', '=', 'INR')], limit=1)
    if not currency_inr:
        print("INR Currency not found! Falling back to company currency.")
        currency_inr = env.company.currency_id

    dest_cols = [
        'HDFC C/A 50200024612749', 'Kotak -3545975369', 'Gkp Current A/c',
        'BANK CHARGES', 'Imprest - Shantalinga',
        'BG Rail Bhavan -009GT02231400001', 'FD INTEREST',
        'Cholamandalam Investment and Finance Cmpy LTD  Term', 'F D Amount',
        'Suspense', 'THE KARUR VYSYA BANK LIMITED -Unsecured'
    ]

    count = 0
    invoices_linked = 0
    errors = 0
    
    for idx, row in df.iterrows():
        try:
            part_name = str(row['Particulars']).strip() if pd.notna(row['Particulars']) else ''
            if not part_name or part_name.lower() == 'nan' or 'total' in part_name.lower():
                continue
                
            amount = float(row['Gross Total']) if pd.notna(row['Gross Total']) else 0.0
            if amount <= 0:
                continue

            raw_date = row['Date']
            if isinstance(raw_date, (datetime, pd.Timestamp)):
                date_val = raw_date
            else:
                date_val = pd.to_datetime(raw_date)
            
            dt_str = date_val.strftime('%Y-%m-%d')
                
            vref = str(row['Voucher Ref. No.']).strip() if pd.notna(row['Voucher Ref. No.']) else ''
            narration = str(row['Narration']).strip() if pd.notna(row['Narration']) else ''
            
            # Identify the journal
            dest_account_name = None
            for col in dest_cols:
                if col in row and pd.notna(row[col]) and float(row[col] or 0) != 0:
                    dest_account_name = col
                    break
            
            journal = get_journal(env, dest_account_name)
            partner = get_partner(env, part_name)
            if not partner:
                print(f"Partner not found: {part_name}. Creating...")
                partner = env['res.partner'].create({
                    'name': part_name, 
                    'customer_rank': 1,
                    'property_account_receivable_id': env['account.account'].search([('account_type', '=', 'asset_receivable')], limit=1).id
                })
            
            memo = f"{vref} | {narration}" if vref and narration else (vref or narration)
            memo = memo[:255]
            
            # Step 1: Find matching invoice
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
                payment_register = env['account.payment.register'].with_context(ctx).create({
                    'journal_id': journal.id,
                    'amount': amount,
                    'payment_date': dt_str,
                    'communication': memo,
                    'currency_id': currency_inr.id,
                })
                # This creates and posts the payment, and reconciles it
                payment_register._create_payments()
                invoices_linked += 1
                print(f"[{count+1}] Linked to Invoice {inv.name} for {part_name} - Amount: {amount}")
            else:
                # Check for existing standalone payment to avoid duplicates
                existing_payment = env['account.payment'].search([
                    ('partner_id', '=', partner.id),
                    ('amount', '=', amount),
                    ('date', '=', dt_str),
                    ('memo', '=', memo),
                    ('journal_id', '=', journal.id),
                    ('payment_type', '=', 'inbound')
                ], limit=1)
                
                if existing_payment:
                    print(f"[{count+1}] Standalone payment already exists for {part_name} - Amount: {amount}")
                else:
                    # Create standalone payment
                    payment = env['account.payment'].create({
                        'payment_type': 'inbound',
                        'partner_type': 'customer',
                        'partner_id': partner.id,
                        'amount': amount,
                        'date': dt_str,
                        'journal_id': journal.id,
                        'memo': memo,
                        'currency_id': currency_inr.id,
                    })
                    payment.action_post()
                    print(f"[{count+1}] Created standalone payment for {part_name} - Amount: {amount}")

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
    print(f"Invoices linked: {invoices_linked}")
    print(f"Stand-alone payments: {count - invoices_linked}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    migrate_receipts(env)

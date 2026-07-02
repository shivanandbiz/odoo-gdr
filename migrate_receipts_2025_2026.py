
import pandas as pd
from datetime import datetime
import odoo
from odoo import api, SUPERUSER_ID

def get_partner(env, name):
    name = name.strip()
    partner = env['res.partner'].search([('name', '=', name)], limit=1)
    if not partner:
        # Try ilike for slight variations
        partner = env['res.partner'].search([('name', 'ilike', name)], limit=1)
    return partner

def get_journal(env, name):
    if not name:
        return env['account.journal'].search([('type', '=', 'bank')], limit=1)
    
    # Check if name is a code or part of name
    j = env['account.journal'].search(['|', ('name', 'ilike', name), ('code', 'ilike', name)], limit=1)
    if not j:
        # Fallback to HDFC if possible
        if 'HDFC' in name.upper():
            j = env['account.journal'].search([('name', 'ilike', '50200024612749')], limit=1)
        elif 'KOTAK' in name.upper():
            j = env['account.journal'].search([('name', 'ilike', '3545975369')], limit=1)
    
    if not j:
        j = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def migrate(env):
    # Use odoo-bin shell context if possible, otherwise we'd need to initialize
    # Assuming this script is run via: ./odoo-venv/bin/python odoo-bin shell ...
    
    file_path = '/home/biz/GDR_Original_Data/Final Data/Final_recipt_register_2025_2026.xlsx'
    print(f"Reading Excel: {file_path}")
    
    # Header is at row 8 (0-indexed)
    df = pd.read_excel(file_path, skiprows=8)
    
    dest_map = {
        'HDFC C/A 50200024612749': 'HDFC C/A 50200024612749',
        'Kotak -3545975369': 'Kotak -3545975369',
        'Gkp Current A/c': 'Gkp Current A/c',
        'BANK CHARGES': 'BANK CHARGES',
        'Imprest - Shantalinga': 'Imprest - Shantalinga',
        'BG Rail Bhavan -009GT02231400001': 'BG Rail Bhavan -009GT02231400001',
        'FD INTEREST': 'FD INTEREST',
        'Cholamandalam Investment and Finance Cmpy LTD  Term': 'Cholamandalam',
        'F D Amount': 'F D Amount',
        'Suspense': 'Suspense',
        'THE KARUR VYSYA BANK LIMITED -Unsecured': 'Karur Vysya'
    }

    inr_currency = env.ref('base.INR')
    count = 0
    reconciled_count = 0
    errors = 0

    print("Starting migration...")

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
                dt_str = raw_date.strftime('%Y-%m-%d')
            else:
                dt_str = str(raw_date)[:10]

            vref = str(row['Voucher Ref. No.']).strip() if pd.notna(row['Voucher Ref. No.']) else ''
            narration = str(row['Narration']).strip() if pd.notna(row['Narration']) else ''
            
            # Determine which bank account column has a value
            dest_account_name = None
            for col in dest_map.keys():
                if col in row and pd.notna(row[col]) and float(row[col] or 0) != 0:
                    dest_account_name = dest_map[col]
                    break
            
            journal = get_journal(env, dest_account_name)
            partner = get_partner(env, part_name)
            
            if not partner:
                print(f"Creating missing partner: {part_name}")
                partner = env['res.partner'].create({'name': part_name, 'customer_rank': 1})
            
            # Check if this is an internal transfer
            is_transfer = any(part_name.lower() in (v or '').lower() for v in dest_map.values())
            
            if is_transfer:
                # Handle as internal transfer move
                source_journal = get_journal(env, part_name)
                move = env['account.move'].create({
                    'move_type': 'entry',
                    'date': dt_str,
                    'ref': f"REC_MIG/{vref}" if vref else f"REC_MIG/{idx}",
                    'journal_id': source_journal.id,
                    'line_ids': [
                        (0, 0, {
                            'name': narration or "Internal Transfer",
                            'account_id': journal.default_account_id.id,
                            'debit': amount,
                        }),
                        (0, 0, {
                            'name': narration or "Internal Transfer",
                            'account_id': source_journal.default_account_id.id,
                            'credit': amount,
                        }),
                    ]
                })
                move.action_post()
                count += 1
                continue

            # Customer Payment
            dest_acc_id = journal.default_account_id.id
            source_acc_id = partner.property_account_receivable_id.id
            
            # Create account.move for the receipt
            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': vref or f"REC_MIG/{idx}",
                'journal_id': journal.id,
                'line_ids': [
                    (0, 0, {
                        'name': f"Receipt: {part_name} | {narration}",
                        'account_id': dest_acc_id,
                        'debit': amount,
                        'currency_id': inr_currency.id,
                    }),
                    (0, 0, {
                        'name': f"Receipt: {part_name} | {narration}",
                        'account_id': source_acc_id,
                        'partner_id': partner.id,
                        'credit': amount,
                        'currency_id': inr_currency.id,
                    }),
                ]
            })
            move.action_post()
            
            # Create the link to account.payment manually to ensure it shows up in "Payments"
            mline = env['account.payment.method.line'].search([
                ('payment_type', '=', 'inbound'),
                ('journal_id', '=', journal.id)
            ], limit=1)
            mline_id = mline.id if mline else None
            
            memo = f"{vref} | {narration}"[:255] if vref else narration[:255]
            
            env.cr.execute("""
                INSERT INTO account_payment 
                (amount, date, journal_id, partner_id, payment_type, partner_type, state, memo, move_id, company_id, currency_id, payment_method_line_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (amount, dt_str, journal.id, partner.id, 'inbound', 'customer', 'posted', memo, move.id, journal.company_id.id, inr_currency.id, mline_id))
            
            payment_id = env.cr.fetchone()[0]
            env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (payment_id, move.id))
            
            count += 1

            # Reconciliation
            try:
                rec_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                if rec_line:
                    # 1. Try to match by Voucher Ref. No.
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
                    
                    # 2. Fallback to FIFO
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
            print(f"Error on row {idx}: {e}")
            errors += 1

    env.cr.commit()
    print(f"\nMigration Summary:")
    print(f"Total Records Processed: {idx + 1}")
    print(f"Payments Created: {count}")
    print(f"Reconciled with Invoices: {reconciled_count}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    # This is for when run directly, but usually it needs an env
    pass

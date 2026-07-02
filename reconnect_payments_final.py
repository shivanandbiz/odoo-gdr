
import pandas as pd
import odoo
from odoo import api, SUPERUSER_ID

def run_reconciliation(env):
    excel_path = '/home/biz/GDR_Original_Data/Final Data/Final_recipt_register_2025_2026.xlsx'
    print(f"Reading Excel: {excel_path}")
    df = pd.read_excel(excel_path, skiprows=8)
    
    # Filter for Receipt type
    df = df[df['Voucher Type'] == 'Receipt']
    
    reconciled_count = 0
    not_found_count = 0
    already_done_count = 0
    
    print(f"Processing {len(df)} receipts from Excel...")
    
    for idx, row in df.iterrows():
        partner_name = str(row['Particulars']).strip()
        amount = float(row['Gross Total'])
        vref = str(row['Voucher Ref. No.']).strip() if pd.notna(row['Voucher Ref. No.']) else None
        narration = str(row['Narration']).strip() if pd.notna(row['Narration']) else None
        
        if not partner_name or partner_name == 'nan':
            continue
            
        # 1. Find the partner
        partner = env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner:
            # Try fuzzy or lowercase
            partner = env['res.partner'].search([('name', '=ilike', partner_name)], limit=1)
            
        if not partner:
            # print(f"  Row {idx}: Partner '{partner_name}' not found.")
            # not_found_count += 1
            continue

        # 2. Find the payment in Odoo
        # We match by partner and amount and maybe date or memo
        # But for now, let's look for payments with this amount and partner that are not reconciled
        domain = [
            ('partner_id', '=', partner.id),
            ('amount', '=', amount),
            ('payment_type', '=', 'inbound')
        ]
        payments = env['account.payment'].search(domain)
        
        if not payments:
            # Try without exact amount (maybe rounded?)
            # Or check if it's already a move?
            pass
            
        matched_payment = None
        for p in payments:
            # Check if it matches narration or vref in memo
            if (narration and narration in (p.memo or '')) or (vref and vref in (p.memo or '')):
                matched_payment = p
                break
        
        if not matched_payment and len(payments) == 1:
            matched_payment = payments[0]
        elif not matched_payment and len(payments) > 1:
            # If multiple, maybe find the unreconciled one closest in date?
            unreconciled_pays = payments.filtered(lambda p: any(not l.reconciled for l in p.move_id.line_ids if l.account_id.account_type == 'asset_receivable'))
            if len(unreconciled_pays) == 1:
                matched_payment = unreconciled_pays[0]
            else:
                # Still ambiguous, pick first unreconciled
                if unreconciled_pays:
                    matched_payment = unreconciled_pays[0]

        if not matched_payment:
            # Search for moves directly if not found as payment
            continue

        # Check if already reconciled
        rec_line = matched_payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        if not rec_line or all(l.reconciled for l in rec_line):
            already_done_count += 1
            continue

        # 3. Find the invoice to reconcile with
        matched_invoice = None
        if vref:
            matched_invoice = env['account.move'].search([
                ('ref', '=', vref),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid')
            ], limit=1)
            if not matched_invoice:
                # Try partial match or name
                matched_invoice = env['account.move'].search([
                    ('name', '=', vref),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', '!=', 'paid')
                ], limit=1)

        if not matched_invoice and narration:
            matched_invoice = env['account.move'].search([
                ('ref', '=', narration),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid')
            ], limit=1)

        if not matched_invoice:
            # Try to match invoice by partner and amount?
            # Or just find any open invoice for this partner that matches the amount
            matched_invoice = env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('amount_total', '=', amount),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid')
            ], limit=1)

        if not matched_invoice:
            # Last resort: oldest open invoice for this partner
            matched_invoice = env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'not in', ['paid', 'in_payment'])
            ], order='invoice_date asc, id asc', limit=1)

        if matched_invoice:
            try:
                # Reconcile them
                inv_line = matched_invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
                if inv_line and rec_line:
                    (rec_line | inv_line).reconcile()
                    # print(f"  ✓ Reconciled Payment {matched_payment.name} with Invoice {matched_invoice.name} for {partner_name}")
                    reconciled_count += 1
                else:
                    pass
            except Exception as e:
                print(f"  ✗ Failed to reconcile Row {idx}: {e}")
        else:
            # print(f"  ? No matching invoice found for Row {idx} ({partner_name}, {amount})")
            not_found_count += 1

    print(f"\nSummary:")
    print(f"Total Reconciled: {reconciled_count}")
    print(f"Already Reconciled: {already_done_count}")
    print(f"Invoices Not Found: {not_found_count}")

if __name__ == "__main__":
    # This will be run via odoo shell
    run_reconciliation(env)

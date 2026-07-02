
# Audit Customer Payments
# Run with: python3 odoo-bin shell -c odoo.conf --no-http --stop-after-init < audit_customer_payments_shell.py

import pandas as pd
from datetime import datetime

def audit_payments():
    print("--- CUSTOMER PAYMENTS AUDIT ---")
    
    # 1. Total Payments in Odoo (account.payment)
    payments = env['account.payment'].search([('payment_type', '=', 'inbound')])
    print(f"Total account.payment (inbound): {len(payments)}")
    
    # 2. Total Receipts by Migration Reference (REC/%)
    receipt_moves = env['account.move'].search([('ref', 'like', 'REC/%')])
    print(f"Total account.move (ref like REC/%): {len(receipt_moves)}")
    print(f"Total value of REC/% moves: {sum(receipt_moves.mapped('amount_total')):,.2f}")

    # 3. Total Receipts by Migration Reference (PAY_GDR/%) - just in case
    gdr_moves = env['account.move'].search([('ref', 'like', 'PAY_GDR/%')])
    print(f"Total account.move (ref like PAY_GDR/%): {len(gdr_moves)}")

    # 4. Check against Excel Source if possible
    fname = '/home/biz/odoo/new_receipt_register.xlsx'
    try:
        df = pd.read_excel(fname, header=None)
        # Assuming data starts from row 11 (index 10) as in migrate_receipts_final.py
        data_rows = df.iloc[10:]
        source_count = 0
        source_total = 0.0
        for idx, row in data_rows.iterrows():
            r = row.tolist()
            if not any(pd.notna(x) for x in r): continue
            part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
            if not part_name or 'Total' in part_name or part_name == 'nan': continue
            try: amount = float(r[5] or 0)
            except: amount = 0.0
            if amount > 0:
                source_count += 1
                source_total += amount
        
        print(f"\nExcel Source ({fname}):")
        print(f"  Count: {source_count}")
        print(f"  Total Amount: {source_total:,.2f}")
        
        print(f"\nComparison:")
        print(f"  Count Diff: {len(receipt_moves) - source_count}")
        print(f"  Amount Diff: {sum(receipt_moves.mapped('amount_total')) - source_total:,.2f}")
        
    except Exception as e:
        print(f"\nCould not read excel source: {e}")

    # 5. List some recent receipts
    print("\nRecent 5 Migration Receipts (REC/%):")
    for m in receipt_moves[:5]:
        print(f"  - {m.date} | {m.ref} | {m.partner_id.name} | {m.amount_total:,.2f} | {m.state}")

audit_payments()

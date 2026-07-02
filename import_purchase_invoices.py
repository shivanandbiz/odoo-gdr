"""
Import purchase invoices from all_tally_to_odoo_migratation.xlsx
Grouping rows by Supplier Invoice No. to handle multi-line invoices.

Run via:
  /home/biz/odoo/odoo-venv/bin/python3 /home/biz/odoo/odoo-bin shell \
      --config /home/biz/odoo/odoo.conf \
      --no-http \
      -d Odoo < /home/biz/odoo/import_purchase_invoices.py 2>&1 | tee /home/biz/odoo/import_purchase_invoices_v4.log
"""

import pandas as pd
import math
from datetime import datetime

# ── Load Excel ────────────────────────────────────────────────────────────────
file_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
sheet_name = 'Purchase Register'
df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl', header=8)

# Remove rows without Date or Particulars
df = df[df['Date'].notna() & df['Particulars'].notna()].copy().reset_index(drop=True)
print(f"Total purchase register rows: {len(df)}")

# Columns for breakdown
taxable_cols = [
    'LOCAL PURCHASE GST 18%', 'Interstate Purchases Gst @28%', 'INTERSTATE PURCHASE @18%',
    'Local Purchases Gst @5%', 'GST PURCHASE @12%', 'Local Purchase Gst @5%', 'LOCAL PURCHASE GST @28 %'
]
tax_cols = [
    'SGST@ 9%', 'CGST @ 9%', 'IGST@ 28', 'IGST@18', 'Cgst@2.5%', 'Sgst@2.5%',
    'SGST@6%', 'CGST@6%', 'CGST@14%', 'SGST@14%'
]
other_cols = ['Rounded Off', 'Discount Received']

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean(val):
    if val is None:
        return 0.0
    try:
        f = float(val)
        return f if not math.isnan(f) else 0.0
    except (TypeError, ValueError):
        return 0.0

# ── Caches ───────────────────────────────────────────────────────────────────
partner_cache = {}

def get_partner(name):
    if not name:
        return None
    if name not in partner_cache:
        partner = env['res.partner'].search([('name', '=', name)], limit=1)
        if not partner:
            partner = env['res.partner'].search([('name', 'ilike', name)], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': name, 'is_company': True, 'supplier_rank': 1})
            print(f"  [CREATE] Partner '{name}' created.")
        partner_cache[name] = partner
    return partner_cache[name]

generic_expense = env['account.account'].search([('account_type', '=', 'expense')], limit=1)

# ── Grouping ──────────────────────────────────────────────────────────────────
# Group by Date, Particulars and Supplier Invoice No.
# If Supplier Invoice No is missing, we use a counter
df['InvoiceKey'] = df['Supplier Invoice No.'].fillna('MISSING_' + pd.Series(df.index.astype(str)))
grouped = df.groupby(['Date', 'Particulars', 'InvoiceKey'])

print(f"Total distinct invoices to import: {len(grouped)}")

created = 0
errors = 0
BATCH = 20

for (date, particulars, inv_key), group in grouped:
    try:
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()
        
        vendor_name = str(particulars).strip()
        ref = str(inv_key).strip() if not str(inv_key).startswith('MISSING_') else False
        
        partner = get_partner(vendor_name)
        if not partner:
            continue

        invoice_line_ids = []
        
        # Combine all lines in the group
        for idx, row in group.iterrows():
            # Breakdown lines
            for col in taxable_cols + tax_cols + other_cols:
                val = clean(row.get(col))
                if val != 0:
                    invoice_line_ids.append((0, 0, {
                        'name': col,
                        'quantity': 1.0,
                        'price_unit': val,
                        'account_id': generic_expense.id,
                    }))

            if not invoice_line_ids:
                gross = clean(row.get('Gross Total'))
                if gross != 0:
                   invoice_line_ids.append((0, 0, {
                        'name': "Total (Migration)",
                        'quantity': 1.0,
                        'price_unit': gross,
                        'account_id': generic_expense.id,
                    }))

        if not invoice_line_ids:
            continue

        vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': date,
            'name': ref if ref else False,
            'ref': ref,
            'invoice_line_ids': invoice_line_ids,
        }

        # Check if already exists (Odoo handles duplicate names usually, but good to check)
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('partner_id', '=', partner.id),
            ('invoice_date', '=', date)
        ]
        if ref:
            domain.append(('name', '=', ref))
        
        existing = env['account.move'].search(domain, limit=1)
        if existing:
            continue

        move = env['account.move'].create(vals)
        try:
            move.action_post()
        except Exception as post_e:
            print(f"  [WARNING] Could not post invoice {inv_key}: {post_e}")
        created += 1

        if created % BATCH == 0:
            env.cr.commit()
            print(f"  Progress: {created} created, {errors} errors ...")

    except Exception as e:
        print(f"  [ERROR] {inv_key} ({particulars}): {e}")
        env.cr.rollback()
        errors += 1

# Final commit
env.cr.commit()
print(f"\n=== Grouped Purchase Invoice Import Complete ===")
print(f"  Created : {created}")
print(f"  Errors  : {errors}")

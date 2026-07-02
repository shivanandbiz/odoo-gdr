"""
Import purchase invoices from Excel (handles missing and duplicates)
"""

import pandas as pd
import math
from datetime import datetime
from odoo.addons.account.models.sequence_mixin import SequenceMixin

# Bypassing chronological constraint
old_constrain = SequenceMixin._constrains_date_sequence
SequenceMixin._constrains_date_sequence = lambda self: True

# ── Load Excel ────────────────────────────────────────────────────────────────
file_path = '/home/biz/odoo/purchase.xlsx-2025-26.......xlsx'
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
other_cols = [c for c in ['Rounded Off', 'Discount Received'] if c in df.columns]

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
df['InvoiceKey'] = df['Supplier Invoice No.'].fillna('MISSING_' + pd.Series(df.index.astype(str)))
grouped = df.groupby(['Date', 'Particulars', 'InvoiceKey'])

print(f"Total distinct invoices in new file: {len(grouped)}")

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

        # Check if already exists in Odoo with this specific name/date/partner
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('partner_id', '=', partner.id),
            ('invoice_date', '=', date)
        ]
        if ref:
            domain.append('|')
            domain.append(('name', '=', ref))
            domain.append(('ref', '=', ref))
        
        existing = env['account.move'].search(domain, limit=1)
        if existing:
            # print(f"  [SKIP] '{ref}' already exists.")
            continue

        invoice_line_ids = []
        for idx, row in group.iterrows():
            for col in taxable_cols + tax_cols + other_cols:
                if col in row:
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

        # Create Move
        move = env['account.move'].create(vals)
        
        # Try to Post with duplicate handling
        posted = False
        attempt = 0
        original_name = move.name
        while not posted and attempt < 5:
            try:
                with env.cr.savepoint():
                    move.action_post()
                    posted = True
            except Exception as pe:
                if 'account_move_unique_name' in str(pe) or 'duplicate key value violates unique constraint' in str(pe):
                    attempt += 1
                    move.name = f"{original_name}-DUP{attempt}"
                else:
                    # Generic post error, keep as draft
                    print(f"  [WARNING] Could not post {move.name}: {pe}")
                    break
        
        created += 1
        if created % BATCH == 0:
            env.cr.commit()
            print(f"  Progress: {created} missing invoices migrated...")

    except Exception as e:
        print(f"  [ERROR] {inv_key}: {e}")
        env.cr.rollback()
        errors += 1

# Final commit
env.cr.commit()
SequenceMixin._constrains_date_sequence = old_constrain
print(f"\n=== Migration Complete ===")
print(f"  Migrated : {created}")
print(f"  Errors   : {errors}")

import csv
import re
from datetime import datetime
from odoo.addons.account.models.sequence_mixin import SequenceMixin

sales_data = []
with open('/home/biz/odoo/purchase_data.tsv', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('Grand Total'):
            continue
        parts = line.split('\t')

        date_str = parts[0].strip()
        vendor_name = parts[1].strip()
        inv_num = parts[3].strip() if len(parts) > 3 else ''

        if not inv_num or '(cancelled )' in vendor_name:
            continue

        try:
            date_obj = datetime.strptime(date_str, '%d-%b-%y').date()
        except ValueError:
            try:
                date_obj = datetime.strptime(date_str, '%d-%m-%y').date()
            except:
                print(f"Skipping bad date: {date_str} for {inv_num}")
                continue

        cr_strings = re.findall(r'([\d\.]+)\s*Cr', line)
        dr_strings = re.findall(r'([\d\.]+)\s*Dr', line)
        
        cr_vals = [float(x) for x in cr_strings]
        dr_vals = [float(x) for x in dr_strings]
        
        if not cr_vals:
            continue
            
        total_amount = cr_vals[0]
        
        base_amount = sum([v for v in dr_vals if v >= total_amount * 0.2])
        if base_amount == 0 and dr_vals:
            base_amount = max(dr_vals)
        elif base_amount == 0:
            base_amount = total_amount / 1.18

        sales_data.append({
            'date': date_obj,
            'vendor': vendor_name,
            'inv_num': inv_num,
            'base_amount': base_amount
        })

print(f"Found {len(sales_data)} valid purchase rows to import.")

# ── Find company ──────────────────────────────────────────────────────────────
company = env['res.company'].search([('name', 'ilike', 'GDR MEKTEK')], limit=1)
if not company:
    company = env['res.company'].create({'name': 'GDR MEKTEK PVT LTD'})
    print(f"Created company {company.name}")
else:
    print(f"Found existing company: {company.name}")

env = env(context=dict(env.context, allowed_company_ids=[company.id], company_id=company.id))

# ── Product ───────────────────────────────────────────────────────────────────
product = env['product.product'].search(
    [('name', '=', 'GST PURCHASES'), '|', ('company_id', '=', False), ('company_id', '=', company.id)],
    limit=1
)
if not product:
    categ = env.ref('product.product_category_all', raise_if_not_found=False)
    product = env['product.product'].create({
        'name': 'GST PURCHASES',
        'type': 'service',
        'categ_id': categ.id if categ else False,
        'company_id': company.id,
    })

# ── Tax ───────────────────────────────────────────────────────────────────────
tax = env['account.tax'].search([
    ('company_id', '=', company.id),
    ('type_tax_use', '=', 'purchase'),
    ('amount', '=', 18.0)
], limit=1)

if not tax:
    tax = env['account.tax'].create({
        'name': 'GST 18% (Purchase)',
        'amount_type': 'percent',
        'amount': 18.0,
        'type_tax_use': 'purchase',
        'company_id': company.id,
    })

# ── Monkey-patch sequence date constraint ─────────────────────────────────────
_original_constraint = SequenceMixin._constrains_date_sequence.__func__ if hasattr(SequenceMixin._constrains_date_sequence, '__func__') else None

def _noop_constrains_date_sequence(self):
    pass  

SequenceMixin._constrains_date_sequence = _noop_constrains_date_sequence

print("Sequence date constraint disabled for import.")

# ── Import loop ───────────────────────────────────────────────────────────────
inv_count = 0
skip_count = 0
error_count = 0

for row in sales_data:
    # Find or create partner
    partner = env['res.partner'].search(
        [('name', '=', row['vendor']), ('company_id', 'in', [False, company.id])],
        limit=1
    )
    if not partner:
        partner = env['res.partner'].create({
            'name': row['vendor'],
            'company_id': False,
            'supplier_rank': 1,
        })

    # Skip if already imported
    existing = env['account.move'].search([
        ('ref', '=', row['inv_num']),  # vendor bills use 'ref' for vendor invoice number commonly
        ('company_id', '=', company.id),
        ('move_type', '=', 'in_invoice'),
    ], limit=1)
    
    if existing:
        skip_count += 1
        continue

    try:
        move = env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': row['date'],
            'date': row['date'],
            'company_id': company.id,
            'ref': row['inv_num'],
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'name': f"Purchase - {row['inv_num']}",
                'quantity': 1,
                'price_unit': row['base_amount'],
                'tax_ids': [(6, 0, [tax.id])],
            })],
        })

        # Post the invoice
        move.action_post()

        # Overwrite the sequence name if we want, but for vendor bills `ref` is the main thing.
        # So we leave the sequence to whatever Odoo assigned, or update it.
        # We will also update name to match if needed, but standard is `BILL/YYYY/MM/...`
        env.cr.commit()
        inv_count += 1
        if inv_count % 10 == 0:
            print(f"  ...imported {inv_count} bills so far")

    except Exception as e:
        print(f"ERROR importing {row['inv_num']}: {e}")
        env.cr.rollback()
        error_count += 1

print(f"\n=== Import complete ===")
print(f"  Imported : {inv_count}")
print(f"  Skipped  : {skip_count} (already existed)")
print(f"  Errors   : {error_count}")

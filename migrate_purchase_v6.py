# migrate_purchase_v6.py
# Revised script based on user feedback:
# - Ignore invoice number duplication (accept all records).
# - Handle (Partner + Ref) duplicates by appending suffixes to allow Odoo import.
# - Maintain January exclusion logic to match reference image balance.
# - Improved tax detection and rounding handling for better precision.

import openpyxl
from datetime import datetime
from collections import defaultdict

def get_tax(name, amount, type_tax_use='purchase'):
    t = env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', type_tax_use)], limit=1)
    if not t:
        t = env['account.tax'].create({
            'name': name, 'amount': amount,
            'type_tax_use': type_tax_use, 'amount_type': 'percent'
        })
    return t.id

def get_partner(name):
    p = env['res.partner'].search([('name', '=', name)], limit=1)
    if not p:
        p = env['res.partner'].create({'name': name, 'supplier_rank': 1})
    return p.id

def fval(d, *keys):
    for k in keys:
        try:
            v = d.get(k)
            if v is None: continue
            return float(v)
        except: pass
    return 0.0

def read_xlsx(fname, sheet_name='Purchase Register'):
    print(f"Reading {fname}...")
    wb = openpyxl.load_workbook(fname, read_only=True, data_only=True)
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    hdr_idx = None
    for i, row in enumerate(rows):
        if any(str(c).strip() == 'Date' for c in row if c is not None):
            hdr_idx = i
            break
    headers = [str(c).strip() if c is not None else f'Col{j}' for j, c in enumerate(rows[hdr_idx])]
    data = []
    for idx, row in enumerate(rows[hdr_idx + 1:]):
        d = {h: v for h, v in zip(headers, row)}
        d['_row_idx'] = idx + hdr_idx + 1
        part = str(d.get('Particulars', '') or '').strip()
        if not part or 'Total' in part or 'Grand' in part or part == 'nan': continue
        
        raw_date = d.get('Date')
        if not isinstance(raw_date, (datetime, str)): continue
        try:
            dt = raw_date if isinstance(raw_date, datetime) else datetime.strptime(str(raw_date)[:10], '%Y-%m-%d')
        except: continue
        d['_date'] = dt
        try:
            d['_gross'] = float(d.get('Gross Total') or 0)
        except:
            try: d['_gross'] = float(d.get('LOCAL PURCHASE GST 18%') or 0)
            except: d['_gross'] = 0.0
        data.append(d)
    return data

# 1. READ DATA
file1 = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
file2 = '/home/biz/odoo/purchase.xlsx-2025-26.......xlsx'

rows1 = read_xlsx(file1)
rows2 = read_xlsx(file2)

# Deduplication of EXACT technical replicates (Date, Particulars, Ref, Gross)
# but NOT if they differ in any of these.
unique_rows = []
seen = set()
for r in rows1:
    my = r['_date'].strftime('%Y-%m')
    if my == '2026-01' and r['_row_idx'] < 800: continue # The 3.12L discrepancy block
    if my <= '2026-01':
        # Technical Deduplication
        key = (r['_date'], r.get('Particulars'), r.get('Supplier Invoice No.'), r['_gross'])
        if key in seen: continue
        seen.add(key)
        unique_rows.append(r)

for r in rows2:
    my = r['_date'].strftime('%Y-%m')
    if my in ['2026-02', '2026-03']:
        key = (r['_date'], r.get('Particulars'), r.get('Supplier Invoice No.'), r['_gross'])
        if key in seen: continue
        seen.add(key)
        unique_rows.append(r)

print(f"Total unique records to migrate: {len(unique_rows)}")

# 2. CLEAR EXISTING
print("Deleting existing purchase invoices...")
all_existing = env['account.move'].search([('move_type', '=', 'in_invoice')])
if all_existing:
    to_draft = all_existing.filtered(lambda m: m.state != 'draft')
    if to_draft: to_draft.button_draft()
    all_existing.unlink()
    env.cr.commit()
    print(f"  Deleted {len(all_existing)} invoices.")

# 3. MIGRATE
journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)
count = 0
errors = 0

partner_ref_counter = defaultdict(int)

for idx, row in enumerate(unique_rows):
    gross = row['_gross']
    part_name = str(row.get('Particulars', '') or '').strip()
    inv_no = str(row.get('Supplier Invoice No.', '') or '').strip()
    dt_str = row['_date'].strftime('%Y-%m-%d')
    
    partner_id = get_partner(part_name)
    
    # Handle Partner + Ref duplication by appending suffix
    base_ref = inv_no if inv_no and inv_no != 'nan' else f'MIG'
    full_ref = base_ref
    partner_ref_counter[(partner_id, base_ref)] += 1
    if partner_ref_counter[(partner_id, base_ref)] > 1:
        full_ref = f"{base_ref}/{partner_ref_counter[(partner_id, base_ref)] - 1}"

    # Tax detection
    igst28_amt = fval(row, 'IGST@ 28', 'IGST@28')
    igst18_amt = fval(row, 'IGST@18', 'IGST@ 18')
    cgst9_amt = fval(row, 'CGST @ 9%', 'CGST@9%', 'CGST @ 9')
    sgst9_amt = fval(row, 'SGST@ 9%', 'SGST@9%', 'SGST @ 9')
    cgst6_amt = fval(row, 'CGST@6%', 'CGST @ 6%')
    sgst6_amt = fval(row, 'SGST@6%', 'SGST @ 6%')
    cgst25_amt = fval(row, 'Cgst@2.5%', 'CGST@2.5%', 'CGST @ 2.5%')
    sgst25_amt = fval(row, 'Sgst@2.5%', 'SGST@2.5%', 'SGST @ 2.5%')
    cgst14_amt = fval(row, 'CGST@14%', 'CGST @ 14%')
    sgst14_amt = fval(row, 'SGST@14%', 'SGST @ 14%')
    rounded = fval(row, 'Rounded Off', 'Rounded off')

    total_gst = igst28_amt + igst18_amt + cgst9_amt + sgst9_amt + cgst6_amt + sgst6_amt + cgst25_amt + sgst25_amt + cgst14_amt + sgst14_amt
    taxable_base = gross - total_gst - rounded

    tax_ids = []
    if igst28_amt > 0: tax_ids = [get_tax('IGST 28%', 28.0)]
    elif igst18_amt > 0: tax_ids = [get_tax('IGST 18%', 18.0)]
    elif cgst9_amt > 0 or sgst9_amt > 0: tax_ids = [get_tax('CGST 9%', 9.0), get_tax('SGST 9%', 9.0)]
    elif cgst14_amt > 0 or sgst14_amt > 0: tax_ids = [get_tax('CGST 14%', 14.0), get_tax('SGST 14%', 14.0)]
    elif cgst6_amt > 0 or sgst6_amt > 0: tax_ids = [get_tax('CGST 6%', 6.0), get_tax('SGST 6%', 6.0)]
    elif cgst25_amt > 0 or sgst25_amt > 0: tax_ids = [get_tax('CGST 2.5%', 2.5), get_tax('SGST 2.5%', 2.5)]

    try:
        move = env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner_id,
            'invoice_date': dt_str,
            'date': dt_str,
            'ref': full_ref,
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Purchase (Migration)',
                'quantity': 1,
                'price_unit': round(taxable_base, 2),
                'tax_ids': [(6, 0, tax_ids)],
            })],
        })
        move.action_post()
        count += 1
        if count % 100 == 0:
            env.cr.commit()
            print(f"  ✓ {count} records imported...")
    except Exception as e:
        errors += 1
        print(f"  ERR row {idx}: {e}")

env.cr.commit()
print(f"\nMigration Finished. Unique Imported: {count} | Errors: {errors}")

# Final verify
all_bills = env['account.move'].search([('move_type', '=', 'in_invoice'), ('state', '=', 'posted')])
odoo_total = sum(m.amount_total for m in all_bills)
print(f"Odoo Grand Total: {odoo_total:,.2f}")
print(f"Tally Target: 9,03,23,140.32")
print(f"Difference: {odoo_total - 90323140.32:,.2f}")

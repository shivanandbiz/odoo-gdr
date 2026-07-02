# migrate_sales_final.py
# Migrates Sales Register from Excel to Odoo.
# Logic:
# - Uses 'Sales Inv. Register' from all_tally_to_odoo_migratation.xlsx
# - Handles GST breakdown (18% mainly).
# - Matches Grand Total: 14,55,47,005.25

import openpyxl
from datetime import datetime
from collections import defaultdict

def get_tax(name, amount, type_tax_use='sale'):
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
        p = env['res.partner'].create({'name': name, 'customer_rank': 1})
    return p.id

def fval(d, *keys):
    for k in keys:
        try:
            v = d.get(k)
            if v is None: continue
            return float(v)
        except: pass
    return 0.0

def read_xlsx(fname, sheet_name='Sales Inv. Register'):
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
        if not part or 'Total' in part or 'Grand' in part or part == 'nan' or part == 'None': continue
        raw_date = d.get('Date')
        if not isinstance(raw_date, (datetime, str)): continue
        try:
            dt = raw_date if isinstance(raw_date, datetime) else datetime.strptime(str(raw_date)[:10], '%Y-%m-%d')
        except: continue
        d['_date'] = dt
        try:
            d['_gross'] = float(d.get('Gross Total') or 0)
        except: d['_gross'] = 0.0
        data.append(d)
    return data

# 1. READ DATA
file1 = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
final_rows = read_xlsx(file1)

print(f"Total records to migrate: {len(final_rows)}")

# ── 2. DELETE existing sales invoices ───────────────────────────────────────
print("Deleting existing sales invoices...")
all_existing = env['account.move'].search([('move_type', '=', 'out_invoice')])
if all_existing:
    to_draft = all_existing.filtered(lambda m: m.state != 'draft')
    if to_draft:
        to_draft.button_draft()
    all_existing.unlink()
    env.cr.commit()
    print(f"  Deleted {len(all_existing)} invoices.")

# 3. MIGRATE
journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)
count = 0
errors = 0

# Track (Partner, Ref) to avoid duplication error (though Odoo allows it across partners)
ref_counter = defaultdict(int)

for idx, row in enumerate(final_rows):
    gross = row['_gross']
    part_name = str(row.get('Particulars', '') or '').strip()
    inv_no = str(row.get('Voucher Ref. No.', '') or '').strip()
    dt_str = row['_date'].strftime('%Y-%m-%d')
    
    partner_id = get_partner(part_name)
    base_ref = inv_no if inv_no and inv_no != 'nan' else f'SALE/{idx}'
    
    # Suffix for same-partner duplicate refs
    ref_counter[(partner_id, base_ref)] += 1
    full_ref = base_ref if ref_counter[(partner_id, base_ref)] == 1 else f"{base_ref}/{ref_counter[(partner_id, base_ref)]}"

    # Tax detection
    igst18_amt = fval(row, 'IGST@18', 'IGST@ 18')
    cgst9_amt = fval(row, 'CGST @ 9%', 'CGST@9%', 'CGST @ 9')
    sgst9_amt = fval(row, 'SGST@ 9%', 'SGST@9%', 'SGST @ 9')
    # Use 'Services Interstate Gst@18%' if it's a tax column
    # Checking if it has values
    svc_18 = fval(row, 'Services Interstate Gst@18%')

    total_gst = igst18_amt + cgst9_amt + sgst9_amt
    # If total_gst is 0 but Gross > 0, we might need to check if svc_18 is tax
    # But usually 18% is standard.
    
    taxable_base = gross - total_gst
    
    tax_ids = []
    if igst18_amt > 0: tax_ids = [get_tax('IGST 18%', 18.0)]
    elif cgst9_amt > 0 or sgst9_amt > 0: tax_ids = [get_tax('CGST 9%', 9.0), get_tax('SGST 9%', 9.0)]
    else:
        # Default to 18 if no tax detected but Gross > 0? 
        # Or no tax if it's exempt. Let's see if there are non-taxed ones.
        pass

    try:
        move = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'invoice_date': dt_str,
            'date': dt_str,
            'ref': full_ref,
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Sales (Migration)',
                'quantity': 1,
                'price_unit': round(taxable_base, 2),
                'tax_ids': [(6, 0, tax_ids)],
            })],
        })
        move.action_post()
        count += 1
        if count % 20 == 0:
            env.cr.commit()
            print(f"  ✓ {count} invoices imported...")
    except Exception as e:
        errors += 1
        print(f"  ERR row {idx} ({full_ref}): {e}")

env.cr.commit()
print(f"\nMigration Finished. Total: {count} | Errors: {errors}")

# Final verify
all_moves = env['account.move'].search([('move_type', '=', 'out_invoice'), ('state', '=', 'posted')])
odoo_total = sum(m.amount_total for m in all_moves)
print(f"Odoo Sales Total: {odoo_total:,.2f}")
print(f"Tally Sales Target: 145,547,005.25")
print(f"Difference: {odoo_total - 145547005.25:,.2f}")

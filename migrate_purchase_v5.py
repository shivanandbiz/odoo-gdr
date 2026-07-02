# migrate_purchase_v5.py
# FIX: Use actual taxable value (Gross Total minus GST amounts) as price_unit
# so that Odoo total = Tally Gross Total (no double taxation)
from openpyxl.worksheet.filters import FilterColumn, CustomFilter
def _patch_fc(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId, self.hidden, self.customFilters, self.method, self.val = colId, hidden, customFilters, method, val
FilterColumn.__init__ = _patch_fc
def _patch_cf(self, operator=None, val=None, **kwargs):
    self.operator = operator
    self.__dict__['val'] = val
CustomFilter.__init__ = _patch_cf

import openpyxl
from datetime import datetime
from collections import defaultdict

# ── Helpers ─────────────────────────────────────────────────────────────────

def read_purchase(fname):
    """Read purchase register sheet, return list of dicts."""
    wb = openpyxl.load_workbook(fname, read_only=True, data_only=True)
    ws = wb['Purchase Register']
    rows = list(ws.iter_rows(values_only=True))
    # Find header row (contains 'Date')
    hdr_idx = None
    for i, row in enumerate(rows):
        if any(str(c).strip() == 'Date' for c in row if c is not None):
            hdr_idx = i
            break
    if hdr_idx is None:
        print(f"  WARNING: no header in {fname}")
        return []
    headers = [str(c).strip() if c is not None else f'_Col{j}' for j, c in enumerate(rows[hdr_idx])]
    result = []
    for row in rows[hdr_idx + 1:]:
        d = {h: v for h, v in zip(headers, row)}
        # Skip totals/empty
        part = str(d.get('Particulars', '') or '').strip()
        if not part or 'Total' in part or 'Grand' in part or part == 'nan':
            continue
        raw_date = d.get('Date')
        if raw_date is None:
            continue
        try:
            if isinstance(raw_date, datetime):
                dt = raw_date
            else:
                dt = datetime.strptime(str(raw_date).strip(), '%Y-%m-%d')
        except Exception:
            continue
        d['_date'] = dt
        result.append(d)
    return result

def fval(d, *keys):
    """Return float value of first matching key that has a positive value."""
    for k in keys:
        try:
            v = float(d.get(k) or 0)
            if v > 0:
                return v
        except (ValueError, TypeError):
            pass
    return 0.0

def get_tax(name, amount):
    t = env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'purchase')], limit=1)
    if not t:
        t = env['account.tax'].create({'name': name, 'amount': amount,
                                       'type_tax_use': 'purchase', 'amount_type': 'percent'})
    return t.id

def get_partner(name):
    p = env['res.partner'].search([('name', '=', name)], limit=1)
    if not p:
        p = env['res.partner'].create({'name': name, 'supplier_rank': 1})
    return p.id

# ── 1. DELETE existing purchase invoices ────────────────────────────────────
print("Deleting existing purchase invoices...")
existing = env['account.move'].search([('move_type', '=', 'in_invoice')])
if existing:
    existing.button_draft()
    existing.unlink()
    env.cr.commit()
    print(f"  Deleted {len(existing)} invoices.")

# ── 2. READ SOURCE DATA ──────────────────────────────────────────────────────
rows1 = read_purchase('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx')
rows2 = read_purchase('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx')

# File1: Apr-Dec 2025 + Jan 2026; File2: Feb-Mar 2026
all_rows = []
for r in rows1:
    dt = r['_date']
    if (dt.year == 2025) or (dt.year == 2026 and dt.month == 1):
        all_rows.append(r)
for r in rows2:
    dt = r['_date']
    if dt.year == 2026 and dt.month in (2, 3):
        all_rows.append(r)

print(f"Total records to migrate: {len(all_rows)}")

# ── 3. JOURNAL ───────────────────────────────────────────────────────────────
journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)

# ── 4. MIGRATE ───────────────────────────────────────────────────────────────
count = 0
errors = 0

for idx, row in enumerate(all_rows):
    gross_total = fval(row, 'Gross Total')
    part_name   = str(row.get('Particulars', '') or '').strip()
    inv_no      = str(row.get('Supplier Invoice No.', '') or '').strip()
    dt_str      = row['_date'].strftime('%Y-%m-%d')

    if gross_total == 0 and not inv_no:
        continue

    # ── Detect GST breakdown ────────────────────────────────────────────────
    igst28  = fval(row, 'IGST@ 28', 'IGST@28')
    igst18  = fval(row, 'IGST@18', 'IGST@ 18')
    cgst9   = fval(row, 'CGST @ 9%', 'CGST@9%', 'CGST @ 9')
    sgst9   = fval(row, 'SGST@ 9%', 'SGST@9%', 'SGST @ 9')
    cgst6   = fval(row, 'CGST@6%', 'CGST @ 6%')
    sgst6   = fval(row, 'SGST@6%', 'SGST @ 6%')
    cgst25  = fval(row, 'Cgst@2.5%', 'CGST@2.5%', 'CGST @ 2.5%')
    sgst25  = fval(row, 'Sgst@2.5%', 'SGST@2.5%', 'SGST @ 2.5%')
    cgst14  = fval(row, 'CGST@14%', 'CGST @ 14%')
    sgst14  = fval(row, 'SGST@14%', 'SGST @ 14%')
    rounded = fval(row, 'Rounded Off', 'Rounded off')

    # Total GST paid (as shown in Tally columns)
    total_gst = igst28 + igst18 + cgst9 + sgst9 + cgst6 + sgst6 + cgst25 + sgst25 + cgst14 + sgst14

    # Taxable amount = Gross Total - GST amounts - rounding
    taxable_base = gross_total - total_gst - rounded

    # Determine which tax to apply
    if igst28 > 0:
        tax_ids = [(6, 0, [get_tax('IGST 28%', 28.0)])]
    elif igst18 > 0:
        tax_ids = [(6, 0, [get_tax('IGST 18%', 18.0)])]
    elif cgst9 > 0 and sgst9 > 0:
        tax_ids = [(6, 0, [get_tax('CGST 9%', 9.0), get_tax('SGST 9%', 9.0)])]
    elif cgst6 > 0 and sgst6 > 0:
        tax_ids = [(6, 0, [get_tax('CGST 6%', 6.0), get_tax('SGST 6%', 6.0)])]
    elif cgst25 > 0 and sgst25 > 0:
        tax_ids = [(6, 0, [get_tax('CGST 2.5%', 2.5), get_tax('SGST 2.5%', 2.5)])]
    elif cgst14 > 0 and sgst14 > 0:
        tax_ids = [(6, 0, [get_tax('CGST 14%', 14.0), get_tax('SGST 14%', 14.0)])]
    else:
        # No GST columns have values — use Gross Total as-is (no tax)
        taxable_base = gross_total
        tax_ids = [(6, 0, [])]

    ref = inv_no if inv_no and inv_no != 'nan' else f'INV/MIG/{idx}'

    try:
        move = env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': get_partner(part_name),
            'invoice_date': dt_str,
            'date': dt_str,
            'ref': ref,
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Purchase (Migration)',
                'quantity': 1,
                'price_unit': round(taxable_base, 2),
                'tax_ids': tax_ids,
            })],
        })
        move.action_post()
        count += 1
        if count % 50 == 0:
            env.cr.commit()
            print(f"  ✓ {count} invoices committed...")
    except Exception as e:
        errors += 1
        print(f"  ERR row {idx} ({part_name} {ref}): {e}")

env.cr.commit()
print(f"\nMigration done. Imported: {count} | Errors: {errors}")

# ── 5. VERIFICATION ──────────────────────────────────────────────────────────
all_bills = env['account.move'].search([('move_type', '=', 'in_invoice'), ('state', '=', 'posted')])
odoo_total = sum(m.amount_total for m in all_bills)
print(f"\nOdoo Purchase Total (amount_total): {odoo_total:,.2f}")
print(f"Tally Reference Total:              91,930,034.81")
print(f"Difference:                         {odoo_total - 91930034.81:,.2f}")

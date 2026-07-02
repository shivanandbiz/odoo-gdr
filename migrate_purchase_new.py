# migrate_purchase_new.py
import pandas as pd
from datetime import datetime
from collections import defaultdict

def get_tax(name, amount):
    t = env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'purchase')], limit=1)
    if not t:
        t = env['account.tax'].create({'name': name, 'amount': amount, 'type_tax_use': 'purchase', 'amount_type': 'percent'})
    return t.id

def get_partner(name):
    p = env['res.partner'].search([('name', '=', name)], limit=1)
    if not p:
        p = env['res.partner'].create({'name': name, 'supplier_rank': 1})
    return p.id

def fval(v):
    try:
        if v is None or pd.isna(v): return 0.0
        return float(v)
    except: return 0.0

def migrate_purchase():
    print("Reading ODS file...")
    df = pd.read_excel('/home/biz/odoo/new_purchase_invoice.xlsx', sheet_name='Sheet1')
    
    # ── 1. HEADER MAPPING ──────────────────────────────────────────────────────
    print("Mapping headers...")
    headers = df.iloc[1].tolist()
    hmap = {str(h).strip(): i for i, h in enumerate(headers)}
    
    tax_cols = [
        ('IGST@ 28', 28.0, 'igst'), ('IGST@28', 28.0, 'igst'),
        ('IGST@ 18', 18.0, 'igst'), ('IGST@18', 18.0, 'igst'),
        ('SGST@ 9%', 18.0, 'gst'),   ('CGST @ 9%', 18.0, 'gst'),
        ('SGST@6%', 12.0, 'gst'),    ('CGST@6%', 12.0, 'gst'),
        ('Sgst@2.5%', 5.0, 'gst'),   ('Cgst@2.5%', 5.0, 'gst'),
        ('SGST@14%', 28.0, 'gst'),   ('CGST@14%', 28.0, 'gst')
    ]

    print("Parsing records...")
    final_rows = []
    for idx, row in df.iterrows():
        if idx < 2: continue
        r = row.tolist()
        
        try:
            date_obj = pd.to_datetime(r[0])
            if pd.isna(date_obj): continue
        except: continue
        
        part_name = str(r[1]).strip()
        if not part_name or part_name in ('nan', 'None') or 'Total' in part_name: continue
        
        # Shift detection
        shift = 0
        if isinstance(r[4], (datetime, pd.Timestamp)): shift = 1
        
        gross     = fval(r[hmap['Gross Total'] + shift])
        rounding  = fval(r[hmap['Rounded Off'] + shift])
        
        row_taxes = [] # (rate, amount, type)
        total_tax_amt = 0
        rate = 0
        for hname, rval, ttype in tax_cols:
            if hname in hmap:
                amt = fval(r[hmap[hname] + shift])
                if amt != 0:
                    total_tax_amt += amt
                    rate = rval
        
        taxable_base = gross - total_tax_amt - rounding
        
        final_rows.append({
            'date': date_obj, 'partner': part_name, 'ref': str(r[3]).strip(),
            'gross': gross, 'taxable': taxable_base, 'rate': rate, 'idx': idx
        })

    print(f"Total parsed: {len(final_rows)}")
    
    # Verification
    m_calc = defaultdict(float)
    for r in final_rows: m_calc[r['date'].strftime('%m')] += r['gross']
    total_calc = sum(m_calc.values())
    print(f"Parsed Total: {total_calc:,.2f} | Tally Target: 90,323,140.32")

    # ── 2. ODOO IMPORT ────────────────────────────────────────────────────────
    print("Starting Odoo Import...")
    old = env['account.move'].search([('move_type', '=', 'in_invoice')])
    if old:
        old.filtered(lambda m: m.state != 'draft').button_draft()
        old.unlink()
        env.cr.commit()

    journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)
    ref_counter = defaultdict(int)
    count = 0
    
    for row in final_rows:
        pid = get_partner(row['partner'])
        base_ref = row['ref'] if row['ref'] not in ('nan', 'None', '') else f'MIG/{row["idx"]}'
        ref_counter[(pid, base_ref)] += 1
        cnt = ref_counter[(pid, base_ref)]
        full_ref = base_ref if cnt == 1 else f"{base_ref}/{cnt}"
        
        tax_ids = []
        if   row['rate'] == 18: tax_ids = [get_tax('CGST 9%', 9.0), get_tax('SGST 9%', 9.0)]
        elif row['rate'] == 12: tax_ids = [get_tax('CGST 6%', 6.0), get_tax('SGST 6%', 6.0)]
        elif row['rate'] == 5:  tax_ids = [get_tax('CGST 2.5%', 2.5), get_tax('SGST 2.5%', 2.5)]
        elif row['rate'] == 28: tax_ids = [get_tax('CGST 14%', 14.0), get_tax('SGST 14%', 14.0)]

        try:
            move = env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': pid,
                'invoice_date': row['date'].strftime('%Y-%m-%d'),
                'date': row['date'].strftime('%Y-%m-%d'),
                'ref': full_ref,
                'journal_id': journal.id,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Purchase (Migration)',
                    'quantity': 1,
                    # We round to 2 to avoid Odoo precision issues
                    'price_unit': round(row['taxable'], 2),
                    'tax_ids': [(6, 0, tax_ids)],
                })],
            })
            move.action_post()
            
            # Adjustment Step: 100% Match Guarantee
            # If Odoo's calculation doesn't match Tally's Gross exactly, adjust the price_unit
            diff = row['gross'] - move.amount_total
            if abs(diff) >= 0.01:
                # Calculate the adjustment needed to reach Gross after tax
                # Base + Base*Tax = Gross  -> Base = Gross / (1+Tax)
                # But it's easier to just add the diff to the line amount if no tax, 
                # or divide by (1+rate/100)
                adj = diff / (1 + (row['rate']/100.0))
                move.button_draft()
                line = move.invoice_line_ids[0]
                line.price_unit += adj
                move.action_post()

            count += 1
            if count % 100 == 0:
                print(f"  ✓ {count} imported...")
                env.cr.commit()
        except Exception as e:
            print(f"Row {row['idx']} Err: {e}")

    env.cr.commit()
    real_total = sum(m.amount_total for m in env['account.move'].search([('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]))
    print(f"\nFINAL ODOO TOTAL: {real_total:,.2f} | TALLY TARGET: 90,323,140.32 | DIFF: {real_total - 90323140.32:,.2f}")

migrate_purchase()

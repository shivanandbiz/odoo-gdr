# migrate_march_new_file.py
import pandas as pd
import numpy as np
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

def migrate_march():
    print("Reading March Invoice file...")
    # No headers in this file, read raw
    df = pd.read_excel('/home/biz/odoo/March_Purchase_invoice.xlsx', sheet_name='March', header=None)
    
    print("Parsing records with Smart Heuristic...")
    final_rows = []
    
    # Target for March
    target_march = 30054329.14
    
    for idx, row in df.iterrows():
        r = row.tolist()
        
        # 1. Date (Col 0)
        try:
            date_obj = pd.to_datetime(r[0])
            if pd.isna(date_obj) or date_obj.month != 3: continue
        except: continue
        
        # 2. Particulars & Ref (Col 1, 3)
        part_name = str(r[1]).strip()
        if not part_name or part_name in ('nan', 'None', 'Grand Total'): continue
        ref = str(r[3]).strip()
        
        # 3. Numeric Heuristic
        # Gross is usually index 5 in this file
        gross = fval(r[5])
        if gross == 0: continue
        
        # Find taxable base and taxes by looking at all subsequent cells
        nums = []
        for i in range(6, len(r)):
            v = fval(r[i])
            if v != 0: nums.append(v)
            
        taxable_base = gross
        rate = 0.0
        
        if nums:
            # Largest is taxable base
            taxable_base = max(nums)
            # Find rate
            calc_rate = (gross - taxable_base) / taxable_base if taxable_base > 0 else 0
            if 0.17 <= calc_rate <= 0.19: rate = 18.0
            elif 0.04 <= calc_rate <= 0.06: rate = 5.0
            elif 0.11 <= calc_rate <= 0.13: rate = 12.0
            elif 0.27 <= calc_rate <= 0.29: rate = 28.0
            
        final_rows.append({
            'date': date_obj, 'partner': part_name, 'ref': ref,
            'gross': gross, 'taxable': taxable_base, 'rate': rate, 'idx': idx
        })

    print(f"Total parsed for March: {len(final_rows)}")
    parsed_total = sum(r['gross'] for r in final_rows)
    print(f"Parsed March Total: {parsed_total:,.2f} | Tally Image Target: 30,054,329.14")

    # ── ODOO IMPORT ────────────────────────────────────────────────────────
    print("\nDeleting existing March purchase records...")
    march_moves = env['account.move'].search([
        ('move_type', '=', 'in_invoice'),
        ('date', '>=', '2026-03-01'),
        ('date', '<=', '2026-03-31')
    ])
    if march_moves:
        march_moves.filtered(lambda m: m.state != 'draft').button_draft()
        march_moves.unlink()
        env.cr.commit()

    journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)
    ref_counter = defaultdict(int)
    count = 0
    
    for row in final_rows:
        pid = get_partner(row['partner'])
        base_ref = row['ref'] if row['ref'] not in ('nan', 'None', '') else f'MIG/M/{row["idx"]}'
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
                    'name': 'Purchase (March Update)',
                    'quantity': 1,
                    'price_unit': float(round(row['taxable'], 2)),
                    'tax_ids': [(6, 0, tax_ids)],
                })],
            })
            move.action_post()
            
            # Adjustment Step
            diff = row['gross'] - move.amount_total
            if abs(diff) >= 0.01:
                adj = diff / (1 + (row['rate']/100.0))
                move.button_draft()
                move.invoice_line_ids[0].price_unit += adj
                move.action_post()
                
            count += 1
        except: pass

    env.cr.commit()
    print(f"\nMarch Migration Done. Records: {count}")
    
    # Final check
    bills = env['account.move'].search([
        ('move_type', '=', 'in_invoice'),
        ('date', '>=', '2026-03-01'),
        ('date', '<=', '2026-03-31'),
        ('state', '=', 'posted')
    ])
    real_total = sum(m.amount_total for m in bills)
    print(f"Final Odoo March Total: {real_total:,.2f} | Tally Image Target: 30,054,329.14")
    print(f"Difference: {real_total - 30054329.14:,.2f}")

migrate_march()

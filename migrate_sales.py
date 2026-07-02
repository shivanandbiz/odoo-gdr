# migrate_sales.py
import pandas as pd
from datetime import datetime
from collections import defaultdict

def get_tax(name, amount):
    t = env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'sale')], limit=1)
    if not t:
        t = env['account.tax'].create({'name': name, 'amount': amount, 'type_tax_use': 'sale', 'amount_type': 'percent'})
    return t.id

def get_partner(name):
    p = env['res.partner'].search([('name', '=', name)], limit=1)
    if not p:
        p = env['res.partner'].create({'name': name, 'customer_rank': 1})
    return p.id

def fval(v):
    try:
        if v is None or pd.isna(v): return 0.0
        return float(str(v).replace(',',''))
    except: return 0.0

def migrate_sales():
    print("Reading Sales Registers...")
    sheets = ['Sales Inv. Register', 'Sales Inv. Register (2)']
    all_rows = []
    
    for s in sheets:
        df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', sheet_name=s, header=None)
        for idx, row in df.iterrows():
            r = row.tolist()
            try:
                date_obj = pd.to_datetime(r[0])
                if pd.isna(date_obj): continue
            except: continue
            
            part_name = str(r[1]).strip()
            if not part_name or part_name in ('nan', 'None', 'Grand Total', 'Particulars'): continue
            
            ref = str(r[3]).strip()
            # Numeric Heuristic
            nums = []
            for i in range(4, len(r)):
                v = fval(r[i])
                if v != 0: nums.append(v)
            if not nums: continue
            
            gross = nums[1] if len(nums) > 1 else nums[0]
            taxable = nums[0]
            
            rate = 0.0
            if taxable > 0:
                calc_rate = (gross - taxable) / taxable
                if 0.17 <= calc_rate <= 0.19: rate = 18.0
                elif 0.04 <= calc_rate <= 0.06: rate = 5.0
                elif 0.11 <= calc_rate <= 0.13: rate = 12.0
                elif 0.27 <= calc_rate <= 0.29: rate = 28.0
            
            all_rows.append({
                'date': date_obj, 'partner': part_name, 'ref': ref,
                'gross': gross, 'taxable': taxable, 'rate': rate
            })

    print(f"Total parsed sales: {len(all_rows)}")
    
    # ── ODOO IMPORT ────────────────────────────────────────────────────────
    print("Deleting existing sales records for 2025-26...")
    env['account.move'].search([('move_type', '=', 'out_invoice'), ('date', '>=', '2025-04-01'), ('date', '<=', '2026-03-31')]).button_draft()
    env['account.move'].search([('move_type', '=', 'out_invoice'), ('date', '>=', '2025-04-01'), ('date', '<=', '2026-03-31')]).unlink()

    journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)
    ref_counter = defaultdict(int)
    
    for row in all_rows:
        pid = get_partner(row['partner'])
        ref_counter[(pid, row['ref'])] += 1
        cnt = ref_counter[(pid, row['ref'])]
        full_ref = row['ref'] if cnt == 1 else f"{row['ref']}/{cnt}"
        
        tax_ids = []
        if   row['rate'] == 18: tax_ids = [get_tax('Output CGST 9%', 9.0), get_tax('Output SGST 9%', 9.0)]
        elif row['rate'] == 12: tax_ids = [get_tax('Output CGST 6%', 6.0), get_tax('Output SGST 6%', 6.0)]
        elif row['rate'] == 5:  tax_ids = [get_tax('Output CGST 2.5%', 2.5), get_tax('Output SGST 2.5%', 2.5)]
        
        move = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': pid,
            'invoice_date': row['date'].strftime('%Y-%m-%d'),
            'date': row['date'].strftime('%Y-%m-%d'),
            'ref': full_ref,
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Sales Migration',
                'quantity': 1,
                'price_unit': float(row['taxable']),
                'tax_ids': [(6, 0, tax_ids)],
            })],
        })
        move.action_post()
        
        # Adjustment
        diff = row['gross'] - move.amount_total
        if abs(diff) >= 0.01:
            adj = diff / (1 + (row['rate']/100.0))
            move.button_draft()
            move.invoice_line_ids[0].price_unit += adj
            move.action_post()

    env.cr.commit()
    print("Sales Migration Done.")

migrate_sales()

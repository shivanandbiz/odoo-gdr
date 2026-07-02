import pandas as pd
from datetime import datetime

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

def migrate_credit_notes():
    fname = '/home/biz/odoo/new_credit_note_register.xlsx'
    print(f"Reading {fname} with pandas...")
    df = pd.read_excel(fname, header=None)
    
    # ── 1. DELETE existing credit notes (out_refund) ───────────────────
    print("Deleting existing customer refunds (Credit Notes)...")
    existing = env['account.move'].search([('move_type', '=', 'out_refund')])
    if existing:
        for m in existing:
            if m.state != 'draft': m.button_draft()
        existing.unlink()
        env.cr.commit()
        print(f"  Deleted {len(existing)} records.")
    
    journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)
    count = 0
    errors = 0
    
    # Data starts from row 10 (index 9)
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = str(r[3]).strip() if pd.notna(r[3]) else f"MIG/CN/{idx}"
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        try: taxable_value = float(r[5] or 0)
        except: taxable_value = 0.0
            
        try: gross_total = float(r[6] or 0)
        except: gross_total = 0.0
            
        try: igst_amt = float(r[8] or 0)
        except: igst_amt = 0.0
        
        # Check for CGST/SGST if they exist in other columns (unlikely based on preview but safe)
        cgst_amt = 0.0
        sgst_amt = 0.0
        # If the file had more columns, I'd check them. Preview shows 9 columns (0 to 8).
        
        if isinstance(raw_date, (datetime, pd.Timestamp)):
            dt_str = raw_date.strftime('%Y-%m-%d')
        else:
            try:
                dt_str = str(raw_date)[:10]
                if ' ' in dt_str: dt_str = dt_str.split(' ')[0]
            except:
                dt_str = datetime.now().strftime('%Y-%m-%d')
                
        # Determine tax IDs
        tax_ids = []
        if igst_amt > 0:
            tax_ids = [get_tax('IGST 18%', 18.0, 'sale')]
        elif taxable_value > 0 and abs(gross_total - taxable_value * 1.18) < 1.0:
             # Default to IGST 18% for sales refund if value matches
             tax_ids = [get_tax('IGST 18%', 18.0, 'sale')]
        
        try:
            move = env['account.move'].create({
                'move_type': 'out_refund',
                'partner_id': get_partner(part_name),
                'invoice_date': dt_str,
                'date': dt_str,
                'ref': vref,
                'journal_id': journal.id,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Credit Note (Migration)',
                    'quantity': 1,
                    'price_unit': round(taxable_value, 2),
                    'tax_ids': [(6, 0, tax_ids)],
                })],
            })
            move.action_post()
            count += 1
        except Exception as e:
            errors += 1
            print(f"  ERR row {idx}: {e}")
            
    env.cr.commit()
    print(f"\nMigration Finished. Total Credit Notes: {count} | Errors: {errors}")

migrate_credit_notes()
